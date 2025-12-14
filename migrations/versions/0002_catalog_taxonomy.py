from __future__ import annotations

from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_catalog_taxonomy"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def _seed_taxonomy() -> None:
    professions_table = sa.table(
        "professions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String(length=64)),
        sa.column("label", sa.String(length=100)),
        sa.column("sort_order", sa.Integer()),
    )

    categories_table = sa.table(
        "categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String(length=64)),
        sa.column("label", sa.String(length=100)),
    )

    profession_categories_table = sa.table(
        "profession_categories",
        sa.column("profession_id", postgresql.UUID(as_uuid=True)),
        sa.column("category_id", postgresql.UUID(as_uuid=True)),
        sa.column("sort_order", sa.Integer()),
    )

    professions: list[tuple[str, str, int]] = [
        ("larare", "Lärare", 10),
        ("specialpedagog", "Specialpedagog", 20),
        ("skoladministrator", "Skoladministratör", 30),
        ("rektor", "Rektor", 40),
        ("gemensamt", "Gemensamt", 50),
    ]

    categories: list[tuple[str, str, int]] = [
        ("lektionsplanering", "Lektionsplanering", 10),
        ("mentorskap", "Mentorskap", 20),
        ("administration", "Administration", 30),
        ("ovrigt", "Övrigt", 40),
    ]

    profession_ids: dict[str, UUID] = {slug: uuid4() for slug, _, _ in professions}
    category_ids: dict[str, UUID] = {slug: uuid4() for slug, _, _ in categories}

    op.bulk_insert(
        professions_table,
        [
            {"id": profession_ids[slug], "slug": slug, "label": label, "sort_order": sort_order}
            for slug, label, sort_order in professions
        ],
    )
    op.bulk_insert(
        categories_table,
        [{"id": category_ids[slug], "slug": slug, "label": label} for slug, label, _ in categories],
    )
    op.bulk_insert(
        profession_categories_table,
        [
            {
                "profession_id": profession_ids[profession_slug],
                "category_id": category_ids[category_slug],
                "sort_order": sort_order,
            }
            for profession_slug, _, _profession_sort_order in professions
            for category_slug, _label, sort_order in categories
        ],
    )


def upgrade() -> None:
    op.create_table(
        "professions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_professions_slug"),
    )
    op.create_index("ix_professions_slug", "professions", ["slug"])
    op.create_index("ix_professions_sort_order", "professions", ["sort_order"])

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"])

    op.create_table(
        "profession_categories",
        sa.Column(
            "profession_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["profession_id"], ["professions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profession_id", "category_id", name="pk_profession_categories"),
    )
    op.create_index(
        "ix_profession_categories_profession_id",
        "profession_categories",
        ["profession_id"],
    )
    op.create_index(
        "ix_profession_categories_category_id",
        "profession_categories",
        ["category_id"],
    )

    op.create_table(
        "tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_tools_slug"),
    )
    op.create_index("ix_tools_slug", "tools", ["slug"])

    op.create_table(
        "tool_professions",
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profession_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profession_id"], ["professions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tool_id", "profession_id", name="pk_tool_professions"),
    )
    op.create_index("ix_tool_professions_tool_id", "tool_professions", ["tool_id"])
    op.create_index("ix_tool_professions_profession_id", "tool_professions", ["profession_id"])

    op.create_table(
        "tool_categories",
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tool_id", "category_id", name="pk_tool_categories"),
    )
    op.create_index("ix_tool_categories_tool_id", "tool_categories", ["tool_id"])
    op.create_index("ix_tool_categories_category_id", "tool_categories", ["category_id"])

    _seed_taxonomy()


def downgrade() -> None:
    op.drop_index("ix_tool_categories_category_id", table_name="tool_categories")
    op.drop_index("ix_tool_categories_tool_id", table_name="tool_categories")
    op.drop_table("tool_categories")

    op.drop_index("ix_tool_professions_profession_id", table_name="tool_professions")
    op.drop_index("ix_tool_professions_tool_id", table_name="tool_professions")
    op.drop_table("tool_professions")

    op.drop_index("ix_tools_slug", table_name="tools")
    op.drop_table("tools")

    op.drop_index("ix_profession_categories_category_id", table_name="profession_categories")
    op.drop_index("ix_profession_categories_profession_id", table_name="profession_categories")
    op.drop_table("profession_categories")

    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_professions_sort_order", table_name="professions")
    op.drop_index("ix_professions_slug", table_name="professions")
    op.drop_table("professions")
