"""Record each saved exam's format version for the readable/unreadable listing.

`exam_index` gains `document_format_version`, written on every save. This
revision backfills each existing row from its head file, read at
``VAULT_ROOT/<owner_user_id>/<head_vault_file_id>`` as migration
4e9b7d1c6a02 reads that root: the version number of `document.json`'s
`schema_version`, or 0 when the file is missing, is not a zip, or has no
parsable version. 0 is below every readable version, so such an exam is
listed as unreadable.

Revision ID: 74adf10e2441
Revises: 67c02402930c
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.engine.reflection import Inspector

from skriptoteket.config import Settings

revision: str = "74adf10e2441"
down_revision: str | Sequence[str] | None = "67c02402930c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VERSION_PATTERN = re.compile(r"native_exam_document_v(\d+)")


def _read_format_version(
    *, vault_root: Path, owner_user_id: str, head_vault_file_id: str
) -> tuple[int, str]:
    """Return the head file's format version and the outcome bucket for the summary."""
    try:
        data = (vault_root / owner_user_id / head_vault_file_id).read_bytes()
    except FileNotFoundError:
        return 0, "missing"
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return 0, "not_zip"
    with archive:
        try:
            raw = archive.read("document.json")
        except KeyError:
            return 0, "no_document"
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 0, "invalid_json"
    schema_version = payload.get("schema_version") if isinstance(payload, dict) else None
    match = _VERSION_PATTERN.fullmatch(schema_version) if isinstance(schema_version, str) else None
    if match is None:
        return 0, "unknown_version"
    return int(match.group(1)), "versioned"


def _backfill_format_versions(*, connection: Connection) -> None:
    rows = connection.execute(
        sa.text(
            "SELECT owner_user_id::text AS owner, lineage_id::text AS lineage, "
            "head_vault_file_id::text AS head FROM exam_index "
            "ORDER BY owner_user_id, lineage_id"
        )
    ).all()

    vault_root = Settings().VAULT_ROOT
    outcomes: dict[str, int] = {}
    for row in rows:
        version, outcome = _read_format_version(
            vault_root=vault_root, owner_user_id=row.owner, head_vault_file_id=row.head
        )
        connection.execute(
            sa.text(
                "UPDATE exam_index SET document_format_version = :version "
                "WHERE owner_user_id = :owner AND lineage_id = :lineage"
            ),
            {"version": version, "owner": row.owner, "lineage": row.lineage},
        )
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        print(
            f"exam_index_format_version owner={row.owner} lineage={row.lineage} {outcome}={version}"
        )
    print(
        "exam_index_format_versions_backfilled"
        f" vault_root={vault_root}"
        f" examined_rows={len(rows)}"
        f" outcomes={outcomes!r}"
    )


def upgrade() -> None:
    """Add the format version column and backfill it from each head file."""

    connection = op.get_bind()
    inspector = inspect(connection)

    columns = {column["name"] for column in inspector.get_columns("exam_index")}
    if "document_format_version" not in columns:
        op.add_column(
            "exam_index",
            sa.Column("document_format_version", sa.Integer(), nullable=True),
        )

    _backfill_format_versions(connection=connection)

    op.alter_column("exam_index", "document_format_version", nullable=False)


def downgrade() -> None:
    """Drop the format version column; the saved exams keep their head files."""

    connection = op.get_bind()
    inspector: Inspector = inspect(connection)

    columns = {column["name"] for column in inspector.get_columns("exam_index")}
    if "document_format_version" in columns:
        op.drop_column("exam_index", "document_format_version")
