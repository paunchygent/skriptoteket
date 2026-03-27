"""Unit tests for web startup checks.

This module locks the fail-fast database revision guard so the web app refuses
to start against a stale schema instead of surfacing late planner/export 500s.
"""

import pytest

from skriptoteket.config import Settings
from skriptoteket.web.startup_checks import (
    _assert_database_revision_is_current,
    _assert_roster_smart_rule_schema_is_current,
    ensure_database_revision_is_current,
)


@pytest.mark.unit
def test_assert_database_revision_is_current_accepts_matching_revisions() -> None:
    _assert_database_revision_is_current(
        expected_heads=("6a1e9d3c4b7f",),
        current_revisions=("6a1e9d3c4b7f",),
    )


@pytest.mark.unit
def test_assert_database_revision_is_current_raises_on_mismatch() -> None:
    with pytest.raises(RuntimeError, match="pdm run db-upgrade") as error:
        _assert_database_revision_is_current(
            expected_heads=("6a1e9d3c4b7f",),
            current_revisions=("5f2c7d1a9b8e",),
        )

    assert "Current: 5f2c7d1a9b8e" in str(error.value)
    assert "Expected: 6a1e9d3c4b7f" in str(error.value)


@pytest.mark.unit
def test_assert_roster_smart_rule_schema_is_current_accepts_current_contract() -> None:
    _assert_roster_smart_rule_schema_is_current(
        table_names=frozenset(
            {
                "classroom_planner_roster_smart_rule_sets",
                "classroom_planner_roster_seating_preferences",
                "classroom_planner_roster_relationship_rules",
            }
        ),
        foreign_key_targets={
            "classroom_planner_roster_seating_preferences": (
                "classroom_planner_roster_smart_rule_sets",
            ),
            "classroom_planner_roster_relationship_rules": (
                "classroom_planner_roster_smart_rule_sets",
            ),
        },
    )


@pytest.mark.unit
def test_assert_roster_smart_rule_schema_is_current_raises_on_missing_tables() -> None:
    with pytest.raises(RuntimeError, match="missing required classroom planner smart-rule tables"):
        _assert_roster_smart_rule_schema_is_current(
            table_names=frozenset(
                {
                    "classroom_planner_roster_seating_preferences",
                    "classroom_planner_roster_relationship_rules",
                }
            ),
            foreign_key_targets={
                "classroom_planner_roster_seating_preferences": ("classroom_planner_rosters",),
                "classroom_planner_roster_relationship_rules": ("classroom_planner_rosters",),
            },
        )


@pytest.mark.unit
def test_assert_roster_smart_rule_schema_is_current_raises_on_outdated_foreign_keys() -> None:
    with pytest.raises(
        RuntimeError,
        match="outdated classroom planner smart-rule foreign-key contract",
    ):
        _assert_roster_smart_rule_schema_is_current(
            table_names=frozenset(
                {
                    "classroom_planner_roster_smart_rule_sets",
                    "classroom_planner_roster_seating_preferences",
                    "classroom_planner_roster_relationship_rules",
                }
            ),
            foreign_key_targets={
                "classroom_planner_roster_seating_preferences": ("classroom_planner_rosters",),
                "classroom_planner_roster_relationship_rules": ("classroom_planner_rosters",),
            },
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_database_revision_is_current_uses_repo_and_database_revisions(
    monkeypatch,
) -> None:
    async def fake_load_database_revisions(_database_url: str) -> tuple[str, ...]:
        return ("6a1e9d3c4b7f",)

    async def fake_load_database_schema_contract(
        _database_url: str,
    ) -> tuple[frozenset[str], dict[str, tuple[str, ...]]]:
        return (
            frozenset(
                {
                    "classroom_planner_roster_smart_rule_sets",
                    "classroom_planner_roster_seating_preferences",
                    "classroom_planner_roster_relationship_rules",
                }
            ),
            {
                "classroom_planner_roster_seating_preferences": (
                    "classroom_planner_roster_smart_rule_sets",
                ),
                "classroom_planner_roster_relationship_rules": (
                    "classroom_planner_roster_smart_rule_sets",
                ),
            },
        )

    monkeypatch.setattr(
        "skriptoteket.web.startup_checks._load_repo_head_revisions",
        lambda: ("6a1e9d3c4b7f",),
    )
    monkeypatch.setattr(
        "skriptoteket.web.startup_checks._load_database_revisions",
        fake_load_database_revisions,
    )
    monkeypatch.setattr(
        "skriptoteket.web.startup_checks._load_database_schema_contract",
        fake_load_database_schema_contract,
    )

    await ensure_database_revision_is_current(Settings())
