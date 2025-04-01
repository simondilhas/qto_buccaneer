import pandas as pd
from pathlib import Path
import sys

src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.enrich import enrich_ifc_with_df

def main():
    # Load enrichment data
    file = "src/qto_buccaneer/configs/enrichment_space_table.xlsx"
    df_enrichment = pd.read_excel(file)
    print("Enrichment DataFrame:")
    print(df_enrichment)

    # Enrich IFC file - the function now handles the GlobalId mapping internally
    enriched_ifc_path = enrich_ifc_with_df(
        ifc_file="examples/Mustermodell V1_abstractBIM.ifc",
        df_for_ifc_enrichment=df_enrichment,
        key="LongName"
    )

    print(f"\nCreated enriched IFC file: {enriched_ifc_path}")

if __name__ == "__main__":
    main()