from fetchers import get_token, get_latest_report, get_bv_data
from parsers import parse_report, parse_bv_data
from utils import load_done, mark_done, dump_parquet_batch, load_all_batches, save_result, clear_tmp
from config import BATCH_SIZE, PARQUET_DATA_DIR, DONE_FILE_DIR

def run_main_pipeline(
        org_nos,
        save = True,
        output_path = None,
        file_format = "parquet"
        ):

    #ADD TOKEN REGENERATOR LOGIC HERE
    token = get_token()
    rows = []
    done = load_done()

    for org_no in org_nos:
        print(f"Loading {org_no}...")
        report = get_latest_report(token, org_no)
        if not report or org_no in done:
            continue

        parsed_report = parse_report(report)
        company_info = get_bv_data(token, org_no)
        parsed_company_info = parse_bv_data(company_info)

        row = {
            **parsed_company_info,
            **parsed_report
        }
        rows.append(row)

        if len(rows) >= BATCH_SIZE:
            dump_parquet_batch(rows)
            mark_done(org_no)
            rows.clear()

        mark_done(org_no)

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
    org_nos = ["5568808686",
              "5568649478",
              "5565540035",
              "5566086483",
              "5590892542",
              "5564363421",
              "5592565096"] # index example number

    #org_no = org_nos[0]
    #token = get_token()

    #report = get_latest_report(token, org_no)
    #save_report_file(report, org_no)
    #parsed_report = parse_report(report)

    print(run_main_pipeline(org_nos, file_format = "csv"))
