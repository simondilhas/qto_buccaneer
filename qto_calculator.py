from typing import Optional

class QtoCalculator:
    def __init__(self, loader):
        self.loader = loader

    def sum_quantity(self, elements, qset: str, quantity_name: str) -> float:
        """
        Sums up a quantity value from a quantity set for a list of IFC elements.

        Args:
            elements: List of IFC elements (e.g. spaces).
            qset (str): Name of the quantity set (e.g. "Qto_SpaceBaseQuantities").
            quantity_name (str): Name of the quantity to sum (e.g. "NetFloorArea").

        Returns:
            float: The total sum of the found quantities.
        """
        total = 0.0

        for el in elements:
            for rel in getattr(el, "IsDefinedBy", []):
                qto = getattr(rel, "RelatingPropertyDefinition", None)
                if not qto or not qto.is_a("IfcElementQuantity") or qto.Name != qset:
                    continue
                for quantity in getattr(qto, "Quantities", []):
                    if quantity.Name == quantity_name:
                        try:
                            if quantity.is_a("IfcQuantityArea"):
                                value = quantity.AreaValue
                            elif quantity.is_a("IfcQuantityVolume"):
                                value = quantity.VolumeValue
                            elif quantity.is_a("IfcQuantityLength"):
                                value = quantity.LengthValue
                            else:
                                value = None

                            if value is not None:
                                total += value

                        except AttributeError:
                            # Log or skip if quantity is malformed
                            pass
        return total

    def calculate_gross_floor_area(
        self,
        value: str = "GrossArea",
        key: str = "Name",
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: str = "NetFloorArea"
    ) -> Optional[float]:
        """
        Automatically calculates the Gross Floor Area from IFC files, with default
        classifications and parameters aligned to the abstractBIM IFC conventions.

        Args:
            value (str): The classification or name to filter by. Defaults to "GFA".
            key (str): The attribute or property to filter on. Defaults to "Name".
            ifc_entity (str): The IFC entity type to search for. Defaults to "IfcSpace".
            pset_name (str): The property or quantity set. Defaults to "Qto_SpaceBaseQuantities".
            prop_name (str): The specific quantity or property name. Defaults to "NetFloorArea".

        Returns:
            float: The summed area value (0.0 if not found).
        """
        elements = self.loader.get_elements(key=key, value=value, ifc_entity=ifc_entity)
        return self.sum_quantity(elements, qset=pset_name, quantity_name=prop_name)
    
    def calculate_gross_floor_volume(
        self,
        value: str = "GrossVolume",
        key: str = "Name",
        ifc_entity: str = "IfcSpace",
        pset_name: str = "Qto_SpaceBaseQuantities",
        prop_name: str = "NetVolume"
    ) -> Optional[float]:
        """
        Automatically calculates the Gross Volume from IFC files, with default
        classifications and parameters aligned to the abstractBIM IFC conventions.

        Args:
            value (str): The classification or name to filter by. Defaults to "GFA".
            key (str): The attribute or property to filter on. Defaults to "Name".
            ifc_entity (str): The IFC entity type to search for. Defaults to "IfcSpace".
            pset_name (str): The property or quantity set. Defaults to "Qto_SpaceBaseQuantities".
            prop_name (str): The specific quantity or property name. Defaults to "NetFloorArea".

        Returns:
            float: The summed area value (0.0 if not found).
        """
        elements = self.loader.get_elements(key=key, value=value, ifc_entity=ifc_entity)
        return self.sum_quantity(elements, qset=pset_name, quantity_name=prop_name)
