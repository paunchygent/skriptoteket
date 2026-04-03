import glob
import json
import os

repo_dir = ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/"

for f in sorted(glob.glob(os.path.join(repo_dir, "Wall.*.json"))):
    try:
        with open(f, "r") as fp:
            data = json.load(fp)
            points = data.get("Wall", {}).get("drag_points", [])
            for p in points:
                if p.get("x", 0) > 950 and p.get("y", 0) > 1700:
                    print(f"File: {os.path.basename(f)}")
                    for pt in points:
                        print(f"  {pt.get('x'):.1f}, {pt.get('y'):.1f}")
                    break
    except Exception:
        pass
