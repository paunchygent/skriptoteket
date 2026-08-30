/**
 * Exam Converter correction-session test fixtures.
 *
 * Domain purpose:
 *   Provide source-state, replay, and persisted-session fixtures for
 *   authenticated Exam Converter tests that exercise durable teacher changes.
 *
 * Relationships:
 *   - Used by review and correction-session Vitest slices.
 *   - Mirrors the minimum source-bound fields required by local correction replay.
 */

import { ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION } from "../../api/examConverterContracts";

function replayArtifactReferences(jobId: string = "job_correction_replay") {
  return [
    {
      artifact_key: "correction_replay_examnet_pdf",
      artifact_set_id: `${jobId}-artifact-set-pdf`,
      content_sha256: `sha256:${jobId}-pdf`,
      correction_payload_digest: `sha256:${jobId}-correction-payload`,
      created_at: "2026-06-29T12:00:00Z",
      job_id: jobId,
      replay_profile_version: "correction-replay-v1",
      request_id: `${jobId}-request`,
      schema_version: "correction_replay_artifact_reference_v1",
      source_binding_digest: `sha256:${jobId}-source-binding`,
      source_state_sha256: `sha256:${jobId}-source-state`,
      target: "examnet_pdf",
      target_set_digest: `sha256:${jobId}-target-set`,
    },
    {
      artifact_key: "correction_replay_qti_package",
      artifact_set_id: `${jobId}-artifact-set-qti`,
      content_sha256: `sha256:${jobId}-qti`,
      correction_payload_digest: `sha256:${jobId}-correction-payload`,
      created_at: "2026-06-29T12:00:00Z",
      job_id: jobId,
      replay_profile_version: "correction-replay-v1",
      request_id: `${jobId}-request`,
      schema_version: "correction_replay_artifact_reference_v1",
      source_binding_digest: `sha256:${jobId}-source-binding`,
      source_state_sha256: `sha256:${jobId}-source-state`,
      target: "qti_package",
      target_set_digest: `sha256:${jobId}-target-set`,
    },
  ];
}

type CorrectionSessionFixtureIntent = Record<string, unknown> & {
  target_key: string;
};

type CorrectionSessionFixture = {
  active_intents: CorrectionSessionFixtureIntent[];
  conversion_hub_job_id: string;
  owner_user_id: string;
  session_id: string | null;
  session_version: number;
  source_binding: unknown;
};

export function emptyCorrectionSession(): CorrectionSessionFixture {
  return {
    active_intents: [],
    conversion_hub_job_id: "local-conversion-hub-job-1",
    owner_user_id: "11111111-1111-4111-8111-111111111111",
    session_id: null,
    session_version: 0,
    source_binding: null,
  };
}

export function createCorrectionSessionRecorder() {
  let current = emptyCorrectionSession();
  return {
    current: () => current,
    recordIntents: (intents: Record<string, unknown>[]) => {
      current = correctionSessionFromIntents({
        current,
        intents,
      });
      return current;
    },
    reset: () => {
      current = emptyCorrectionSession();
    },
  };
}

function targetKeyForIntent(intent: Record<string, unknown>): string {
  const target = intent.target as Record<string, unknown> | undefined;
  return `${String(intent.kind)}:${String(intent.item_id)}:${String(target?.interaction_id ?? "-")}`;
}

function correctionSessionFromIntents(params: {
  current: CorrectionSessionFixture;
  intents: Record<string, unknown>[];
}): CorrectionSessionFixture {
  const replacements = new Map(
    params.intents.map((intent, index) => {
      const targetKey = targetKeyForIntent(intent);
      return [
        targetKey,
        {
          ...intent,
          intent_id: `22222222-2222-4222-8222-${String(index + 1).padStart(12, "0")}`,
          target: intent.target ?? {},
          target_key: targetKey,
        },
      ];
    }),
  );
  const activeIntents = [
    ...params.current.active_intents.filter((intent) => !replacements.has(intent.target_key)),
    ...replacements.values(),
  ];
  return {
    active_intents: activeIntents,
    conversion_hub_job_id: "local-conversion-hub-job-1",
    owner_user_id: "11111111-1111-4111-8111-111111111111",
    session_id: "33333333-3333-4333-8333-333333333333",
    session_version: params.current.session_version + 1,
    source_binding: params.intents[0]?.source_binding ?? params.current.source_binding,
  };
}

