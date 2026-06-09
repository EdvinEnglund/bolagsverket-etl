from bs4 import BeautifulSoup
import pandas as pd

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

