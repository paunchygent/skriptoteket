import glob
import json
import os

repo_dir = ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/"

print("Primitives in bottom right:")
for f in sorted(glob.glob(os.path.join(repo_dir, "Primitive.*.json"))):
    try:
        with open(f, "r") as fp:
            data = json.load(fp)
            if "Primitive" in data:
                p = data["Primitive"]
                x = p.get("x", 0)
                y = p.get("y", 0)
                if 950 <= x <= 1081 and 1700 <= y <= 2162:
                    print(f"  {os.path.basename(f)}: x={x:.1f}, y={y:.1f}")
    except Exception:
        pass

print("\nWalls in bottom right:")
for f in sorted(glob.glob(os.path.join(repo_dir, "Wall.*.json"))):
    try:
        with open(f, "r") as fp:
            data = json.load(fp)
            points = data.get("Wall", {}).get("drag_points", [])
            for p in points:
                if 950 <= p.get("x", 0) <= 1081 and 1700 <= p.get("y", 0) <= 2162:
                    print(f"  {os.path.basename(f)}")
                    break
    except Exception:
        pass
