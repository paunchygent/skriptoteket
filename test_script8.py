import glob
import json
import os

repo_dir = ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/"

print("All walls in shooter lane lower area:")
for f in sorted(glob.glob(os.path.join(repo_dir, "Wall.*.json"))):
    if "Apron" in f or "Wall34" in f or "Wall95" in f:
        continue
    try:
        with open(f, "r") as fp:
            data = json.load(fp)
            points = data.get("Wall", {}).get("drag_points", [])
            for p in points:
                x = p.get("x", 0)
                y = p.get("y", 0)
                if 950 <= x <= 1081 and 1750 <= y <= 2162:
                    print(f"  {os.path.basename(f)}: x={x:.1f}, y={y:.1f}")
    except Exception:
        pass
