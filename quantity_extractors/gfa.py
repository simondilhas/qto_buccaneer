import pandas as pd

def get_gfa_elements(project: ):
    """Extracts all elements relevant for GFA calculation (e.g. slabs, zones)."""
    return [el for el in project.get_slabs() if el.is_internal_floor()]

def calculate_gfa(elements):
    """Calculates GFA by summing areas of all internal floors."""
    return sum(el.gross_floor_area for el in elements)

def get_gfa_by_storey(project):
