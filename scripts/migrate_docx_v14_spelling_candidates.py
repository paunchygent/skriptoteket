"""One-off TASK-SKRIPT-39-09-06 rewrite of v14 recorded producer outputs.

The model no longer proposes spelling candidates for gap answers; the shared
deterministic producer does. This is fixture maintenance, not a production
compatibility reader. Every recorded reply keeps its wording, anchors and key
provenance and loses only the ``spelling_candidates`` field, so the migrated
recordings load under the current strict producer contract.
"""

import argparse
import json
from pathlib import Path

RECORDINGS = Path("tests/fixtures/exam_conversion/docx_key_provenance_v14")


def rewrite_recordings(*, manifest: Path) -> None:
    """Drop the removed field and retain an exact changed-file manifest."""
    changed: list[str] = []
    candidates = 0
    for path in sorted(RECORDINGS.rglob("*.json")):
        content = json.loads(path.read_text())
        modified = False
        for item in content.get("items", []):
            for paragraph in item["body"]:
                for segment in paragraph["segments"]:
                    if "spelling_candidates" not in segment:
                        raise ValueError(f"Missing spelling_candidates in {path}")
                    candidates += len(segment.pop("spelling_candidates"))
                    modified = True
        if modified:
            path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n")
            changed.append(path.as_posix())
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "authority": "TASK-SKRIPT-39-09-06",
                "candidates_removed": candidates,
                "files": changed,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(f"Rewrote {len(changed)} recordings, dropping {candidates} candidates; {manifest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    rewrite_recordings(manifest=args.manifest)


if __name__ == "__main__":
    main()
