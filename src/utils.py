from idlelib.colorizer import prog_group_name_to_tag
from pathlib import Path
from datetime import datetime
import pandas as pd
import uuid
import shutil
from config import DONE_FILE_DIR, PARQUET_DATA_DIR, DEFAULT_OUTPUT_DIR

def save_report_file(report, org_no):
    try:
        if len(report) == 0:
            print("No report to save")
            return ""

        project_root = Path(__file__).resolve().parent.parent
        save_dir = project_root / "data" / "example-xmls"
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"{org_no}_report.xml"
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"Saved XML report to: {save_path}")

    except:
        print("Couldn't save report")
    return


# Batch processing helpers
def load_done():
    project_root = Path(__file__).resolve().parent.parent
    load_dir = project_root / DONE_FILE_DIR
    load_dir.mkdir(parents=True, exist_ok=True)
    save_file = load_dir / "done.txt"
    try:
        with open(save_file, "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def mark_done(org_nos):
    project_root = Path(__file__).resolve().parent.parent
    save_dir = project_root / DONE_FILE_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    save_file = save_dir / "done.txt"

    for org_no in org_nos:
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

def load_all_batches() -> pd.DataFrame:
    path = Path(__file__).resolve().parent.parent / PARQUET_DATA_DIR
    parquet_files = sorted(Path(path).glob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError("No batch files found.")

    dfs = [pd.read_parquet(file) for file in parquet_files]

    return pd.concat(dfs, ignore_index=True)

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

# Save helpers
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


#######################################################################################
# Utility function to extract org. numbers from csv's downloaded from bolagsfilter.se #
#######################################################################################

def extract_orgnrs():
    project_root = Path(__file__).resolve().parent.parent
    data_dir = Path("data/example_csvs")

    example_list = []

    for i in range(1, 7):
        file_path = project_root / data_dir / f"screener_sida{i}.csv"
        df = pd.read_csv(file_path)

        if "org_nr" in df.columns:
            example_list.extend(df["org_nr"].dropna().tolist())

    for i in range(len(example_list)):
        example_list[i] = str(example_list[i])

    print(example_list)



if __name__ == "__main__":
    extract_orgnrs()













