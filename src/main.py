import asyncio
from src.extract.bv_client import BVClient, RateLimiter, get_token
from src.utils.utils import unzip_documents
from src.transform.parsers import parse_report, parse_bv_data
from src.load.load_utils import load_done, mark_done, dump_parquet_batch, load_all_batches, save_result, clear_tmp
from src.config.config import CONCURRENCY, BATCH_SIZE, PARQUET_DATA_DIR, DONE_FILE_DIR, EXAMPLE_ORGS
import time

semaphore = asyncio.Semaphore(CONCURRENCY)

async def process_org(client: BVClient, org_no: str):

    # Add token regenerator logic here, create whole new client.. global time variable
    async with semaphore:

        zip_bytes = await client.get_latest_doc_zip(org_no)
        if not zip_bytes: return None

        # Documents index 0 = Annual report, 1 = Accountant statement
        documents = unzip_documents(zip_bytes)
        if not documents: return None

        report = documents[0]
        acc_statement = documents[1] if len(documents) > 1 else None

        bv_data = await client.get_bv_data(org_no)
        if not bv_data: return None

        return {
            **parse_bv_data(bv_data),
            **parse_report(report)
        }

async def process_batch(org_nos, client: BVClient):
    done = load_done()
    tasks = [process_org(client, org_no) for org_no in org_nos if org_no not in done]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]

async def run_pipeline(
        org_nos,
        save = False,
        output_path = None,
        file_format = "parquet"
    ):

    token = get_token()
    limiter = RateLimiter()
    client = BVClient(token, limiter)

    if BATCH_SIZE >= len(org_nos):
        batches = [org_nos]
    else:
        batches = [org_nos[i:i+BATCH_SIZE] for i in range(0, len(org_nos), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        t0 = time.time()
        print(f"Processing batch {i+1} of {len(batches)}...")
        orgs = await process_batch(batch, client)
        if orgs:
            dump_parquet_batch(orgs)
            mark_done(batch)
        print(f"Done processing batch {i+1} of {len(batches)} in {time.time() - t0:.2f}s")

    await client.close()

    # Load and clear /tmp data
    df = load_all_batches()

    if save:
        save_result(df, output_path, file_format)

    clear_tmp(PARQUET_DATA_DIR)
    clear_tmp(DONE_FILE_DIR)

    return df

if __name__ == "__main__":
    t = time.time()
    result = asyncio.run(run_pipeline(EXAMPLE_ORGS, save = False))
    print(result)
    print(f"Ran pipeline in {time.time() - t:.2f} seconds")




