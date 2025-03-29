import ifcopenshell

ifc_file = ifcopenshell.open("tests/help.ifc")

spaces = ifc_file.by_type("IfcSpace")

for space in spaces:
    print(f"Space: {space.Name}, GlobalId: {space.GlobalId}")
    for rel in space.IsDefinedBy:
        qto = getattr(rel, "RelatingPropertyDefinition", None)
        if qto and qto.is_a("IfcElementQuantity") and qto.Name == "Qto_SpaceBaseQuantities":
            for quantity in qto.Quantities:
                if quantity.Name in ["NetFloorArea", "GrossFloorArea"]:
                    print(f"  {quantity.Name}: {quantity.NominalValue.wrappedValue}")
