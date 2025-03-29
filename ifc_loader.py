import ifcopenshell

class IfcProject:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.model = ifcopenshell.open(file_path)

    def get_gfa_elements(self, ifc_entity = "IfcSpace", attribute = "Name", name = "GFA", quantity = "NetFloorArea"):
        """Extracts all Spaces that are Gross Floor Area (GFA) elements.
        """
        return [el for el in self.model.by_type(ifc_entity) if el.Name == name and el.NetFloorArea == quantity]
    

        
        