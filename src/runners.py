#Hello world
from fetchers import get_token, get_latest_report, get_bv_data
from parsers import parse_report, parse_bv_data
import pandas as pd
from utils import save_report_file
from config import DONE_FILE_DIR, DONE_FILE_NAME, PARQUET_DATA_DIR, BATCH_SIZE
from datetime import datetime
from pathlib import Path

# Batch processing helpers
def load_done():
    project_root = Path(__file__).resolve().parent.parent
    load_dir = project_root / DONE_FILE_DIR
    load_dir.mkdir(parents=True, exist_ok=True)
    save_file = load_dir / DONE_FILE_NAME
    try:
        with open(save_file, "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def mark_done(org_no):
    project_root = Path(__file__).resolve().parent.parent
    save_dir = project_root / DONE_FILE_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    save_file = save_dir / DONE_FILE_NAME
    with open(save_file, "a") as f:
        f.write(str(org_no) + "\n")
    return

def dump_parquet_batch(rows):
    project_root = Path(__file__).resolve().parent.parent
    save_dir = project_root / PARQUET_DATA_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime(
        "%Y%m%d_%H%M%S.parquet"
    )
    df = pd.DataFrame(rows)

    df.to_parquet(save_dir / filename)
    return

def run_main_pipeline(org_nos):
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


    # final flush
    dump_parquet_batch(rows)
    mark_done(org_nos[-1])

    return


if __name__ == "__main__":
    org_nos = ["5568808686",
              "5568649478",
              "5565540035",
              "5566086483",
              "5590892542",
              "5564363421",
              "5592565096"] # index example number

    org_no = org_nos[0]
    token = get_token()

    #report = get_latest_report(token, org_no)
    #save_report_file(report, org_no)
    #parsed_report = parse_report(report)

    run_main_pipeline(org_nos)
