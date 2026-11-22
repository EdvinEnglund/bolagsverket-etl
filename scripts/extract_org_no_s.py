from pathlib import Path
import pandas as pd

#######################################################################################
# Utility function to extract org. numbers from csv's downloaded from bolagsfilter.se #
#######################################################################################

def extract_orgnrs():
    project_root = Path(__file__).resolve().parent.parent
    data_dir = Path("data/example_csvs")

    example_list = []

    for i in range(1, 7):
        file_path = project_root / data_dir / f"screener_sida{i}.csv"
        df = pd.read_csv(file_path)

        if "org_nr" in df.columns:
            example_list.extend(df["org_nr"].dropna().tolist())

    for i in range(len(example_list)):
        example_list[i] = str(example_list[i])

    print(example_list)

if __name__ == "__main__":
    extract_orgnrs()