export function correctionSourceState() {
  return {
    schema_version: "exam_authoring_correction_source_state_issue_result_v1",
    source_binding: {
      source_authoring_schema_version: "exam_authoring_ir_v1",
      source_bundle_id: "job_exam_converter_review",
      source_file_sha256: "sha256:source",
      source_state_sha256: "sha256:source-state",
      source_state_signature: "hmac-sha256:signature",
    },
    source_authoring_state: {
      schema_version: "exam_authoring_correction_source_state_v1",
      source_authoring_schema_version: "exam_authoring_ir_v1",
      source_state_sha256: "sha256:source-state",
      items: [
        sourceReviewDecisionItem(),
        sourceChoiceItem(),
        sourceSiblingChoiceItem(),
        sourceGapItem(),
      ],
    },
  };
}

function sourceReviewDecisionItem() {
  return {
    choice_interactions: [],
    gap_open_cloze_interactions: [],
    item_id: "item-001",
    item_type: "gap_fill",
    max_score: 1,
    prompt_html: null,
    prompt_lines: ["Begrepp i ekologi"],
    sequence: 1,
    source_item_fingerprint: "sha256:item-001",
    title: "Begrepp i ekologi",
  };
}

function sourceChoiceItem() {
  return {
    choice_interactions: [
      {
        answer_key: null,
        choices: [
          { choice_id: "choice-1", order: 1, source_id: "1", text: "Fel 1" },
          { choice_id: "choice-2", order: 2, source_id: "2", text: "Fel 2" },
          { choice_id: "choice-3", order: 3, source_id: "3", text: "Rätt" },
        ],
        interaction_id: "choice-item-004",
      },
    ],
    gap_open_cloze_interactions: [],
    item_id: "item-004",
    item_type: "single_choice",
    max_score: 1,
    prompt_html: null,
    prompt_lines: ["Vilket av följande påståenden beskriver cellandning bäst?"],
    sequence: 4,
    source_item_fingerprint: "sha256:item-004",
    title: "Fråga 4",
  };
}

function sourceSiblingChoiceItem() {
  return {
    choice_interactions: [
      {
        answer_key: null,
        choices: [
          { choice_id: "choice-1", order: 1, source_id: "1", text: "Rätt 1" },
          { choice_id: "choice-2", order: 2, source_id: "2", text: "Rätt 2" },
          { choice_id: "choice-3", order: 3, source_id: "3", text: "Fel" },
        ],
        interaction_id: "choice-item-005",
      },
    ],
    gap_open_cloze_interactions: [],
    item_id: "item-005",
    item_type: "multiple_response",
    max_score: 1,
    prompt_html: null,
    prompt_lines: ["Vilka två alternativ är korrekta?"],
    sequence: 5,
    source_item_fingerprint: "sha256:item-005",
    title: "Fråga 5",
  };
}

function sourceGapItem() {
  return {
    choice_interactions: [],
    gap_open_cloze_interactions: [
      {
        answer_key: null,
        gaps: [{ gap_id: "gap-001" }, { gap_id: "gap-002" }],
        interaction_id: "gap-item-013",
      },
    ],
    item_id: "item-013",
    item_type: "gap_fill",
    max_score: 2,
    prompt_html: null,
    prompt_lines: ["Lucktext om ekologi."],
    sequence: 13,
    source_item_fingerprint: "sha256:item-013",
    title: "Fråga 13",
  };
}

