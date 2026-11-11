# Bolagsverket ETL

A Python ETL (Extract, Transform, Load) pipeline that retrieves company information and digital annual reports from the Swedish Companies Registration Office (Bolagsverket) API for high-value datasets and turns them into tabular data for further analysis.

**Status: work in progress.** The core pipeline is implemented, but data validation, error handling, and preprocessing need further development before the output can serve as a reliable basis for analysis.

## Purpose

The project aims to simplify the collection and processing of company information and financial report data without manually handling each annual report. The goal is a reusable workflow that takes a list of company registration numbers and produces a dataset for company analysis and, eventually, machine learning.

The project covers API integration, asynchronous data collection, structured document parsing, and batch storage. The code is separated into extraction, transformation, and loading modules.

## Current functionality

1. **Authentication:** obtains an OAuth2 token using API credentials from environment variables.
2. **Data collection:** retrieves the document list for each company, selects the document with the latest reporting period end date, and downloads its ZIP archive. Company information is fetched separately.
3. **Transformation:** extracts XML/XHTML files and reads numeric `ix:nonFraction` fields from the annual report. These are combined with company registration number, name, registration date, postal code, business description, and up to four SNI industry classification codes.
4. **Storage:** writes intermediate results to temporary Parquet files and combines them into a Pandas DataFrame. The final result can be exported as Parquet or CSV.

Collection uses `asyncio` and `aiohttp`, with bounded concurrency and a shared request rate limiter. Retries with exponential backoff and jitter are implemented for failures including HTTP 429 responses.

### Output and limitations

The output contains one row per processed company. Financial columns are generated from report field names and context references, so different reports can produce different columns and missing values.

- The pipeline takes a supplied list of company registration numbers; it does not discover companies automatically.
- Companies without downloadable, readable XML/XHTML documents are skipped. PDF parsing is not supported.
- The first XML/XHTML file in an archive is treated as the annual report. More reliable document identification is still needed.
- The parser performs basic numeric extraction. Full handling of iXBRL signs, scaling, units, and reporting periods remains to be implemented.
- Auditor's reports are not yet analysed.
- A local record of processed companies supports resuming work, but currently an entire batch is marked as complete if it produces any results. This needs to be refined so failed companies can be retried correctly.
- Returning an empty dataset when no batch produces results is not yet supported.

## Technology

- **Python 3.12 or later** for the syntax used in the current code.
- **aiohttp, asyncio, and requests** for API calls and concurrency.
- **Beautiful Soup and lxml** for XML/iXBRL parsing.
- **Pandas and a Parquet engine such as PyArrow** for tabular processing and storage.
- **python-dotenv** for loading local API credentials.

## Running locally

You need API credentials with access to Bolagsverket's API for high-value datasets. The project does not yet include a dependency file with pinned versions; the commands below manually install the libraries used by the code.

Run from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install aiohttp requests python-dotenv beautifulsoup4 lxml pandas pyarrow
```

Create a local `.env` file in the project root:

```dotenv
BV_CLIENT=your_client_id
BV_SECRET=your_client_secret
```

The `.env` file is excluded from Git through `.gitignore`. Keep API credentials local.

Company registration numbers, batch size, concurrency, request rate, and paths are configured in `src/config/config.py`. Adjust `EXAMPLE_ORGS`, then run:

```bash
python -m src.main
```

The default run prints the result and execution time without saving a final output file (`save=False`). Temporary batch files and the record of processed companies are cleared at the end of a normal run.

To save the result, call the pipeline from Python:

```python
import asyncio
from src.main import run_pipeline

df = asyncio.run(
    run_pipeline(
        ["5568808686", "5568649478"],
        save=True,
        output_path="data/output/companies.parquet",
        file_format="parquet",
    )
)
```

For CSV export, use `file_format="csv"` and a path ending in `.csv`. If `output_path` is omitted, the file is saved with a timestamp in `data/output/`.

## Project structure

```text
src/
├── main.py               # Pipeline orchestration and batch processing
├── config/config.py      # Settings and example company registration numbers
├── extract/bv_client.py  # Authentication, API client, and rate limiting
├── transform/parsers.py  # Company information and report field parsing
├── load/load_utils.py    # Parquet batches, export, and progress tracking
└── utils/utils.py        # Document archive extraction
TODO.txt                  # Development notes
```

## Remaining work

The following areas remain, based on the development plan and limitations of the current implementation:

- **More robust execution:** add automatic token renewal for longer runs, shared retry logic, clearer error handling, and reliable HTTP session cleanup when execution is interrupted. Improve resuming at the company level and handle empty results.
- **Report data validation:** identify the correct documents within archives and improve iXBRL parsing so numeric values and their context are represented correctly.
- **Column selection through visual analysis in a notebook:** collect a sample of approximately 1,000 companies and use exploratory visual analysis in a notebook to identify and retain columns relevant to further analysis. Examine data coverage, missing-value patterns, and value distributions; evaluate removing columns with more than 80% missing values. Incorporate the resulting column selection and filtering rules into the pipeline.
- **Auditor's reports:** add support for identifying and parsing auditor's reports, and investigate whether auditor remarks can be represented in a separate column.
- **Machine learning preprocessing:** handle missing values and produce a more consistent dataset for subsequent modelling.
- **Usability and performance:** add command-line arguments, a progress indicator, and an estimated time remaining. Evaluate request rate, concurrency, and retry settings.
- **Testing and reproducibility:** add automated tests for parsing and error handling, document dependency versions, and introduce CI checks.
