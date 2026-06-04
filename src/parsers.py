from bs4 import BeautifulSoup
import pandas as pd
from fetchers import get_token, get_latest_report, get_bv_data

def parse_report(xml_string):
    result = {}
    try:
        soup = BeautifulSoup(xml_string, "xml")

        for tag in soup.find_all("ix:nonFraction"):

            name = tag.get("name")
            ctx = tag.get("contextRef")
            if not name or not ctx:
                continue

            # remove "se-gen-base:" from columns name
            start_index = len("se-gen-base:")
            key = f"{name[start_index::]}_{ctx.upper()}"

            value_string = tag.get_text(strip=True)
            value = float(value_string.replace(" ", ""))

            result[key] = value

    except:
        print("XML parsing failed")

    return result

def parse_reports(token, org_nos):
    rows = []

    for org_no in org_nos:
        report = get_latest_report(token, org_no)
        if not report:
            continue
        row = parse_report(report)
        rows.append(row)

    if len(rows) == 0:
        return pd.DataFrame()

    return pd.DataFrame(rows)

def parse_bv_data(company_info):
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

def get_merged_data(org_nos):
    #ADD TOKEN REGENERATOR LOGIC HERE
    token = get_token()
    rows = []
    for org_no in org_nos:
        print(f"Loading {org_no}...")
        report = get_latest_report(token, org_no)

        if not report:
            continue

        parsed_report = parse_report(report)
        company_info = get_bv_data(token, org_no)
        parsed_company_info = parse_bv_data(company_info)

        row = {
            **parsed_company_info,
            **parsed_report
        }
        rows.append(row)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    org_nos = ["5568808686", "5568649478", "5565540035", "5566086483", "5590892542", "5564363421"]
    #token = get_token()
    #df = parse_reports(token, org_nos)
    company_df = get_merged_data(org_nos)
    print(company_df)
    # SHow NaNs per columns
    #print(df.isna().sum())

    #print(df.head())

    #print((df.notna().all()).sum())