export function correctionApplyResult() {
  return {
    answer_key_review_state: {
      schema_version: ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
      items: [
        {
          choice_ids: [],
          choice_interaction_ids: [],
          correction_affordances: [],
          current_key_origin: "source_provided",
          gap_ids: [],
          gap_interaction_ids: [],
          item_id: "item-001",
          item_type: "gap_fill",
          message_key: "exam_converter.answer_key.source_present",
          provenance_detail: null,
          reasons: ["source_answer_key_present"],
          replay_artifact_references: replayArtifactReferences(),
          review_state: "review_complete",
          sequence: 1,
          source_item_fingerprint: "sha256:item-001",
        },
        {
          choice_ids: ["choice-3"],
          choice_interaction_ids: ["choice-item-004"],
          correction_affordances: [],
          current_key_origin: "teacher_authored",
          gap_ids: [],
          gap_interaction_ids: [],
          item_id: "item-004",
          item_type: "single_choice",
          message_key: "exam_converter.answer_key.teacher_answer_key_present",
          provenance_detail: null,
          reasons: ["teacher_answer_key_present"],
          replay_artifact_references: replayArtifactReferences(),
          review_state: "teacher_modified",
          sequence: 4,
          source_item_fingerprint: "sha256:item-004",
        },
        {
          choice_ids: ["choice-1", "choice-2"],
          choice_interaction_ids: ["choice-item-005"],
          correction_affordances: [],
          current_key_origin: "reviewed_advisory",
          gap_ids: [],
          gap_interaction_ids: [],
          item_id: "item-005",
          item_type: "multiple_response",
          message_key: "exam_converter.answer_key.reviewed_advisory_accepted",
          provenance_detail: null,
          reasons: ["reviewed_advisory_accepted"],
          replay_artifact_references: replayArtifactReferences(),
          review_state: "review_complete",
          sequence: 5,
          source_item_fingerprint: "sha256:item-005",
        },
        {
          choice_ids: [],
          choice_interaction_ids: [],
          correction_affordances: [],
          current_key_origin: "none",
          gap_ids: [],
          gap_interaction_ids: [],
          item_id: "item-006",
          item_type: "open_ended",
          message_key: "exam_converter.answer_key.source_present",
          provenance_detail: null,
          reasons: ["source_answer_key_present"],
          replay_artifact_references: replayArtifactReferences(),
          review_state: "review_complete",
          sequence: 6,
          source_item_fingerprint: "sha256:item-006",
        },
        {
          choice_ids: [],
          choice_interaction_ids: [],
          correction_affordances: [],
          current_key_origin: "teacher_edited_advisory",
          gap_ids: [],
          gap_interaction_ids: [],
          item_id: "item-012",
          item_type: "open_ended",
          message_key: "exam_converter.answer_key.teacher_modified",
          provenance_detail: null,
          reasons: ["teacher_edited_advisory_candidate"],
          replay_artifact_references: replayArtifactReferences(),
          review_state: "teacher_modified",
          sequence: 12,
          source_item_fingerprint: "sha256:item-012",
        },
        {
          choice_ids: [],
          choice_interaction_ids: [],
          correction_affordances: [],
          current_key_origin: "teacher_authored",
          gap_ids: ["gap-001", "gap-002"],
          gap_interaction_ids: ["gap-item-013"],
          item_id: "item-013",
          item_type: "gap_fill",
          message_key: "exam_converter.answer_key.teacher_answer_key_present",
          provenance_detail: null,
          reasons: ["teacher_answer_key_present"],
          replay_artifact_references: replayArtifactReferences(),
          review_state: "teacher_modified",
          sequence: 13,
          source_item_fingerprint: "sha256:item-013",
        },
      ],
    },
    artifact_availability: [
      { artifact_key: "examnet_pdf", availability: "available", unavailable_code: null },
      { artifact_key: "qti_package", availability: "available", unavailable_code: null },
    ],
    correction_report: {
      accepted_entries: [],
      rejected_entries: [],
      schema_version: "exam_authoring_correction_report_v1",
    },
    effective_state: {
      effective_state_sha256: "sha256:effective-state",
      items: [
        {
          ...sourceChoiceItem(),
          choice_interactions: [
            {
              ...sourceChoiceItem().choice_interactions[0],
              answer_key: {
                correct_choice_ids: ["choice-3"],
                provenance: "reviewed",
              },
            },
          ],
        },
        {
          ...sourceGapItem(),
          gap_open_cloze_interactions: [
            {
              ...sourceGapItem().gap_open_cloze_interactions[0],
              answer_key: {
                accepted_values: [
                  { gap_id: "gap-001", value: "kretslopp" },
                  { gap_id: "gap-002", value: "näringsväv" },
                ],
                provenance: "reviewed",
              },
            },
          ],
        },
      ],
      schema_version: "exam_authoring_effective_state_v1",
    },
    request_id: "correction-session-replay-local-conversion-hub-job-1-v1",
    schema_version: "exam_authoring_corrections_apply_result_v1",
    source_binding: correctionSourceState().source_binding,
    target_readiness: {
      schema_version: "target_readiness_report_v1",
      targets: [
        readyTarget("examnet_pdf"),
        readyTarget("qti_package"),
      ],
    },
  };
}

function readyTarget(target: "examnet_pdf" | "qti_package") {
  return {
    export_enabled: true,
    item_id: null,
    message_key: "exam_converter.target.ready",
    readiness: "ready",
    reason_code: "target_available",
    sequence: null,
    target,
  };
}
