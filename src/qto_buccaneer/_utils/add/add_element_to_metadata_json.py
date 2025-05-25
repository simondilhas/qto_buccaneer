import json
import pandas as pd
from pathlib import Path

def add_element_to_metadata_json(json_path: Path, excel_path: Path, output_json_path: Path, ifc_entities: list):
    """Import data from filled Excel templates back to JSON.
    
    Args:
        json_path (str): Path to the input JSON file
        excel_path (str): Base path for input Excel files
        output_json_path (str): Path for the output JSON file
        ifc_entities (list): List of IFC entity types to process
    """
    with open(json_path, 'r') as f:
        metadata = json.load(f)
    
    # Get the highest existing ID
    max_id = max([int(id) for id in metadata['elements'].keys()]) if metadata['elements'] else 0
    
    # Process each entity type
    for entity_type in ifc_entities:
        entity_excel_path = str(excel_path)
        print(f"Using Excel file: {entity_excel_path}")
        
        try:
            # Read Excel sheet
            df = pd.read_excel(entity_excel_path, sheet_name=entity_type)
            print(f"Excel columns: {df.columns.tolist()}")
            print(f"Number of rows in Excel: {len(df)}")
            
            # Process the data
            for index, row in df.iterrows():
                print(f"\nProcessing row {index}:")
                print(f"Row data: {row.to_dict()}")
                
                # Generate new ID if none exists
                if pd.isna(row['id']):
                    max_id += 1
                    obj_id = str(max_id)
                    print(f"Generated new ID: {obj_id}")
                else:
                    obj_id = str(int(row['id']))
                
                print(f"Processing ID: {obj_id}")
                print(f"ID exists in metadata: {obj_id in metadata['elements']}")
                
                if obj_id in metadata['elements']:
                    print(f"Updating existing element {obj_id}")
                    for column in df.columns:
                        if pd.notna(row[column]):
                            # Convert NaN to None for JSON compatibility
                            value = None if pd.isna(row[column]) else row[column]
                            metadata['elements'][obj_id][column] = value
                else:
                    print(f"Adding new element {obj_id}")
                    new_element = {
                        'id': int(obj_id),
                        'parent_id': None,
                        'GlobalId': None,  # Default to None instead of NaN
                        'IfcEntity': entity_type,
                        'Classifications': [],
                        'Systems': [],
                        'ConnectedFrom': [],
                        'ConnectedTo': [],
                        'ContainedInStructure': []
                    }
                    # Add any additional columns from the Excel
                    for column in df.columns:
                        if pd.notna(row[column]):
                            # Convert NaN to None for JSON compatibility
                            value = None if pd.isna(row[column]) else row[column]
                            new_element[column] = value
                    
                    metadata['elements'][obj_id] = new_element
                    print(f"Added new element with ID: {obj_id}")
        except FileNotFoundError:
            print(f"Warning: No Excel file found for {entity_type}")
            continue
        except Exception as e:
            print(f"Error processing Excel file: {str(e)}")
            continue
    
    # Save updated metadata
    with open(output_json_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"\nSaved updated metadata to: {output_json_path}")

if __name__ == "__main__":
    # Get the current script's directory
    script_dir = Path(__file__).parent
    print(f"Script directory: {script_dir}")

    building_name = "Seefeld"

    # Define paths relative to the script directory
    json_path = script_dir / "test_data" / "ifc_model_metadata.json"
    template_excel = script_dir / "test_data" / f"{building_name}_add_IfcSpace.xlsx"
    print(f"Template excel path: {template_excel}")
    print(f"Template excel exists: {template_excel.exists()}")
    
    updated_json = script_dir / "test_data" / f"{building_name}_updated_metadata.json"
    workflow_config = script_dir / "test_data" / "00_workflow_config.yaml"

    add_element_to_metadata_json(json_path, template_excel, updated_json, ["IfcSpace"])
    