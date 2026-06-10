#Hello world
from fetchers import get_token, get_latest_report, get_bv_data
from parsers import parse_report, parse_bv_data
import pandas as pd
from config import DONE_FILE_DIR, DONE_FILE_NAME, PARQUET_DATA_DIR, BATCH_SIZE, DEFAULT_OUTPUT_DIR
from datetime import datetime
from pathlib import Path
import shutil
import uuid

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
    filename = str(uuid.uuid4()) + ".parquet"
    df = pd.DataFrame(rows)
    df.to_parquet(save_dir / filename)
    return

# Save helpers
def load_all_batches() -> pd.DataFrame:
    path = Path(__file__).resolve().parent.parent / PARQUET_DATA_DIR
    parquet_files = sorted(Path(path).glob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError("No batch files found.")

    dfs = [pd.read_parquet(file) for file in parquet_files]

    return pd.concat(dfs, ignore_index=True)

def resolve_output_path(output_path = None, output_format = "parquet"):
    project = Path(__file__).resolve().parents[1]
    default_path = project / DEFAULT_OUTPUT_DIR
    time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_path is None:
        return default_path / f"{time_stamp}.{output_format}"
    return Path(output_path)

def save_result(df, path = None, output_format = "parquet"):
    output_path = resolve_output_path(path, output_format)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "parquet":
        df.to_parquet(output_path, index=False)
        return
    if output_format == "csv":
        df.to_csv(output_path, index=False)
        return
    print("Could not save result: format must be 'parquet' or 'csv'")
    return

def clear_tmp(directory):
    project_root = Path(__file__).resolve().parent.parent
    path = project_root / directory

    if not path.exists():
        return

    if not path.is_dir():
        raise ValueError(f"{path} is not a directory")

    for item in path.iterdir():

        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

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
    #clear_tmp(PARQUET_DATA_DIR)
    #clear_tmp(DONE_FILE_DIR)
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
