import asyncio
import io
import logging
import os
import random
import time
import uuid
import zipfile
from email.utils import parsedate_to_datetime

import aiohttp
import requests
from dotenv import load_dotenv

from src.config.config import (
    BV_MAX_ATTEMPTS,
    BV_REQUESTS_PER_SECOND,
    BV_THROTTLE_BACKOFF_SECONDS,
    BV_TOKEN_RENEWAL_MARGIN_SECONDS,
)


logger = logging.getLogger(__name__)
API_BASE_URL = "https://gw.api.bolagsverket.se/vardefulla-datamangder/v1"
RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}


def unzip_documents(zip_bytes):
    xml_files = []
    if zip_bytes is None:
        return xml_files
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in z.namelist():
                if name.endswith(".xml") or name.endswith(".xhtml"):
                    with z.open(name) as f:
                        xml_files.append(f.read().decode("utf-8"))
    except Exception as e:
        print(f"Couldn't unzip documents: {e}")

    return xml_files if len(xml_files) > 0 else None


# --- Token generator ---
def _fetch_token() -> tuple[str, int]:
    load_dotenv()
    url = "https://portal.api.bolagsverket.se/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("BV_CLIENT"),
        "client_secret": os.getenv("BV_SECRET"),
        "scope": "vardefulla-datamangder:read vardefulla-datamangder:ping"
    }
    response = requests.post(url, data=data, timeout=30)
    response.raise_for_status()
    payload = response.json()
    lifetime = int(payload["expires_in"])
    if lifetime <= 0:
        raise ValueError("Token endpoint returned a non-positive lifetime")
    return payload["access_token"], lifetime


def get_token() -> str:
    return _fetch_token()[0]


class RateLimiter:
    def __init__(self, rate_per_sec: float = BV_REQUESTS_PER_SECOND):
        self._interval = 1.0 / rate_per_sec
        self._lock = asyncio.Lock()
        self._next_request = 0.0

    def defer(self, seconds: float):
        """Apply a cooldown to every request sharing this limiter."""
        self._next_request = max(self._next_request, time.monotonic() + seconds)

    async def wait(self):
        async with self._lock:
            while (delay := self._next_request - time.monotonic()) > 0:
                await asyncio.sleep(delay)
            self._next_request = time.monotonic() + self._interval


def retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    if value.isascii() and value.isdecimal():
        return int(value)
    try:
        retry_at = parsedate_to_datetime(value)
        if retry_at.tzinfo is not None:
            return max(0.0, retry_at.timestamp() - time.time())
    except (ValueError, OverflowError):
        pass
    return None


class BVClient:
    def __init__(self, *, limiter: RateLimiter | None = None):
        self.token = None
        self.limiter = limiter if limiter is not None else RateLimiter()
        self._token_lock = asyncio.Lock()
        self._renew_at = 0
        self.session = aiohttp.ClientSession()

    @staticmethod
    def _renewal_deadline(lifetime):
        margin = BV_TOKEN_RENEWAL_MARGIN_SECONDS
        if not 0 <= margin < lifetime:
            raise ValueError(
                f"BV_TOKEN_RENEWAL_MARGIN_SECONDS ({margin}) must be nonnegative "
                f"and smaller than the token lifetime ({lifetime} seconds)"
            )
        return time.monotonic() + lifetime - margin

    async def _request_token(self):
        async with self._token_lock:
            await self.limiter.wait()
            if time.monotonic() >= self._renew_at:
                token, lifetime = await asyncio.to_thread(_fetch_token)
                self._renew_at = self._renewal_deadline(lifetime)
                self.token = token
            return self.token

    async def _request(self, method, path, *, payload=None):
        accept = "application/zip" if method == "GET" else "application/json"

        retried_auth = False
        for attempt in range(1, BV_MAX_ATTEMPTS + 1):
            token = await self._request_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": accept,
                "X-Request-Id": str(uuid.uuid4()),
            }
            delay = 2 ** (attempt - 1) + random.uniform(0, 0.3)
            shared_cooldown = False

            try:
                async with self.session.request(
                    method, f"{API_BASE_URL}/{path}", json=payload, headers=headers
                ) as response:
                    status = response.status
                    if 200 <= status < 300:
                        return await response.read() if method == "GET" else await response.json()

                    if status == 401 and not retried_auth and attempt < BV_MAX_ATTEMPTS:
                        if self.token == token:
                            self._renew_at = 0
                        retried_auth = True
                        continue
                    failure = f"HTTP {status}"
                    if status not in RETRYABLE_STATUSES:
                        logger.warning("%s %s failed with %s", method, path, failure)
                        return None

                    retry_after = retry_after_seconds(response.headers.get("Retry-After"))
                    if status == 429:
                        delay *= BV_THROTTLE_BACKOFF_SECONDS
                    if retry_after is not None:
                        delay = max(delay, retry_after)

                    shared_cooldown = status == 429 or (status == 503 and retry_after is not None)
                    if shared_cooldown:
                        self.limiter.defer(delay)
            except (aiohttp.ClientConnectionError, aiohttp.ClientPayloadError, TimeoutError) as error:
                failure = f"{type(error).__name__}: {error}"
            except (aiohttp.ClientError, ValueError) as error:
                logger.warning("%s %s failed with %s: %s", method, path, type(error).__name__, error)
                return None

            if attempt == BV_MAX_ATTEMPTS:
                logger.warning("%s %s failed after %s attempts (%s)", method, path, attempt, failure)
                return None

            logger.warning(
                "%s %s attempt %s/%s failed (%s), retrying in at least %.1f seconds",
                method, path, attempt, BV_MAX_ATTEMPTS, failure, delay,
            )
            if not shared_cooldown:
                await asyncio.sleep(delay)

    async def get_bv_data(self, org_no):
        return await self._request("POST", "organisationer", payload={"identitetsbeteckning": org_no})

    async def get_doc_list(self, org_no):
        response = await self._request(
            "POST", "dokumentlista", payload={"identitetsbeteckning": org_no}
        )
        return response.get("dokument", []) if response else []

    async def get_doc_zip(self, doc_id):
        return await self._request("GET", f"dokument/{doc_id}")

    # --- Composite document downloads ---
    async def iter_all_doc_zips(self, org_no):
        """Yield the document metadata and ZIP bytes for every available download."""
        for doc in await self.get_doc_list(org_no):
            zip_bytes = await self.get_doc_zip(doc["dokumentId"])
            if zip_bytes:
                yield doc, zip_bytes

    async def get_latest_doc_zip(self, org_no):
        docs = await self.get_doc_list(org_no)

        if len(docs) == 0:
            print(f"No documents to download for {org_no}")
            return None

        latest_doc = max(
            docs,
            key=lambda d: d["rapporteringsperiodTom"]
        )
        doc_id = latest_doc["dokumentId"]

        zip_bytes = await self.get_doc_zip(doc_id)
        return zip_bytes if zip_bytes else None

    async def close(self):
        await self.session.close()
