import requests
from dotenv import load_dotenv
import os
import uuid
import zipfile
import io
import time
from src.config.config import LIMIT_RATE, MAX_RETRIES
import random
import asyncio
import aiohttp

# --- Unzip helper ---
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
    return xml_files

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

# --- Rate limiter ---
class RateLimiter:
    def __init__(self, rate_per_sec: float = LIMIT_RATE):
        self.delay = 1.0 / rate_per_sec
        self.lock = asyncio.Lock()
        self.last_call = 0

    async def wait(self):
        async with self.lock:
            now = time.time()
            wait = self.delay - (now - self.last_call)

            if wait > 0:
                await asyncio.sleep(wait)

            self.last_call = time.time()

# --- API Client ---
class BVClient:
    def __init__(self, token: str, limiter: RateLimiter):
        self.token = token
        self.limiter = limiter
        self.session = aiohttp.ClientSession()

    # --- Core Requests ---
    async def _post(self, url: str, payload, retries = MAX_RETRIES):
        for i in range(retries):
            try:
                await self.limiter.wait()
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "accept": "application/json",
                    "X-Request-Id": str(uuid.uuid4())
                }

                async with self.session.post(url, json=payload, headers=headers) as response:
                    if response.status in (400, 401, 403, 404, 500):
                        print(f"HTTP Error in _post for {payload["identitetsbeteckning"]}: {response.status}")
                        return {}

                    if response.status == 429:
                        raise Exception(f"HTTP Error in _post: {response.status}")

                    return await response.json()

            except Exception:
                print(f"Rate limit exceeded for _post request for org.no {payload["identitetsbeteckning"]}. Retry {i + 1} of {MAX_RETRIES}")
                await asyncio.sleep((2 ** i) + random.uniform(0, 0.3))

        return None

    async def _get(self, url: str, retries = MAX_RETRIES):
        for i in range(retries):
            try:
                await self.limiter.wait()
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "accept": "application/zip",
                    "X-Request-Id": str(uuid.uuid4())
                }
                async with self.session.get(url, headers=headers) as response:
                    if response.status in (400, 401, 403, 404, 500):
                        print(f"HTTP Error in _get for: {response.status}")
                        return None

                    if response.status == 429:
                        raise Exception(f"HTTP Error in _get: {response.status}")

                    response.raise_for_status()
                    return await response.read()

            except Exception:
                print(f"Rate limit exceeded for _get request for URL {url}. Retry {i+1} of {MAX_RETRIES}")
                await asyncio.sleep((2 ** i) + random.uniform(0, 0.3))

        return None

    # --- API methods ---

    async def get_bv_data(self, org_no):
        url = "https://gw.api.bolagsverket.se/vardefulla-datamangder/v1/organisationer"
        return await self._post(url, {"identitetsbeteckning": org_no})

    async def get_doc_list(self, org_no):
        url = "https://gw.api.bolagsverket.se/vardefulla-datamangder/v1/dokumentlista"
        response = await self._post(url, {"identitetsbeteckning": org_no})

        if not response:
            return []

        return response.get("dokument", [])

    async def get_doc_zip(self, doc_id):
        url = f"https://gw.api.bolagsverket.se/vardefulla-datamangder/v1/dokument/{doc_id}"
        return await self._get(url)

    # --- Composite mini pipeline method ---
    async def get_latest_report(self, org_no):
        docs = await self.get_doc_list(org_no)

        if len(docs) == 0:
            print(f"No documents to download for {org_no}")
            return None

        latest_doc = max(
            docs,
            key=lambda d: d["rapporteringsperiodTom"]
        )
        doc_id = latest_doc["dokumentId"]
        #doc_id = docs[-1]["dokumentId"]
        zip_bytes = await self.get_doc_zip(doc_id)
        if not zip_bytes:
            return None
        documents = unzip_documents(zip_bytes)
        if len(documents) == 0:
            return None
        # first index is annual report, second is revisionsberättelse (accountant statement)
        return documents[0]

    async def close(self):
        await self.session.close()




