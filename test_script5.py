import glob
import json
import os

repo_dir = ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/"

print("Looking for walls with x around 1000 and y between 1750 and 1950")
for f in sorted(glob.glob(os.path.join(repo_dir, "Wall.*.json"))):
    try:
        with open(f, "r") as fp:
            data = json.load(fp)
            points = data.get("Wall", {}).get("drag_points", [])
            for p in points:
                if 950 <= p.get("x", 0) <= 1020 and 1750 <= p.get("y", 0) <= 1950:
                    print(f"  {os.path.basename(f)}")
                    break
    except Exception:
        pass
