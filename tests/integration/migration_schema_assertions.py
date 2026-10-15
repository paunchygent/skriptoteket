"""Schema assertion registry for revision-focused Alembic idempotency tests.

Purpose:
    Map every covered migration revision to its responsibility-owned schema
    assertion and expose the coverage entry points used by the tests and the
    coverage check.

Relationships:
    - Re-exports `COVERED_REVISION_IDS` from `migration_revision_coverage`.
    - Registers assertion functions from the responsibility-owned
      `migration_schema_*_assertions` modules.
    - Consumed by the parametrized migration idempotency test and the
      migration test coverage check.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.migration_revision_coverage import COVERED_REVISION_IDS
from tests.integration.migration_schema_checkpoint_assertions import (
    assert_3e8b_seating_export_checkpoints,
    assert_4d2c_grouping_export_checkpoints,
    assert_f2a7_share_checkpoint_provenance,
)
from tests.integration.migration_schema_conversion_assertions import (
    assert_2b6c_conversion_hub_jobs,
    assert_9b2f_exam_converter_correction_sessions,
    assert_b3e7_remove_review_decision_correction_intents,
    assert_c4e8_conversion_hub_saved_transcripts,
    assert_d7c9_conversion_hub_transcript_speaker_overlays,
    assert_e1f2_conversion_hub_transcript_formatter_artifacts,
    assert_e9a4_conversion_hub_transcript_formatter_artifact_content,
    assert_f4c8_conversion_hub_transcript_formatter_export_states,
)
from tests.integration.migration_schema_helpers import (
    RevisionAssertion,
)
from tests.integration.migration_schema_identity_assertions import (
    assert_0001_init,
    assert_0012_tool_owner_user_id,
    assert_0014_tool_versions_settings,
    assert_0022_email_verification_tokens,
    assert_0026_profile_ai_settings,
    assert_0032_user_file_vault,
    assert_1eb5_profile_tutorial_seen_sections,
    assert_8f3d_password_reset_tokens,
    assert_a1e4_default_klassrumskartan_favorite,
    assert_b7f9_drop_legacy_student_notes,
    assert_c1d2_drop_browser_auth_sessions,
    assert_d3a9_guest_upgrade_identity,
)
from tests.integration.migration_schema_planner_assertions import (
    assert_1d3e_seating_preferences_reset,
    assert_4a9d_nullable_xlsx_fields,
    assert_4cb4_grouping_history,
    assert_4f56_refactor_assignments,
    assert_5f2c_roster_owned_smart_rules,
    assert_6a1e_merged_heads,
    assert_6b44_draft_kind,
    assert_7b8a_planner_draft_flags,
    assert_7d4c_roster_smart_rule_repair,
    assert_8a1d_slice_two_workspace,
    assert_8c4d_planner_smart_rule_tables,
    assert_9d7c_room_template_grid_dimensions,
    assert_9f1a_prune_superseded,
    assert_57a6_create_rosters_and_templates,
    assert_71e8_group_name_custom_flag,
    assert_91f6_roomless_seating,
    assert_b18f_seating_export_jobs,
    assert_c2a6_draft_lifecycle,
    assert_c9c1_shared_export_binding,
    assert_d8f0_single_active_draft,
    assert_e4b7_smart_enabled,
    assert_f6c1_grouping_export_jobs,
    assert_f30a_create_plan_drafts,
)
from tests.integration.migration_schema_share_assertions import (
    assert_0d9c_fixed_seat_rules,
    assert_3f6d_use_history_default_on,
    assert_8a6d_grouping_seating_distance_default_on,
    assert_a8f5_classroom_planner_share_artifacts,
    assert_b4c6_share_artifact_lifecycle_fks,
    assert_b6c9_classroom_planner_profile_preferences,
    assert_c7d9_share_artifact_public_path,
    assert_e2f4_public_guest_share_controls,
    assert_f8a2_share_preview_assets,
)

__all__ = [
    "COVERED_REVISION_IDS",
    "SCHEMA_ASSERTIONS",
    "assert_schema_for_revision",
]


SCHEMA_ASSERTIONS: dict[str, RevisionAssertion] = {
    "0001_init": assert_0001_init,
    "0012_tool_owner_user_id": assert_0012_tool_owner_user_id,
    "0014_tool_versions_settings": assert_0014_tool_versions_settings,
    "0022_email_verification_tokens": assert_0022_email_verification_tokens,
    "0026_profile_ai_settings": assert_0026_profile_ai_settings,
    "0032_user_file_vault": assert_0032_user_file_vault,
    "57a6ea32ef0a": assert_57a6_create_rosters_and_templates,
    "f30ac060991c": assert_f30a_create_plan_drafts,
    "4f5605f8be18": assert_4f56_refactor_assignments,
    "8a1d4c7b32ef": assert_8a1d_slice_two_workspace,
    "c2a6b2f4d91e": assert_c2a6_draft_lifecycle,
    "d8f0d0ef2b6d": assert_d8f0_single_active_draft,
    "9f1a6c4d2e7b": assert_9f1a_prune_superseded,
    "6b44e9b5d3c1": assert_6b44_draft_kind,
    "91f6c4a7b2d1": assert_91f6_roomless_seating,
    "4cb43fe0cf54": assert_4cb4_grouping_history,
    "71e8b6f24c1a": assert_71e8_group_name_custom_flag,
    "9d7c4a12b6ef": assert_9d7c_room_template_grid_dimensions,
    "b18f6a0d3e2c": assert_b18f_seating_export_jobs,
    "c9c1c9270a3d": assert_c9c1_shared_export_binding,
    "e4b7c2d9a1f0": assert_e4b7_smart_enabled,
    "f6c1e2a9b3d4": assert_f6c1_grouping_export_jobs,
    "7b8a6f1d2c3e": assert_7b8a_planner_draft_flags,
    "8c4d2e1f7a9b": assert_8c4d_planner_smart_rule_tables,
    "1d3e5f7a9b2c": assert_1d3e_seating_preferences_reset,
    "5f2c7d1a9b8e": assert_5f2c_roster_owned_smart_rules,
    "4a9d7c1e2b34": assert_4a9d_nullable_xlsx_fields,
    "2b6c4d8e1f9a": assert_2b6c_conversion_hub_jobs,
    "6a1e9d3c4b7f": assert_6a1e_merged_heads,
    "7d4c1a2b9e6f": assert_7d4c_roster_smart_rule_repair,
    "3e8b5c1a7d4f": assert_3e8b_seating_export_checkpoints,
    "4d2c6b8e1a9f": assert_4d2c_grouping_export_checkpoints,
    "8f3d2c1b4a6e": assert_8f3d_password_reset_tokens,
    "a1e4d6c8b2f0": assert_a1e4_default_klassrumskartan_favorite,
    "b7f9c2d4e1a6": assert_b7f9_drop_legacy_student_notes,
    "d3a9f6b2c4e7": assert_d3a9_guest_upgrade_identity,
    "c1d2e3f4a5b6": assert_c1d2_drop_browser_auth_sessions,
    "a8f5c7d9e2b1": assert_a8f5_classroom_planner_share_artifacts,
    "b4c6d8e1f2a3": assert_b4c6_share_artifact_lifecycle_fks,
    "c7d9e3f5a1b2": assert_c7d9_share_artifact_public_path,
    "e2f4a6b8c9d0": assert_e2f4_public_guest_share_controls,
    "f8a2c6d4e9b1": assert_f8a2_share_preview_assets,
    "0d9c5e8a2f31": assert_0d9c_fixed_seat_rules,
    "3f6d8a2c4b91": assert_3f6d_use_history_default_on,
    "8a6d4c2f1b09": assert_8a6d_grouping_seating_distance_default_on,
    "f2a7c9d4e6b8": assert_f2a7_share_checkpoint_provenance,
    "b6c9f2a1d4e8": assert_b6c9_classroom_planner_profile_preferences,
    "9b2f4c6d8e10": assert_9b2f_exam_converter_correction_sessions,
    "b3e7a1c9d4f2": assert_b3e7_remove_review_decision_correction_intents,
    "c4e8f0a2d6b9": assert_c4e8_conversion_hub_saved_transcripts,
    "d7c9a1e4b6f2": assert_d7c9_conversion_hub_transcript_speaker_overlays,
    "e1f2a3b4c5d6": assert_e1f2_conversion_hub_transcript_formatter_artifacts,
    "e9a4b6c8d2f0": assert_e9a4_conversion_hub_transcript_formatter_artifact_content,
    "f4c8e2a6b9d1": assert_f4c8_conversion_hub_transcript_formatter_export_states,
    "1eb507ae2278": assert_1eb5_profile_tutorial_seen_sections,
}


async def assert_schema_for_revision(revision_id: str, engine: AsyncEngine) -> None:
    """Run the registered schema assertion for a covered revision."""
    await SCHEMA_ASSERTIONS[revision_id](engine)
