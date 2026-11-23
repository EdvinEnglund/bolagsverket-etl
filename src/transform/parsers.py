import re

from bs4 import BeautifulSoup
import pandas as pd

OVERVIEW_HEADING = re.compile(r"^fler[åa]rs[öo]versikt\b", re.IGNORECASE)
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
OVERVIEW_LABEL_TAGS = HEADING_TAGS | {"p", "span", "td", "th", "caption"}


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


if __name__ == "__main__":
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    org_nos = ["5568808686", "5568649478", "5565540035", "5566086483", "5590892542", "5564363421"]
    #token = get_token()
    #df = parse_reports(token, org_nos)
    # SHow NaNs per columns
    #print(df.isna().sum())

    #print(df.head())

    #print((df.notna().all()).sum())

