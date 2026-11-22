"""Identify Bolagsverket filing documents from their XBRL schema references."""

import logging
from enum import Enum
from urllib.parse import urlsplit
from xml.etree import ElementTree


logger = logging.getLogger(__name__)
SCHEMA_REF = "{http://www.xbrl.org/2003/linkbase}schemaRef"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
ANNUAL_SCHEMAS = ("se-k2-risbs-", "se-k3-risbs-", "se-k3-rfibs-", "se-k3k-risbs-")
AUDITOR_SCHEMAS = ("se-ar-rar-", "se-ar-rarc-")


class DocumentType(Enum):
    ANNUAL_REPORT = "annual report"
    AUDITOR_REPORT = "auditor report"


def classify_document(document: str) -> DocumentType | None:
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError:
        return None

    schemas = [
        urlsplit(ref.get(XLINK_HREF, "")).path.rsplit("/", 1)[-1]
        for ref in root.iter(SCHEMA_REF)
    ]
    # Some annual reports include the auditor's report in the same XML.
    if any(schema.startswith(ANNUAL_SCHEMAS) for schema in schemas):
        return DocumentType.ANNUAL_REPORT
    if any(schema.startswith(AUDITOR_SCHEMAS) for schema in schemas):
        return DocumentType.AUDITOR_REPORT
    return None


def identify_documents(documents, filing: str) -> dict[DocumentType, str]:
    """Return each role only when exactly one document matches it."""
    matches = {document_type: [] for document_type in DocumentType}
    for index, document in enumerate(documents, start=1):
        document_type = classify_document(document)
        if document_type is None:
            logger.warning("%s: could not classify XML document %s", filing, index)
            continue
        matches[document_type].append(document)

    identified = {}
    for document_type, candidates in matches.items():
        if len(candidates) == 1:
            identified[document_type] = candidates[0]
        elif candidates:
            logger.warning("%s: found multiple %s documents", filing, document_type.value)
    return identified
