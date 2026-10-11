"""Gruppgenerator's real bundle files as a draft version, plus a teacher-style edit of roster.py."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from skriptoteket.domain.scripting.tool_versions import ToolVersion, create_draft_version
from skriptoteket.script_bank.sources import read_script_bank_source

ROSTER_NORMALIZE_LINE = '    return " ".join(value.strip().split())'
EDIT_MARKER = "ÄNDRAD"


def gruppgenerator_files() -> tuple[str, dict[str, str]]:
    source_code, bundle_files = read_script_bank_source(source_filename="gruppgenerator/tool.py")
    assert set(bundle_files) == {"grouping.py", "roster.py"}
    return source_code, bundle_files


def edited_roster_py(roster_py: str) -> str:
    """Prefix every parsed student name with the marker, so a run shows which roster.py it used."""
    assert roster_py.count(ROSTER_NORMALIZE_LINE) == 1
    return roster_py.replace(
        ROSTER_NORMALIZE_LINE,
        f'    return "{EDIT_MARKER} " + " ".join(value.strip().split())',
    )


def gruppgenerator_draft(
    *,
    version_id: UUID,
    tool_id: UUID,
    created_by_user_id: UUID,
    now: datetime,
    version_number: int = 1,
) -> ToolVersion:
    source_code, bundle_files = gruppgenerator_files()
    return create_draft_version(
        version_id=version_id,
        tool_id=tool_id,
        version_number=version_number,
        source_code=source_code,
        bundle_files=bundle_files,
        entrypoint="run_tool",
        input_schema=[],
        created_by_user_id=created_by_user_id,
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )
