from pathlib import Path
from datetime import datetime
import pandas as pd
import uuid
import shutil
from src.config.config import DONE_FILE_DIR, PARQUET_DATA_DIR, DEFAULT_OUTPUT_DIR

OUTPUT_FORMATS = ("csv", "parquet")

# Batch processing helpers
def load_done():
    project_root = Path(__file__).resolve().parent.parent.parent
    load_dir = project_root / DONE_FILE_DIR
    load_dir.mkdir(parents=True, exist_ok=True)
    save_file = load_dir / "done.txt"
    try:
        with open(save_file, "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def mark_done(org_nos):
    project_root = Path(__file__).resolve().parent.parent.parent
    save_dir = project_root / DONE_FILE_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    save_file = save_dir / "done.txt"

    for org_no in org_nos:
        with open(save_file, "a") as f:
            f.write(str(org_no) + "\n")
    return

def dump_parquet_batch(rows):
    project_root = Path(__file__).resolve().parent.parent.parent
    save_dir = project_root / PARQUET_DATA_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = str(uuid.uuid4()) + ".parquet"
    df = pd.DataFrame(rows)
    df.to_parquet(save_dir / filename)
    return

def load_all_batches() -> pd.DataFrame:
    path = Path(__file__).resolve().parent.parent.parent / PARQUET_DATA_DIR
    parquet_files = sorted(Path(path).glob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError("No batch files found.")

    dfs = [pd.read_parquet(file) for file in parquet_files]

    return pd.concat(dfs, ignore_index=True)

def clear_tmp(directory):
    project_root = Path(__file__).resolve().parent.parent.parent
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

def save_result(df: pd.DataFrame, output_format: str) -> Path:
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"Output format must be one of {OUTPUT_FORMATS}")

    project_root = Path(__file__).resolve().parent.parent.parent
    output_dir = project_root / DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_path = output_dir / f"{timestamp}.{output_format}"
    if output_format == "csv":
        df.to_csv(output_path, index=False)
    else:
        df.to_parquet(output_path, index=False)
    return output_path














