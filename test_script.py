import json


def get_points(filepath):
    with open(filepath, "r") as fp:
        data = json.load(fp)
        return [(p.get("x"), p.get("y")) for p in data.get("Wall", {}).get("drag_points", [])]


print("Apron1:")
for p in get_points(
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Apron1.json"
):
    print(f"  {p[0]:.1f}, {p[1]:.1f}")
print("Apron2:")
for p in get_points(
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Apron2.json"
):
    print(f"  {p[0]:.1f}, {p[1]:.1f}")
