from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ExcelLayoutConfig:
    """Configuration for Excel export layout."""
    horizontal_lines: bool = True
    vertical_lines: bool = False
    bold_headers: bool = True
    auto_column_width: bool = True
    row_height: Optional[float] = None
    alternating_colors: bool = False
    number_format: str = '#,##0.00'
    header_color: str = 'E0E0E0'  # Light gray
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {k: v for k, v in self.__dict__.items()}