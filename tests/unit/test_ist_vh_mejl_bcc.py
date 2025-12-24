from __future__ import annotations

import json
from pathlib import Path

import pytest

from skriptoteket.script_bank.scripts.ist_vh_mejl_bcc import (
    harvest_emails_from_cells,
    prioritized_columns,
    run_tool,
)


@pytest.mark.unit
def test_prioritized_columns_prefers_guardian_email_columns() -> None:
    columns = [
        "Name",
        "Vårdnadshavare e-post",
        "Email",
        "Guardian",
        "Phone",
    ]

    ordered = prioritized_columns(columns)

    assert ordered == [
        "Vårdnadshavare e-post",
        "Email",
        "Guardian",
        "Name",
        "Phone",
    ]


@pytest.mark.unit
def test_harvest_emails_deduplicates_and_normalizes_case() -> None:
    cells = [
        "A@Example.com; b@example.com",
        "b@example.com",
        "",
    ]

    emails = harvest_emails_from_cells(cells)

    assert emails == ["a@example.com", "b@example.com"]


@pytest.mark.unit
def test_run_tool_writes_emails_artifact_and_returns_contract_v2(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "input.csv"
    input_file.write_text(
        "Student,Vårdnadshavare e-post\n"
        "Alice,a@example.com\n"
        "Bob,B@EXAMPLE.COM\n"
        "Caro,a@example.com\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "output"
    result = run_tool(str(input_dir), str(output_dir))

    # Verify artifact file was written
    artifacts = list(output_dir.glob("emails_*.txt"))
    assert len(artifacts) == 1
    assert artifacts[0].read_text(encoding="utf-8") == "a@example.com;b@example.com"

    # Verify Contract v2 dict structure
    assert "outputs" in result
    assert "next_actions" in result
    assert isinstance(result["outputs"], list)
    assert len(result["outputs"]) >= 1

    # Verify notice output mentions unique emails
    notice = result["outputs"][0]
    assert notice["kind"] == "notice"
    assert notice["level"] == "info"
    assert "unika" in notice["message"]


@pytest.mark.unit
def test_run_tool_rejects_unsupported_file_types(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "input.pdf"
    input_file.write_text("nope", encoding="utf-8")
    output_dir = tmp_path / "output"

    result = run_tool(str(input_dir), str(output_dir))

    # Verify Contract v2 error structure
    assert "outputs" in result
    assert len(result["outputs"]) == 1
    error_output = result["outputs"][0]
    assert error_output["kind"] == "notice"
    assert error_output["level"] == "error"
    assert ".pdf" in error_output["message"]
    assert "stöds inte" in error_output["message"]


@pytest.mark.unit
def test_run_tool_processes_multiple_files_from_input_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    file1 = input_dir / "one.csv"
    file1.write_text(
        "Student,Vårdnadshavare e-post\nAlice,a@example.com\n",
        encoding="utf-8",
    )
    file2 = input_dir / "two.csv"
    file2.write_text(
        "Student,Vårdnadshavare e-post\nBob,b@example.com\n",
        encoding="utf-8",
    )

    manifest = {
        "files": [
            {"name": file1.name, "path": str(file1), "bytes": file1.stat().st_size},
            {"name": file2.name, "path": str(file2), "bytes": file2.stat().st_size},
        ]
    }
    monkeypatch.setenv("SKRIPTOTEKET_INPUT_MANIFEST", json.dumps(manifest))

    output_dir = tmp_path / "output"
    result = run_tool(str(input_dir), str(output_dir))

    artifacts = list(output_dir.glob("emails_*.txt"))
    assert len(artifacts) == 1
    assert artifacts[0].read_text(encoding="utf-8") == "a@example.com;b@example.com"

    files_table = next(
        (
            output
            for output in result["outputs"]
            if output.get("kind") == "table" and output.get("title") == "Filer"
        ),
        None,
    )
    assert files_table is not None
    assert len(files_table["rows"]) == 2
