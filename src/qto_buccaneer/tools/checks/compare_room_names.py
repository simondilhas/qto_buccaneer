from qto_buccaneer.utils._result_bundle import ResultBundle
import pandas as pd
from typing import Optional


def _extract_ifc_rooms(metadata_df: pd.DataFrame, room_name_column: str) -> tuple[set, pd.DataFrame]:
    """Extract and normalize room names from IFC metadata."""
    ifc_spaces_df = metadata_df[metadata_df['IfcEntity'] == 'IfcSpace']
    ifc_rooms = set(ifc_spaces_df[room_name_column].dropna().str.lower().unique())
    return ifc_rooms, ifc_spaces_df

def _extract_excel_rooms(target_df: pd.DataFrame, room_name_column: str) -> set:
    """Extract and normalize room names from target program."""
    return set(target_df[room_name_column].dropna().str.lower().unique())

def _create_comparison_df(
    ifc_rooms: set,
    excel_rooms: set,
    ifc_spaces_df: pd.DataFrame,
    actual_room_name_column: str
) -> pd.DataFrame:
    """Create detailed comparison DataFrame with room status and GlobalIds."""
    all_rooms = ifc_rooms.union(excel_rooms)
    data = []
    
    for room in sorted(all_rooms):
        room_data = {
            "Room Name": room,
            "Status": _get_room_status(room, ifc_rooms, excel_rooms),
            "GlobalId": _get_room_global_id(room, ifc_rooms, ifc_spaces_df, actual_room_name_column)
        }
        data.append(room_data)
    
    return pd.DataFrame(data)

def _get_room_status(room: str, ifc_rooms: set, excel_rooms: set) -> str:
    """Determine the status of a room in the comparison."""
    if room in ifc_rooms and room in excel_rooms:
        return "In Both"
    elif room in ifc_rooms:
        return "Only in IFC"
    else:
        return "Only in Excel"

def _get_room_global_id(
    room: str,
    ifc_rooms: set,
    ifc_spaces_df: pd.DataFrame,
    actual_room_name_column: str
) -> str:
    """Get the GlobalId for a room if it exists in IFC."""
    if room in ifc_rooms:
        ifc_room = ifc_spaces_df[ifc_spaces_df[actual_room_name_column].str.lower() == room]
        if not ifc_room.empty:
            return ifc_room["GlobalId"].iloc[0]
    return ""

def _create_summary_data(ifc_rooms: set, excel_rooms: set) -> dict:
    """Create summary data for the ResultBundle.
    
    Status definitions:
    - success: No rooms in Excel that aren't in IFC
    - additional roomtypes used: Rooms exist only in IFC
    """
    rooms_only_in_ifc = list(ifc_rooms - excel_rooms)
    rooms_only_in_excel = list(excel_rooms - ifc_rooms)
    
    # Determine status
    if len(rooms_only_in_excel) == 0:
        status = "success"
    elif len(rooms_only_in_ifc) > 0:
        status = "additional roomtypes used"
    else:
        status = "error"
    
    return {
        "room_comparison": {
            "status": status,
            "summary": {
                "target_rooms": len(excel_rooms),
                "actual_rooms": len(ifc_rooms),
                "additional_rooms": len(rooms_only_in_ifc),
                "missing_rooms": len(rooms_only_in_excel)
            },
            "additional_rooms": sorted(rooms_only_in_ifc),
            "missing_rooms": sorted(rooms_only_in_excel)
        }
    }

def _export_to_excel(result_bundle: ResultBundle, output_dir: str, building_name: Optional[str]) -> None:
    """Export the comparison results to Excel."""
    building_prefix = f"{building_name}_" if building_name else ""
    output_path = f"{building_prefix}room_name_comparison.xlsx"
    result_bundle.save_excel(output_path)

def _create_error_result_bundle(error_message: str) -> ResultBundle:
    """Create a ResultBundle for error cases."""
    error_data = {
        "room_comparison": {
            "status": "error",
            "summary": f"Error comparing room names: {error_message}",
            "target": {},
            "ifc": {}
        }
    }
    return ResultBundle(dataframe=None, json=error_data)