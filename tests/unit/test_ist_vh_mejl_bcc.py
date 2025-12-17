from __future__ import annotations

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
def test_run_tool_writes_emails_artifact_and_returns_html(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    input_path.write_text(
        "Student,Vårdnadshavare e-post\n"
        "Alice,a@example.com\n"
        "Bob,B@EXAMPLE.COM\n"
        "Caro,a@example.com\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "output"
    html = run_tool(str(input_path), str(output_dir))

    artifacts = list(output_dir.glob("emails_*.txt"))
    assert len(artifacts) == 1
    assert artifacts[0].read_text(encoding="utf-8") == "a@example.com;b@example.com"
    assert "a@example.com;b@example.com" in html
    assert "unika" in html


@pytest.mark.unit
def test_run_tool_rejects_unsupported_file_types(tmp_path: Path) -> None:
    input_path = tmp_path / "input.pdf"
    input_path.write_text("nope", encoding="utf-8")
    output_dir = tmp_path / "output"

    html = run_tool(str(input_path), str(output_dir))

    assert ".pdf" in html
    assert "stöds inte" in html
