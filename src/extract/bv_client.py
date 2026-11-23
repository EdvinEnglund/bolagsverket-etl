import asyncio
import logging
import os
import random
import time
import uuid
from email.utils import parsedate_to_datetime

import aiohttp
import requests
from dotenv import load_dotenv

from src.config.config import (
    BV_MAX_ATTEMPTS,
    BV_REQUESTS_PER_SECOND,
    BV_THROTTLE_BACKOFF_SECONDS,
)


logger = logging.getLogger(__name__)
API_BASE_URL = "https://gw.api.bolagsverket.se/vardefulla-datamangder/v1"
RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}


# --- Token generator ---
def get_token():
    load_dotenv()
    url = "https://portal.api.bolagsverket.se/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("BV_CLIENT"),
        "client_secret": os.getenv("BV_SECRET"),
        "scope": "vardefulla-datamangder:read vardefulla-datamangder:ping"
    }
    response = requests.post(url, data=data)

    if response.status_code != 200:
        print(f"Http Error: Get token status: {response.status_code}")

    response = response.json()
    return response["access_token"]

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
    def __init__(self, token: str, limiter: RateLimiter):
        self.token = token
        self.limiter = limiter
        self.session = aiohttp.ClientSession()

    async def _request(self, method, path, *, payload=None):
        accept = "application/zip" if method == "GET" else "application/json"

        for attempt in range(1, BV_MAX_ATTEMPTS + 1):
            await self.limiter.wait()
            headers = {
                "Authorization": f"Bearer {self.token}",
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
