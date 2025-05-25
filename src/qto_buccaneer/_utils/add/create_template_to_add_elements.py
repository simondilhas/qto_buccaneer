import pandas as pd
import json
from pathlib import Path
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from qto_buccaneer._utils.report.excel_styling import ExcelLayoutConfig
import yaml
import os

def create_template_to_add_elements(json_path: str, output_excel_path: str, workflow_config_path: str, 
                         building_name: str = None, layout_config: ExcelLayoutConfig = None):
    """Create separate clean templates for specified IFC entities based on existing metadata.
    
    Args:
        json_path (str): Path to the input JSON file
        output_excel_path (str): Base path for output Excel files
        workflow_config_path (str): Path to the workflow config YAML file
        building_name (str, optional): Name of the building to use as file prefix
        layout_config (ExcelLayoutConfig, optional): Configuration for Excel styling
    """
    if layout_config is None:
        layout_config = ExcelLayoutConfig()
    
    # Read workflow config
    with open(workflow_config_path, 'r') as f:
        workflow_config = yaml.safe_load(f)
    
    # Get IFC entities and their required columns from config
    ifc_entities = list(workflow_config['add'].keys())
    entity_necessary_columns = {
        entity: workflow_config['add'][entity]['required_columns']
        for entity in ifc_entities
    }

    with open(json_path, 'r') as f:
        metadata = json.load(f)['elements']

    # Separate column values by entity type
    entity_column_values = {entity: {} for entity in ifc_entities}
    entity_columns = {entity: set() for entity in ifc_entities}

    # Collect columns and values for each entity type
    for obj_id, obj_data in metadata.items():
        entity_type = obj_data.get('IfcEntity')
        if entity_type in ifc_entities:
            # First add required columns
            entity_columns[entity_type].update(entity_necessary_columns[entity_type])
            # Then add any additional columns from the data
            entity_columns[entity_type].update(obj_data.keys())
            
            for key, value in obj_data.items():
                if key not in entity_column_values[entity_type]:
                    entity_column_values[entity_type][key] = set()
                if value is not None and value != "":
                    entity_column_values[entity_type][key].add(str(value))

    # Sort values for each entity type
    entity_column_values = {
        entity: {k: sorted(list(v)) for k, v in values.items()}
        for entity, values in entity_column_values.items()
    }
    
    # Sort columns to put necessary columns first
    entity_columns = {
        entity: (
            # First add necessary columns in the order they appear in the config
            entity_necessary_columns[entity] +
            # Then add remaining columns in alphabetical order
            sorted([col for col in columns if col not in entity_necessary_columns[entity]])
        )
        for entity, columns in entity_columns.items()
    }

    print("\nAnalysis of unique values per column:")
    for entity_type in ifc_entities:
        print(f"\n{entity_type} columns:")
        for col in entity_columns[entity_type]:
            if col in entity_column_values[entity_type]:
                num_values = len(entity_column_values[entity_type][col])
                print(f"{col}: {num_values} unique values")

    # Create separate workbooks for each entity type
    for entity_type in ifc_entities:
        if not entity_columns[entity_type]:
            print(f"No data found for {entity_type}, skipping...")
            continue

        # Create new workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = entity_type
        ws_lists = wb.create_sheet('Lists')

        # Add headers
        for col_idx, col_name in enumerate(entity_columns[entity_type], 1):
            ws.cell(row=1, column=col_idx, value=col_name)

        # Add a note about adding new values
        ws_lists.cell(row=1, column=1, value="Note: You can add new values to these lists by typing them directly in the cells below the existing values.")
        ws_lists.merge_cells('A1:D1')  # Merge cells for the note
        ws_lists.cell(row=1, column=1).font = openpyxl.styles.Font(bold=True, italic=True)
        
        # Add lists (only for this entity type)
        list_positions = {}
        current_row = 3  # Start after the note
        for col_name, values in entity_column_values[entity_type].items():
            if values:
                ws_lists.cell(row=current_row, column=1, value=col_name)
                for i, value in enumerate(values, start=2):
                    ws_lists.cell(row=current_row, column=i, value=value)
                list_positions[col_name] = (current_row, 2, 1 + len(values))
                current_row += 2

        # Apply styling
        # Apply header styling
        if layout_config.bold_headers:
            for col_idx, col_name in enumerate(entity_columns[entity_type], 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = openpyxl.styles.Font(bold=True)
                
                # Apply yellow background for necessary columns from config
                if col_name in entity_necessary_columns[entity_type]:
                    cell.fill = openpyxl.styles.PatternFill(
                        start_color='FFFF00',  # Yellow
                        end_color='FFFF00',
                        fill_type='solid'
                    )
                else:
                    cell.fill = openpyxl.styles.PatternFill(
                        start_color=layout_config.header_color,
                        end_color=layout_config.header_color,
                        fill_type='solid'
                    )

        # Apply borders
        if layout_config.horizontal_lines or layout_config.vertical_lines:
            for row in ws.iter_rows():
                for cell in row:
                    border = openpyxl.styles.Border()
                    if layout_config.horizontal_lines:
                        border.top = openpyxl.styles.Side(style='thin')
                        border.bottom = openpyxl.styles.Side(style='thin')
                    if layout_config.vertical_lines:
                        border.left = openpyxl.styles.Side(style='thin')
                        border.right = openpyxl.styles.Side(style='thin')
                    cell.border = border

        # Set row height if specified
        if layout_config.row_height:
            for row in ws.iter_rows():
                ws.row_dimensions[row[0].row].height = layout_config.row_height

        # Auto-adjust column widths
        if layout_config.auto_column_width:
            for column in ws.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column_letter].width = adjusted_width

        # Modify the data validation section to skip Qset columns
        for col_idx, col_name in enumerate(entity_columns[entity_type], 1):
            # Skip columns that start with 'Qset'
            if col_name.startswith("Qto"):
                continue
            if col_name in entity_column_values[entity_type] and entity_column_values[entity_type][col_name]:
                if col_name in list_positions:
                    row, start_col, end_col = list_positions[col_name]
                    start_letter = get_column_letter(start_col)
                    end_letter = get_column_letter(end_col)
                    formula = f'=Lists!${start_letter}${row}:${end_letter}${row}'
                    validation = DataValidation(type="list", formula1=formula)
                    ws.add_data_validation(validation)

                    col_letter = get_column_letter(col_idx)
                    validation.add(f"{col_letter}2:{col_letter}1000")

        # Add a note about input options
        ws_lists.cell(row=1, column=1, value="Note: You can either select from the existing values or type a new value directly in the cells.")
        ws_lists.merge_cells('A1:D1')  # Merge cells for the note
        ws_lists.cell(row=1, column=1).font = openpyxl.styles.Font(bold=True, italic=True)

        # Save the workbook with building name prefix at the beginning, in the correct folder
        base_dir = os.path.dirname(output_excel_path)
        if building_name:
            filename = f"{building_name}_add_{entity_type}.xlsx"
        else:
            # Use the base name of the template, but with enrich and entity type
            base_filename = os.path.splitext(os.path.basename(output_excel_path))[0]
            filename = f"{base_filename}_add_{entity_type}.xlsx"
        output_path = os.path.join(base_dir, filename)
        wb.save(output_path)
        print(f"Created Excel template for {entity_type}: {output_path}")


# Example usage
if __name__ == "__main__":
    # Get the current script's directory
    script_dir = Path(__file__).parent
    
    # Define paths relative to the script directory
    json_path = script_dir / "test_data" / "ifc_model_metadata.json"
    template_excel = script_dir / "test_data" / "metadata_template.xlsx"
    updated_json = script_dir / "test_data" / "updated_metadata.json"
    workflow_config = script_dir / "test_data" / "00_workflow_config.yaml"
    
    # Define building name
    building_name = "Seefeld"  # Optional
    
    # Create template with custom styling
    layout_config = ExcelLayoutConfig(
        horizontal_lines=True,
        vertical_lines=True,
        bold_headers=True,
        auto_column_width=True,
        row_height=20,
        alternating_colors=True,
        header_color='E0E0E0'
    )
    create_template_to_add_elements(str(json_path), str(template_excel), str(workflow_config), 
                         building_name, layout_config)
    
    # After filling out the Excel, import back to JSON
    # import_excel_to_json(json_path, template_excel, updated_json, ifc_entities)