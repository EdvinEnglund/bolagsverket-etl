"""Summarize report filenames with python -m scripts.report_stats."""

import re
from pathlib import Path


EXAMPLE_XML_DIR = Path(__file__).resolve().parents[1] / "data" / "example-xmls"
REPORT_FILENAME = re.compile(
    r"(?P<org_no>[0-9]{10})(?P<auditor>_AR)?"
    r"(?:_(?P<filing>(?:[0-9]{4}-[0-9]{2}-[0-9]{2}|unknown)_.+))?_report\.xml"
)


def print_report_stats(directory=EXAMPLE_XML_DIR):
    companies = set()
    financial_reports = set()
    auditor_remarks = set()

    for path in directory.iterdir():
        match = REPORT_FILENAME.fullmatch(path.name)
        if match is None or not path.is_file():
            continue

        org_no = match["org_no"]
        filing = (org_no, match["filing"])
        companies.add(org_no)
        if match["auditor"]:
            auditor_remarks.add(filing)
        else:
            financial_reports.add(filing)

    company_count = len(companies)
    report_count = len(financial_reports)
    matched_count = len(financial_reports & auditor_remarks)
    reports_per_company = f"{report_count / company_count:.2f}" if company_count else "N/A"
    matched_share = f"{matched_count / report_count:.2%}" if report_count else "N/A"

    print(f"Total unique companies: {company_count}")
    print(f"Total financial reports: {report_count}")
    print(f"Total auditor remark documents: {len(auditor_remarks)}")
    print(f"Average financial reports per company: {reports_per_company}")
    print(f"Share of financial reports with an auditor remark: {matched_share}")


if __name__ == "__main__":
    print_report_stats()
