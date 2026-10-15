"""Conversion-hub and exam-converter migration schema assertions.

Purpose:
    Verify conversion-hub, exam-converter, and transcript schema revisions
    during idempotent Alembic tests.

Relationships:
    - Registered by `migration_schema_assertions`.
    - Reuses the planner profile-preferences assertion as its parent check.
    - Uses shared information-schema helpers from `migration_schema_helpers`.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.migration_schema_helpers import (
    column_map,
    foreign_key_targets,
    index_names,
    table_names,
)
from tests.integration.migration_schema_share_assertions import (
    assert_b6c9_classroom_planner_profile_preferences,
)


async def assert_2b6c_conversion_hub_jobs(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "conversion_hub_jobs" in tables
    columns = await column_map(engine, "conversion_hub_jobs")
    assert {"owner_user_id", "input_filename", "source_format", "output_format"}.issubset(columns)
    assert columns["pdf_paper_size"]["is_nullable"] == "YES"
    assert columns["upstream_job_id"]["is_nullable"] == "YES"
    indexes = await index_names(engine, "conversion_hub_jobs")
    assert {
        "ix_conversion_hub_jobs_owner_user_id",
        "ix_conversion_hub_jobs_status",
        "ix_conversion_hub_jobs_owner_created",
        "uq_conversion_hub_jobs_upstream",
    }.issubset(indexes)


async def assert_9b2f_exam_converter_correction_sessions(engine: AsyncEngine) -> None:
    await assert_b6c9_classroom_planner_profile_preferences(engine)
    tables = await table_names(engine)
    assert {
        "exam_converter_correction_sessions",
        "exam_converter_correction_intents",
    }.issubset(tables)

    session_columns = await column_map(engine, "exam_converter_correction_sessions")
    assert {
        "owner_user_id",
        "conversion_hub_job_id",
        "source_authoring_schema_version",
        "source_state_sha256",
        "source_state_signature",
        "session_version",
    }.issubset(session_columns)
    assert session_columns["source_bundle_id"]["is_nullable"] == "YES"
    assert session_columns["source_file_sha256"]["is_nullable"] == "YES"

    intent_columns = await column_map(engine, "exam_converter_correction_intents")
    assert {
        "session_id",
        "entry_id",
        "correction_kind",
        "target_key",
        "conflict_family",
        "source_binding",
        "target",
        "payload",
        "is_active",
    }.issubset(intent_columns)

    session_indexes = await index_names(engine, "exam_converter_correction_sessions")
    assert {
        "ix_exam_converter_correction_sessions_owner_user_id",
        "ix_exam_converter_correction_sessions_job_id",
        "ix_exam_conv_corr_sessions_owner_updated",
        "uq_exam_conv_corr_sessions_owner_job",
    }.issubset(session_indexes)

    intent_indexes = await index_names(engine, "exam_converter_correction_intents")
    assert {
        "ix_exam_converter_correction_intents_session_id",
        "ix_exam_conv_corr_intents_session_active",
        "uq_exam_conv_corr_intents_active_target",
        "uq_exam_conv_corr_intents_active_family",
    }.issubset(intent_indexes)

    session_foreign_keys = await foreign_key_targets(
        engine,
        "exam_converter_correction_sessions",
    )
    assert session_foreign_keys["owner_user_id"] == "users"
    assert session_foreign_keys["conversion_hub_job_id"] == "conversion_hub_jobs"
    intent_foreign_keys = await foreign_key_targets(
        engine,
        "exam_converter_correction_intents",
    )
    assert intent_foreign_keys["session_id"] == "exam_converter_correction_sessions"


async def assert_b3e7_remove_review_decision_correction_intents(engine: AsyncEngine) -> None:
    intent_columns = await column_map(engine, "exam_converter_correction_intents")
    assert "conflict_family" not in intent_columns

    intent_indexes = await index_names(engine, "exam_converter_correction_intents")
    assert "uq_exam_conv_corr_intents_active_family" not in intent_indexes
    assert {
        "ix_exam_converter_correction_intents_session_id",
        "ix_exam_conv_corr_intents_session_active",
        "uq_exam_conv_corr_intents_active_target",
    }.issubset(intent_indexes)


async def assert_c4e8_conversion_hub_saved_transcripts(engine: AsyncEngine) -> None:
    await assert_b3e7_remove_review_decision_correction_intents(engine)
    tables = await table_names(engine)
    assert "conversion_hub_saved_transcripts" in tables
    columns = await column_map(engine, "conversion_hub_saved_transcripts")
    assert {
        "owner_user_id",
        "conversion_hub_job_id",
        "sir_convert_job_id",
        "artifact_key",
        "source_filename",
        "transcript_schema_version",
        "diarization_mode",
        "transcript_json",
    }.issubset(columns)
    assert columns["language_code"]["is_nullable"] == "YES"
    assert columns["generated_at"]["is_nullable"] == "YES"
    indexes = await index_names(engine, "conversion_hub_saved_transcripts")
    assert {
        "ix_conversion_hub_saved_transcripts_owner_user_id",
        "ix_conversion_hub_saved_transcripts_owner_created",
        "ix_conversion_hub_saved_transcripts_job_id",
        "uq_conversion_hub_saved_transcripts_owner_upstream",
    }.issubset(indexes)
    foreign_keys = await foreign_key_targets(engine, "conversion_hub_saved_transcripts")
    assert foreign_keys["owner_user_id"] == "users"
    assert foreign_keys["conversion_hub_job_id"] == "conversion_hub_jobs"


async def assert_d7c9_conversion_hub_transcript_speaker_overlays(
    engine: AsyncEngine,
) -> None:
    await assert_c4e8_conversion_hub_saved_transcripts(engine)
    tables = await table_names(engine)
    assert "conversion_hub_transcript_speaker_overlays" in tables
    columns = await column_map(engine, "conversion_hub_transcript_speaker_overlays")
    assert {
        "owner_user_id",
        "saved_transcript_id",
        "canonical_speaker_label",
        "display_name",
        "created_at",
        "updated_at",
    }.issubset(columns)
    assert columns["canonical_speaker_label"]["is_nullable"] == "NO"
    assert columns["display_name"]["is_nullable"] == "NO"
    indexes = await index_names(engine, "conversion_hub_transcript_speaker_overlays")
    assert {
        "ix_conversion_hub_transcript_speaker_overlays_owner_user_id",
        "ix_conv_hub_transcript_speaker_overlays_owner_transcript",
        "uq_conv_hub_transcript_speaker_overlays_label",
        "uq_conv_hub_transcript_speaker_overlays_display",
    }.issubset(indexes)
    foreign_keys = await foreign_key_targets(
        engine,
        "conversion_hub_transcript_speaker_overlays",
    )
    assert foreign_keys["owner_user_id"] == "users"
    assert foreign_keys["saved_transcript_id"] == "conversion_hub_saved_transcripts"


async def assert_e1f2_conversion_hub_transcript_formatter_artifacts(
    engine: AsyncEngine,
) -> None:
    await assert_d7c9_conversion_hub_transcript_speaker_overlays(engine)
    tables = await table_names(engine)
    assert "conversion_hub_transcript_formatter_artifacts" in tables
    columns = await column_map(engine, "conversion_hub_transcript_formatter_artifacts")
    assert {
        "owner_user_id",
        "saved_transcript_id",
        "conversion_hub_job_id",
        "sir_convert_job_id",
        "requested_artifact",
        "artifact_key",
        "filename",
        "content_type",
        "size_bytes",
        "sha256",
        "retrieval_path",
    }.issubset(columns)
    indexes = await index_names(engine, "conversion_hub_transcript_formatter_artifacts")
    assert {
        "ix_conversion_hub_transcript_formatter_artifacts_owner_user_id",
        "ix_conv_hub_transcript_formatter_artifacts_owner_transcript",
        "ix_conv_hub_transcript_formatter_artifacts_job",
        "uq_conv_hub_transcript_formatter_artifacts_key",
    }.issubset(indexes)
    foreign_keys = await foreign_key_targets(
        engine,
        "conversion_hub_transcript_formatter_artifacts",
    )
    assert foreign_keys["owner_user_id"] == "users"
    assert foreign_keys["saved_transcript_id"] == "conversion_hub_saved_transcripts"
    assert foreign_keys["conversion_hub_job_id"] == "conversion_hub_jobs"


async def assert_e9a4_conversion_hub_transcript_formatter_artifact_content(
    engine: AsyncEngine,
) -> None:
    await assert_e1f2_conversion_hub_transcript_formatter_artifacts(engine)
    columns = await column_map(engine, "conversion_hub_transcript_formatter_artifacts")
    assert "content" in columns


async def assert_f4c8_conversion_hub_transcript_formatter_export_states(
    engine: AsyncEngine,
) -> None:
    await assert_e9a4_conversion_hub_transcript_formatter_artifact_content(engine)
    tables = await table_names(engine)
    assert "conversion_hub_transcript_formatter_export_states" in tables
    columns = await column_map(engine, "conversion_hub_transcript_formatter_export_states")
    assert {
        "owner_user_id",
        "saved_transcript_id",
        "conversion_hub_job_id",
        "requested_artifacts",
        "created_at",
        "updated_at",
    }.issubset(columns)
    assert columns["requested_artifacts"]["is_nullable"] == "NO"
    indexes = await index_names(engine, "conversion_hub_transcript_formatter_export_states")
    assert {
        "ix_conv_hub_formatter_export_states_owner_transcript",
        "ix_conv_hub_formatter_export_states_owner_job",
        "uq_conv_hub_transcript_formatter_export_states_job",
    }.issubset(indexes)
    foreign_keys = await foreign_key_targets(
        engine,
        "conversion_hub_transcript_formatter_export_states",
    )
    assert foreign_keys["owner_user_id"] == "users"
    assert foreign_keys["saved_transcript_id"] == "conversion_hub_saved_transcripts"
    assert foreign_keys["conversion_hub_job_id"] == "conversion_hub_jobs"
