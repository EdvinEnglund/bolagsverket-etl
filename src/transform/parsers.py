import re
from datetime import date

from bs4 import BeautifulSoup
import pandas as pd

OVERVIEW_HEADING = re.compile(r"^fler[åa]rs[öo]versikt\b", re.IGNORECASE)
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
OVERVIEW_LABEL_TAGS = HEADING_TAGS | {"p", "span", "td", "th", "caption"}
AUDIT_FIELDS = {
    "UttalandeText": "audit_opinion_text",
    "AndraKravLagForfattningUttalandenText": "audit_other_legal_opinion_text",
    "AndraKravLagForfattningAnmarkning": "audit_remarks_text",
    "VasentligOsakerhetsfaktorAvseendeAntagandetFortsattDrift": "audit_going_concern_text",
    "OvrigaUpplysningar": "audit_other_disclosures_text",
    "AndraKravLagForfattningOvrigUpplysning": "audit_other_disclosures_text",
    "RevisionAvslutandeDatum": "audit_completion_date",
}
SWEDISH_MONTHS = (
    "januari", "februari", "mars", "april", "maj", "juni",
    "juli", "augusti", "september", "oktober", "november", "december",
)


def _normalize_audit_date(value):
    """Convert ISO dates and Swedish day-month-year text to YYYY-MM-DD."""
    try:
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return date.fromisoformat(value).isoformat()
        match = re.fullmatch(r"([0-9]{1,2})\s+(\w+)\s+([0-9]{4})", value.casefold())
        if match:
            day, month, year = match.groups()
            return date(int(year), SWEDISH_MONTHS.index(month) + 1, int(day)).isoformat()
    except ValueError:
        pass
    return None


def _find_overview_tables(soup):
    overview_tables = set()
    for table in soup.find_all("table"):
        marker = f"{table.get('id', '')} {table.get('class', '')}".casefold()
        if "flerarsoversikt" in marker or "flerårsöversikt" in marker:
            overview_tables.add(id(table))

    for label in soup.find_all(OVERVIEW_LABEL_TAGS):
        if not OVERVIEW_HEADING.match(label.get_text(" ", strip=True)):
            continue

        table = label.find_parent("table")
        if table is not None:
            overview_tables.add(id(table))
            continue

        # Some templates place the heading immediately before the overview table.
        for following in label.find_all_next(HEADING_TAGS | {"table"}):
            if following.name in HEADING_TAGS:
                break
            if following.find("ix:nonFraction"):
                overview_tables.add(id(following))
                break

    return overview_tables


def parse_report(xml_string):
    return _parse_report(xml_string)


def parse_flerarsoversikt(xml_string):
    """Extract numeric iXBRL facts from the flerårsöversikt."""
    return _parse_report(xml_string, overview_only=True)


def parse_report_without_flerarsoversikt(xml_string):
    """Extract numeric iXBRL facts outside the flerårsöversikt."""
    return _parse_report(xml_string, overview_only=False)


def _parse_report(xml_string, *, overview_only=None):
    result = {}
    try:
        soup = BeautifulSoup(xml_string, "xml")

        if overview_only is not None:
            overview_tables = _find_overview_tables(soup)

        for tag in soup.find_all("ix:nonFraction"):
            if overview_only is not None:
                in_overview = any(id(parent) in overview_tables for parent in tag.parents)
                if in_overview != overview_only:
                    continue

            name = tag.get("name")
            ctx = tag.get("contextRef")
            if not name or not ctx:
                continue

            # remove "se-gen-base:" from columns name
            start_index = len("se-gen-base:")
            key = f"{name[start_index::]}_{ctx.upper()}"

            value_string = tag.get_text(strip=True)

            try:
                value = float(
                    value_string.replace(" ", "")
                                .replace(",", ".")
                )
            except ValueError:
                print(f"Could not parse value '{value_string}' for key '{key}'")
                continue

            result[key] = value

    except Exception as e:
        print(f"XML parsing failed: {e}")

    return result


def _audit_fact_text(fact, continuations):
    parts = []
    seen = set()
    while fact is not None:
        for excluded in fact.find_all("ix:exclude"):
            excluded.extract()
        parts.append(fact.get_text(" ", strip=True))
        next_id = fact.get("continuedAt")
        if not next_id or next_id in seen:
            break
        seen.add(next_id)
        fact = continuations.get(next_id)
    return " ".join(part for part in parts if part)


def parse_auditor_report(xml_string, *, annual_report=None):
    """Extract tagged audit fields, including audit text embedded in an annual report."""
    result = dict.fromkeys(AUDIT_FIELDS.values())
    result["audit_parse_status"] = "missing" if xml_string is None else "unparsed"
    source = annual_report if xml_string is None else xml_string
    if not source:
        return result

    soup = BeautifulSoup(source, "xml")
    continuations = {
        tag["id"]: tag for tag in soup.find_all("ix:continuation", id=True)
    }
    values = {}
    for fact in soup.find_all("ix:nonNumeric"):
        prefix, _, concept = fact.get("name", "").partition(":")
        if prefix != "se-ar-base" or concept not in AUDIT_FIELDS:
            continue
        text = _audit_fact_text(fact, continuations)
        if text:
            values.setdefault(AUDIT_FIELDS[concept], []).append(text)

    if values:
        completion_dates = {
            _normalize_audit_date(text)
            for text in values.pop("audit_completion_date", [])
        }
        if len(completion_dates) == 1:
            result["audit_completion_date"] = completion_dates.pop()
        result.update(
            (column, "\n\n".join(dict.fromkeys(texts))) for column, texts in values.items()
        )
        result["audit_parse_status"] = "parsed"
    return result


def parse_bv_data(company_info):
    try:
        org = company_info["organisationer"][0]

        result = {
            "org_no": org["organisationsidentitet"]["identitetsbeteckning"],
            "name": org["organisationsnamn"]["organisationsnamnLista"][0]["namn"],
            "registration_date": org["organisationsdatum"]["registreringsdatum"],
            "avregistreradOrganisation": org.get("avregistreradOrganisation"),
            "avregistreringsorsak": org.get("avregistreringsorsak"),
            "pagaendeAvvecklingsEllerOmstruktureringsforfarande": org.get(
                "pagaendeAvvecklingsEllerOmstruktureringsforfarande"
            ),
            "postnummer": (
                org.get("postadressOrganisation", {})
                   .get("postadress", {})
                   .get("postnummer")
            ),
            "beskrivning": (
                org.get("verksamhetsbeskrivning", {})
                   .get("beskrivning")
            ),
        }

        sni_codes = [
            sni["kod"].strip()
            for sni in org["naringsgrenOrganisation"]["sni"]
            if sni["kod"].strip()
        ]

        for i in range(4):
            result[f"SNI{i}"] = sni_codes[i] if i < len(sni_codes) else None
        return result

    except Exception as e:
        print(f"Could not parse org info: {e}")
        return {}


