"""One-off TASK-SKRIPT-39-09-04 rewrite of v14 recorded producer outputs.

This is fixture maintenance, not a production compatibility reader. A recorded
prose guide has no per-criterion breakdown, so its producer criterion has null
points. The build applies R14: use the item's points or 1, marked estimated.
The original guide text and all unrelated recorded values remain unchanged.
"""

import argparse
import json
from pathlib import Path

RECORDINGS = Path("tests/fixtures/exam_conversion/docx_key_provenance_v14")


def rewrite_recordings(*, manifest: Path) -> None:
    """Replace the removed field and retain an exact changed-file manifest."""
    changed: list[str] = []
    guides = 0
    for path in sorted(RECORDINGS.rglob("*.json")):
        content = json.loads(path.read_text())
        modified = False
        for item in content.get("items", []):
            if "marking_guide" not in item:
                continue
            if "criteria" in item:
                raise ValueError(f"Both schemas present in {path}")
            guide = item.pop("marking_guide")
            if guide:
                if item["kind"] != "free_text":
                    raise ValueError(f"Guide on a non-Fritext item in {path}")
                item["criteria"] = [{"text": guide, "points": None}]
                guides += 1
            else:
                item["criteria"] = []
            modified = True
        if modified:
            path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n")
            changed.append(path.as_posix())
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {"authority": "TASK-SKRIPT-39-09-04", "prose_guides": guides, "files": changed},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(f"Rewrote {len(changed)} recordings, including {guides} prose guides; {manifest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    rewrite_recordings(manifest=args.manifest)


if __name__ == "__main__":
    main()
