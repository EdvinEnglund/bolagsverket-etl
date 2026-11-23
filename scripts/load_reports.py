"""Save Bolagsverket report XMLs with python -m scripts.load_reports."""

import asyncio
from pathlib import Path
from urllib.parse import quote

from src.config.config import CONCURRENCY
from src.extract.bv_client import BVClient, unzip_documents
from src.load.org_numbers import load_org_numbers
from src.transform.document_classifier import DocumentType, identify_documents


EXAMPLE_XML_DIR = Path(__file__).resolve().parents[1] / "data" / "example-xmls"


async def save_company_reports(client, org_no, save_dir):
    async for metadata, zip_bytes in client.iter_all_doc_zips(org_no):
        documents = unzip_documents(zip_bytes)
        if not documents:
            continue

        period_end = quote(metadata.get("rapporteringsperiodTom") or "unknown", safe="")
        doc_id = quote(str(metadata["dokumentId"]), safe="")
        suffix = f"{period_end}_{doc_id}"

        classified = identify_documents(documents, f"{org_no} / {metadata['dokumentId']}")
        report = classified.get(DocumentType.ANNUAL_REPORT)
        if report is not None:
            report_path = save_dir / f"{org_no}_{suffix}_report.xml"
            report_path.write_text(report, encoding="utf-8")
            print(f"Saved XML report to: {report_path}")

        auditor_report = classified.get(DocumentType.AUDITOR_REPORT)
        if auditor_report is not None:
            remark_path = save_dir / f"{org_no}_AR_{suffix}_report.xml"
            remark_path.write_text(auditor_report, encoding="utf-8")
            print(f"Saved auditor's XML to: {remark_path}")


async def load_reports(org_nos, save_dir=EXAMPLE_XML_DIR):
    save_dir = Path(save_dir)
    org_nos = list(dict.fromkeys(str(org_no) for org_no in org_nos))
    if not org_nos:
        return

    save_dir.mkdir(parents=True, exist_ok=True)
    client = BVClient()
    try:
        # Keep the number of active company downloads bounded.
        for start in range(0, len(org_nos), CONCURRENCY):
            async with asyncio.TaskGroup() as group:
                for org_no in org_nos[start:start + CONCURRENCY]:
                    group.create_task(save_company_reports(client, org_no, save_dir))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(load_reports(load_org_numbers()))
