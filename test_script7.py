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
                if 990 <= p.get("x", 0) <= 1010 and 1820 <= p.get("y", 0) <= 1910:
                    print(f"  {os.path.basename(f)}: x={p.get('x'):.1f}, y={p.get('y'):.1f}")
    except Exception:
        pass
