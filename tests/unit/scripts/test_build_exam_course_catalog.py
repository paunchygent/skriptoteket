"""The public builder/check command runs offline against recorded API data."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def test_builder_cli_checks_recorded_mapping_without_rewriting_stale_data(tmp_path: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "scripts.build_exam_course_catalog",
        "--raw-dir",
        "tests/fixtures/exam_course_catalog",
        "--output-dir",
        str(tmp_path),
    ]
    built = subprocess.run(command, capture_output=True, text=True, check=False, timeout=20)
    assert built.returncode == 0, built.stderr
    catalog_path = tmp_path / "catalog.json"
    manifest_path = tmp_path / "BUILD.json"
    before = {path.name: path.read_bytes() for path in (catalog_path, manifest_path)}
    manifest = json.loads(before["BUILD.json"])
    assert manifest["counts"] == {"GY11": 5, "GY25": 3, "grundskolan": 6}
    assert manifest["total"] == 14
    assert set(manifest["source_urls"]) == {
        "https://api.skolverket.se/syllabus/v1/courses?schooltype=GY&timespan=LATEST",
        "https://api.skolverket.se/syllabus/v1/subjects?schooltype=GY&timespan=LATEST",
        "https://api.skolverket.se/syllabus/v1/subjects?schooltype=GR&timespan=LATEST",
        "https://api.skolverket.se/syllabus/v1/subjects/GRGRMSP01",
        "https://api.skolverket.se/syllabus/v1/subjects/GRGRSVE01",
    }

    checked = subprocess.run(
        [*command, "--check"], capture_output=True, text=True, check=False, timeout=20
    )
    assert checked.returncode == 0, checked.stderr
    assert {path.name: path.read_bytes() for path in (catalog_path, manifest_path)} == before

    stale = json.loads(before["catalog.json"])
    stale["courses"][0]["name"] = "Wrong course name"
    catalog_path.write_text(json.dumps(stale))
    stale_bytes = catalog_path.read_bytes()
    rejected = subprocess.run(
        [*command, "--check"], capture_output=True, text=True, check=False, timeout=20
    )
    assert rejected.returncode != 0
    assert "catalog.json" in rejected.stderr
    assert catalog_path.read_bytes() == stale_bytes
    assert manifest_path.read_bytes() == before["BUILD.json"]


def test_builder_cli_rejects_source_drift_before_writing_output(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    shutil.copytree("tests/fixtures/exam_course_catalog", raw_dir)
    subjects = raw_dir / "subjects-gy.json"
    subjects.write_text(subjects.read_text().replace('"endDate": "2030-06-30"', '"endDate": 0', 1))
    output = tmp_path / "output"
    output.mkdir()
    catalog = output / "catalog.json"
    catalog.write_bytes(b"existing snapshot must survive failed validation\n")
    before = catalog.read_bytes()

    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.build_exam_course_catalog",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert rejected.returncode != 0
    assert "endDate" in rejected.stderr
    assert catalog.read_bytes() == before
    assert not (output / "BUILD.json").exists()
