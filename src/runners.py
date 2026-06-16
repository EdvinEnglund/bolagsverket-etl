from fetchers import get_token, get_latest_report, get_bv_data
from parsers import parse_report, parse_bv_data
from utils import load_done, mark_done, dump_parquet_batch, load_all_batches, save_result, clear_tmp
from src.config import BATCH_SIZE, PARQUET_DATA_DIR, DONE_FILE_DIR, EXAMPLE_ORGS
import time

def run_main_pipeline(
        org_nos,
        save = False,
        output_path = None,
        file_format = "parquet"
        ):

    #ADD TOKEN REGENERATOR LOGIC HERE
    token = get_token()
    rows = []
    batch_orgs = []
    done = load_done()
    count = 1
    remaining = len(org_nos)

    for org_no in org_nos:

        if org_no in done:
            batch_orgs.append(org_no)
            remaining -= 1
            continue

        report = get_latest_report(token, org_no)

        if not report:
            batch_orgs.append(org_no)
            remaining -= 1
            continue

        parsed_report = parse_report(report)
        company_info = get_bv_data(token, org_no)
        parsed_company_info = parse_bv_data(company_info)
        row = {
            **parsed_company_info,
            **parsed_report
        }
        rows.append(row)
        batch_orgs.append(org_no)
        print(f"Succesfully loaded {org_no}, {count} done, {remaining - count} remaining.")

        if len(rows) >= BATCH_SIZE:
            dump_parquet_batch(rows)
            mark_done(batch_orgs)
            rows.clear()
            batch_orgs.clear()

        count += 1

    # final flush
    dump_parquet_batch(rows)
    rows.clear()

    #Load and clear /tmp data
    df = load_all_batches()
    clear_tmp(PARQUET_DATA_DIR)
    clear_tmp(DONE_FILE_DIR)
    if save:
        # Save results
        save_result(df, output_path, file_format)
        return df

    return df


if __name__ == "__main__":

    t = time.time()
    print(run_main_pipeline(EXAMPLE_ORGS, save = False, file_format = "csv"))
    print(f"Ran pipe line in {time.time() - t:.2f} seconds")
