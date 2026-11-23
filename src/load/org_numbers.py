import re
from pathlib import Path


DEFAULT_ORG_NUMBERS_PATH = Path(__file__).resolve().parents[2] / "data/input/example_orgs.txt"


def load_org_numbers(path: str | Path | None = None) -> list[str]:
    """Read one registration number per line and remove optional hyphens."""
    input_path = DEFAULT_ORG_NUMBERS_PATH if path is None else Path(path)
    org_nos = []

    with input_path.open(encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            org_no = line.strip()
            if not org_no:
                continue
            if not re.fullmatch(r"[0-9]{6}-?[0-9]{4}", org_no):
                raise ValueError(f"{input_path}:{line_number}: expected XXXXXX-XXXX or XXXXXXXXXX")
            org_nos.append(org_no.replace("-", ""))

    if not org_nos:
        raise ValueError(f"{input_path}: no company registration numbers found")
    return org_nos
