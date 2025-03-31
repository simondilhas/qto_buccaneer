import ifcopenshell

ifc_file = ifcopenshell.open("examples/Mustermodell V1_abstractBIM.ifc")

spaces = ifc_file.by_type("IfcSpace")

# Create a set to store unique LongNames
unique_longnames = set()

for space in spaces:
    if space.LongName:  # Only add non-None values
        unique_longnames.add(space.LongName)

# Print unique LongNames
for longname in unique_longnames:
    print(f"{longname}")
