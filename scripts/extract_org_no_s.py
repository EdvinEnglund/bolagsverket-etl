"""Append company registration numbers from Bolagsfilter CSV exports."""

import re
from pathlib import Path

import pandas as pd


def extract_orgnrs():
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data" / "example_csvs"
    output_path = project_root / "data" / "input" / "example_orgs.txt"

    existing_text = output_path.read_text(encoding="utf-8-sig") if output_path.exists() else ""
    seen = {line.strip().replace("-", "") for line in existing_text.splitlines()}
    new_org_nos = []

    for i in range(1, 7):
        file_path = data_dir / f"screener_sida{i}.csv"
        df = pd.read_csv(file_path, dtype={"org_nr": str})
        if "org_nr" not in df.columns:
            continue

        for value in df["org_nr"].dropna():
            org_no = value.strip()
            if not org_no:
                continue
            if not re.fullmatch(r"[0-9]{6}-?[0-9]{4}", org_no):
                raise ValueError(f"{file_path}: invalid company registration number {org_no!r}")

            org_no = org_no.replace("-", "")
            if org_no not in seen:
                seen.add(org_no)
                new_org_nos.append(org_no)

    if new_org_nos:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as file:
            if existing_text and not existing_text.endswith("\n"):
                file.write("\n")
            file.writelines(f"{org_no}\n" for org_no in new_org_nos)

    print(f"Added {len(new_org_nos)} registration numbers to {output_path}")


if __name__ == "__main__":
    extract_orgnrs()
