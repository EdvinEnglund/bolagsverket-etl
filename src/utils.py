from pathlib import Path


def save_report_file(report, org_no):
    try:
        if len(report) == 0:
            print("No report to save")
            return ""

        project_root = Path(__file__).resolve().parent.parent
        save_dir = project_root / "data" / "example-xmls"
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"{org_no}_report.xml"
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"Saved XML report to: {save_path}")

    except:
        print("Couldn't save report")
    return








