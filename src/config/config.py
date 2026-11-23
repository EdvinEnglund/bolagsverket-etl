from pathlib import Path
BV_REQUESTS_PER_SECOND = 1.75
BV_MAX_ATTEMPTS = 5
BV_THROTTLE_BACKOFF_SECONDS = 5
BATCH_SIZE = 10
DONE_FILE_DIR = Path("data/tmp/done")
PARQUET_DATA_DIR = Path("data/tmp/parquet_batches")
DEFAULT_OUTPUT_DIR = Path("data/output")
CONCURRENCY = 10
