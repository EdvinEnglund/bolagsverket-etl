#Hello world
from fetchers import get_token, get_latest_report, get_bv_data
from parsers import parse_report, parse_bv_data
import pandas as pd

from src.fetchers import save_report_file

def run_main_pipeline(org_nos):
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
    org_nos = ["5568808686",
              "5568649478",
              "5565540035",
              "5566086483",
              "5590892542",
              "5564363421",
              "5592565096"] # index example number

    org_no = org_nos[0]
    token = get_token()

    report = get_latest_report(token, org_no)
    save_report_file(report, org_no)
    parsed_report = parse_report(report)

"""
    output = run_main_pipeline(org_nos)

    for key, value in parsed_report.items():
        print(f"{key}:      {value}")

    print(output.head())

"""