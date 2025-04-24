import sys
from pathlib import Path
import pandas as pd

# Add src directory to path
src_dir = str(Path(__file__).parent.parent / "src")
sys.path.append(src_dir)

from qto_buccaneer.enrich import enrich_ifc_with_df

def main():
    # Project configuration
    projects_dir = Path(__file__).parent
    project_name = "001_example_project__public"
    ifc_file = projects_dir / project_name / "output" / "00_abstractBIM" / "Mustermodell V1_abstractBIM.ifc"
    
    # Verify input file exists
    ifc_file_str = str(ifc_file)
    if not ifc_file.exists():
        raise FileNotFoundError(f"IFC file not found at: {ifc_file_str}")
    
    print(f"Processing IFC file: {ifc_file_str}")
    
    # Create output directory
    output_dir = projects_dir / project_name / "output" / "01_enriched"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load enrichment data
    enrichment_file = Path(__file__).parent.parent / "src" / "qto_buccaneer" / "configs" / "enrichment_space_table.xlsx"
    if not enrichment_file.exists():
        raise FileNotFoundError(f"Enrichment file not found at: {enrichment_file}")
        
    df_enrichment = pd.read_excel(enrichment_file)
    print("\nEnrichment DataFrame:")
    print(df_enrichment)
    
    # Enrich IFC with additional data
    print("\nAdding enrichment data...")
    final_enriched_path = enrich_ifc_with_df(
        ifc_file=ifc_file_str,
        df_for_ifc_enrichment=df_enrichment,
        key="LongName",
        pset_name="Pset_AdditionalData",
        output_dir=str(output_dir)  
        
    )
    
    print(f"\nCreated enriched IFC file: {final_enriched_path}")

if __name__ == "__main__":
    main()