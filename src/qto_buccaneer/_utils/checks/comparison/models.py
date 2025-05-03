from dataclasses import dataclass
from typing import Optional
import pandas as pd
from qto_buccaneer._utils._result_bundle import ResultBundle

@dataclass
class ComparisonResult:
    """Main data structure for comparison results."""
    merged_df: pd.DataFrame
    return_values: list[str]
    area_target_column: Optional[str] = None
    area_actual_column: Optional[str] = None
    comparison_type: str = "area"  # "area" or "name"
    
    def to_result_bundle(self) -> ResultBundle:
        """Convert the comparison to a ResultBundle."""
        if self.comparison_type == "name":
            return self._create_name_comparison_bundle()
        return self._create_area_comparison_bundle()
    
    def _create_name_comparison_bundle(self) -> ResultBundle:
        """Create a ResultBundle for room name comparison."""
        actual_name_col = next(
            (col for col in self.merged_df.columns 
             if col.endswith('_actual') and ('name' in col.lower() or 'longname' in col.lower())),
            None
        )
        if actual_name_col is None:
            raise ValueError("No name column found in actual data")
        
        target_name_col = next(
            (col for col in self.merged_df.columns 
             if col.endswith('_target') and ('name' in col.lower() or 'longname' in col.lower())),
            None
        )
        if target_name_col is None:
            raise ValueError("No name column found in target data")
        
        ifc_rooms = set(self.merged_df[self.merged_df['status'] != 'missing'][actual_name_col].dropna().str.lower().unique())
        excel_rooms = set(self.merged_df[self.merged_df['status'] != 'extra'][target_name_col].dropna().str.lower().unique())
        
        rooms_only_in_ifc = list(ifc_rooms - excel_rooms)
        rooms_only_in_excel = list(excel_rooms - ifc_rooms)
        
        status = "success" if len(rooms_only_in_excel) == 0 else "additional roomtypes used" if len(rooms_only_in_ifc) > 0 else "error"
        
        summary_data = {
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
        
        return ResultBundle(dataframe=self.merged_df[self.return_values], json=summary_data)
    
    def _create_area_comparison_bundle(self) -> ResultBundle:
        """Create a ResultBundle for area comparison."""
        total_items = len(self.merged_df)
        items_within_tolerance = len(self.merged_df[self.merged_df['status'] == 'within_tolerance'])
        missing_items = len(self.merged_df[self.merged_df['status'] == 'missing'])
        extra_items = len(self.merged_df[self.merged_df['status'] == 'extra'])
        
        total_target_area = float(self.merged_df[self.area_target_column].sum())
        total_actual_area = float(self.merged_df[self.area_actual_column].sum())
        total_area_diff = float(total_actual_area - total_target_area)
        total_area_diff_pct = float((total_area_diff / total_target_area * 100) if total_target_area > 0 else 0)
        
        status = "failed" if missing_items > 0 else "warning" if extra_items > 0 else "passed" if items_within_tolerance == total_items else "warning"
        
        summary_data = {
            "name": "Target Program vs Actual Program",
            "status": str(status),
            "overview": {
                "total_items": int(total_items),
                "compliance_rate": float((items_within_tolerance / total_items * 100) if total_items > 0 else 0),
                "total_area": {
                    "target": float(total_target_area),
                    "actual": float(total_actual_area),
                    "difference_pct": float(total_area_diff_pct)
                }
            },
            "issues": {
                "missing": int(missing_items),
                "extra": int(extra_items),
                "out_of_tolerance": int(total_items - items_within_tolerance - missing_items - extra_items)
            }
        }
        
        return ResultBundle(dataframe=self.merged_df[self.return_values], json=summary_data)

@dataclass
class BuildingComparison:
    """Main data structure for building comparison results."""
    merged_df: pd.DataFrame
    return_values: list[str] 
    area_target_column: str
    area_actual_column: str
    
    def to_summary_yaml(self) -> dict:
        """Generate YAML summary of the comparison."""
        total_items = len(self.merged_df)
        items_within_tolerance = len(self.merged_df[self.merged_df['status'] == 'within_tolerance'])
        missing_items = len(self.merged_df[self.merged_df['status'] == 'missing'])
        extra_items = len(self.merged_df[self.merged_df['status'] == 'extra'])
        
        total_target_area = float(self.merged_df[self.area_target_column].sum())
        total_actual_area = float(self.merged_df[self.area_actual_column].sum())
        total_area_diff = float(total_actual_area - total_target_area)
        total_area_diff_pct = float((total_area_diff / total_target_area * 100) if total_target_area > 0 else 0)
        
        status = "failed" if missing_items > 0 else "warning" if extra_items > 0 else "passed" if items_within_tolerance == total_items else "warning"
        
        return {
            "name": "Target Program vs Actual Program",
            "status": str(status),
            "overview": {
                "total_items": int(total_items),
                "compliance_rate": float((items_within_tolerance / total_items * 100) if total_items > 0 else 0),
                "total_area": {
                    "target": float(total_target_area),
                    "actual": float(total_actual_area),
                    "difference_pct": float(total_area_diff_pct)
                }
            },
            "issues": {
                "missing": int(missing_items),
                "extra": int(extra_items),
                "out_of_tolerance": int(total_items - items_within_tolerance - missing_items - extra_items)
            }
        }
    
    def to_dict(self) -> dict:
        """Convert the comparison data to a dictionary."""
        return self.to_dataframe().to_dict(orient='records')
    
    def to_dataframe(self) -> pd.DataFrame:
        """Return the merged DataFrame with the specified columns."""
        return self.merged_df[self.return_values] 