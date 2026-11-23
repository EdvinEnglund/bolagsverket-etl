import argparse
import asyncio
from src.extract.bv_client import BVClient, unzip_documents
from src.transform.document_classifier import DocumentType, identify_documents
from src.transform.parsers import parse_auditor_report, parse_bv_data, parse_flerarsoversikt
from src.load.load_utils import (
    OUTPUT_FORMATS, load_done, mark_done, dump_parquet_batch, load_all_batches, save_result, clear_tmp,
)
from src.load.org_numbers import load_org_numbers
from src.config.config import CONCURRENCY, BATCH_SIZE, PARQUET_DATA_DIR, DONE_FILE_DIR
import time

semaphore = asyncio.Semaphore(CONCURRENCY)

async def process_org(client: BVClient, org_no: str):

    async with semaphore:

        zip_bytes = await client.get_latest_doc_zip(org_no)
        if not zip_bytes: return None

        documents = unzip_documents(zip_bytes)
        if not documents: return None

        classified = identify_documents(documents, org_no)
        report = classified.get(DocumentType.ANNUAL_REPORT)
        if report is None: return None

        bv_data = await client.get_bv_data(org_no)
        if not bv_data: return None

        return {
            **parse_bv_data(bv_data),
            **parse_flerarsoversikt(report),
            **parse_auditor_report(classified.get(DocumentType.AUDITOR_REPORT), annual_report=report),
        }

async def process_batch(org_nos, client: BVClient):
    done = load_done()
    tasks = [process_org(client, org_no) for org_no in org_nos if org_no not in done]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]

async def run_pipeline(
    org_nos=None,
    save: str | None = None,
    *,
    orgs_path=None,
):
    if save is not None and save not in OUTPUT_FORMATS:
        raise ValueError(f"save must be None or one of {OUTPUT_FORMATS}")

    if org_nos is None:
        org_nos = load_org_numbers(orgs_path)
    elif orgs_path is not None:
        raise ValueError("Provide either org_nos or orgs_path")

    client = BVClient()

    if BATCH_SIZE >= len(org_nos):
        batches = [org_nos]
    else:
        batches = [org_nos[i:i+BATCH_SIZE] for i in range(0, len(org_nos), BATCH_SIZE)]

    try:
        for i, batch in enumerate(batches):
            t0 = time.time()
            print(f"Processing batch {i+1} of {len(batches)}...")
            orgs = await process_batch(batch, client)
            if orgs:
                dump_parquet_batch(orgs)
                mark_done(batch)
            print(f"Done processing batch {i+1} of {len(batches)} in {time.time() - t0:.2f}s")
    finally:
        await client.close()

    # Load and clear /tmp data
    df = load_all_batches()

    if save is not None:
        output_path = save_result(df, save)
        print(f"Saved results to {output_path}")

    clear_tmp(PARQUET_DATA_DIR)
    clear_tmp(DONE_FILE_DIR)

    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Bolagsverket pipeline.")
    parser.add_argument(
        "orgs_path",
        nargs="?",
        help="Text file with one registration number per line (default: data/input/example_orgs.txt)",
    )
    parser.add_argument(
        "--save",
        choices=OUTPUT_FORMATS,
        help="Save a timestamped file in data/output.",
    )
    args = parser.parse_args()
    t = time.time()
    result = asyncio.run(run_pipeline(orgs_path=args.orgs_path, save=args.save))
    print(result)
    print(f"Ran pipeline in {time.time() - t:.2f} seconds")




