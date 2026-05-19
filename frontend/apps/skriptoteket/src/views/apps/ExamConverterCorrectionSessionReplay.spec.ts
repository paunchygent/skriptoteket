/**
 * Exam Converter correction-session replay specs.
 *
 * Domain purpose:
 *   Prove persisted Skriptoteket correction intents are replayed as a complete
 *   source-bound set through the HuleEdu Sir Convert Gateway client.
 *
 * Relationships:
 *   - Covers `correctionSessionReplay.ts` before PR-0336 wires the UI.
 *   - Uses generated Skriptoteket and Sir Convert contract types.
 */

import { describe, expect, it, vi } from "vitest";

import type {
  ExamConverterCorrectionIntentResponse,
  ExamConverterCorrectionSessionResponse,
} from "../../api/examConverterCorrectionSessions";
import type {
  ExamAuthoringCorrectionSourceStateIssueResult,
  ExamAuthoringCorrectionsApplyRequest,
  ExamAuthoringCorrectionsApplyResult,
} from "../../api/sirConvertGateway";
import {
  replayPersistedCorrectionSession,
  type CorrectionSessionReplayDependencies,
} from "./exam-converter-authenticated/correctionSessionReplay";

const CONVERSION_HUB_JOB_ID = "11111111-1111-4111-8111-111111111111";
const OWNER_USER_ID = "22222222-2222-4222-8222-222222222222";
const SESSION_ID = "33333333-3333-4333-8333-333333333333";
const CORRELATION_ID = "44444444-4444-4444-8444-444444444444";
const SIR_CONVERT_JOB_ID = "job_exam_converter_review";

function gatewaySourceBinding(
  overrides: Partial<ExamAuthoringCorrectionSourceStateIssueResult["source_binding"]> = {},
): ExamAuthoringCorrectionSourceStateIssueResult["source_binding"] {
  return {
    source_authoring_schema_version: "exam_authoring_ir_v1",
    source_bundle_id: "bundle-001",
    source_file_sha256: "sha256:source-file",
    source_state_sha256: "sha256:source-state",
    source_state_signature: "signed-source-state",
    ...overrides,
  };
}

function intent(
  overrides: Partial<ExamConverterCorrectionIntentResponse>,
): ExamConverterCorrectionIntentResponse {
  const kind = overrides.kind ?? "point_correction";
  const itemId = overrides.item_id ?? "item-001";
  const sequence = overrides.sequence ?? 1;
  const sourceItemFingerprint =
    overrides.source_item_fingerprint ?? `sha256:${itemId}`;
  const targetKey =
    overrides.target_key ?? `${kind}:${itemId}:${sequence}:multiple_choice:${sourceItemFingerprint}`;
  return {
    entry_id: `corr-${kind}-${itemId}`,
    intent_id: "55555555-5555-4555-8555-555555555555",
    item_id: itemId,
    item_type: overrides.item_type ?? "multiple_choice",
    kind,
    payload: { max_score: 2 },
    sequence,
    source_binding: gatewaySourceBinding(),
    source_item_fingerprint: sourceItemFingerprint,
    target: {},
    target_key: targetKey,
    ...overrides,
  };
}

function correctionSession(
  activeIntents: ExamConverterCorrectionIntentResponse[],
  overrides: Partial<ExamConverterCorrectionSessionResponse> = {},
): ExamConverterCorrectionSessionResponse {
  return {
    active_intents: activeIntents,
    conversion_hub_job_id: CONVERSION_HUB_JOB_ID,
    owner_user_id: OWNER_USER_ID,
    session_id: SESSION_ID,
    session_version: 7,
    source_binding: gatewaySourceBinding(),
    ...overrides,
  };
}

function issuedSourceState(
  overrides: Partial<ExamAuthoringCorrectionSourceStateIssueResult> = {},
): ExamAuthoringCorrectionSourceStateIssueResult {
  return {
    schema_version: "exam_authoring_correction_source_state_issue_result_v1",
    source_authoring_state: {
      items: [
        sourceItem("item-001", 1, "multiple_choice"),
        sourceItem("item-002", 2, "gap_fill"),
        sourceItem("item-003", 1, "open_ended"),
      ],
      schema_version: "exam_authoring_correction_source_state_v1",
      source_authoring_schema_version: "exam_authoring_ir_v1",
      source_state_sha256: "sha256:source-state",
    },
    source_binding: gatewaySourceBinding(),
    ...overrides,
  };
}

function sourceItem(itemId: string, sequence: number, itemType: string) {
  return {
    choice_interactions: [],
    gap_open_cloze_interactions: [],
    item_id: itemId,
    item_type: itemType,
    matching_interactions: [],
    max_score: null,
    prompt_html: null,
    prompt_lines: [`Prompt ${itemId}`],
    sequence,
    source_item_fingerprint: `sha256:${itemId}`,
    title: `Question ${sequence}`,
  };
}

function replayResult(
  request: ExamAuthoringCorrectionsApplyRequest,
): ExamAuthoringCorrectionsApplyResult {
  return {
    artifact_availability: [
      {
        artifact_key: "examnet_pdf",
        availability: "available",
        unavailable_code: null,
      },
    ],
    correction_report: {
      accepted_entries: [
        {
          applied_fields: ["max_score"],
          effective_provenance: "teacher_provided",
          entry_id: request.corrections[0]?.entry_id ?? "corr-missing",
          item_id: request.corrections[0]?.item_id ?? "item-missing",
          kind: request.corrections[0]?.kind ?? "point_correction",
          sequence: request.corrections[0]?.sequence ?? 1,
        },
      ],
      rejected_entries: [],
      schema_version: "exam_authoring_correction_report_v1",
    },
    effective_state: {
      effective_state_sha256: "sha256:effective-state",
      items: issuedSourceState().source_authoring_state.items,
      schema_version: "exam_authoring_effective_state_v1",
    },
    request_id: request.request_id,
    schema_version: "exam_authoring_corrections_apply_result_v1",
    source_binding: request.source_binding,
    target_readiness: {
      schema_version: "target_readiness_report_v1",
      targets: [
        {
          export_enabled: true,
          item_id: null,
          message_key: "exam_converter.target.ready",
          reason_code: "ready",
          readiness: "ready",
          target: "examnet_pdf",
        },
      ],
    },
  };
}

function replayDependencies(params: {
  apply?: CorrectionSessionReplayDependencies["applyCorrections"];
  issue?: CorrectionSessionReplayDependencies["issueSourceState"];
  session: ExamConverterCorrectionSessionResponse;
}): CorrectionSessionReplayDependencies {
  const applyCorrections =
    params.apply ??
    vi.fn(({ request }: { request: ExamAuthoringCorrectionsApplyRequest }) =>
      Promise.resolve(replayResult(request)),
    );
  return {
    applyCorrections,
    issueSourceState: params.issue ?? vi.fn(() => Promise.resolve(issuedSourceState())),
    loadCorrectionSession: vi.fn(() => Promise.resolve(params.session)),
  };
}

async function replay(params: {
  dependencies: CorrectionSessionReplayDependencies;
  requestedTargets?: ("examnet_pdf" | "qti_package")[];
}) {
  return await replayPersistedCorrectionSession({
    conversionHubJobId: CONVERSION_HUB_JOB_ID,
    correlationId: CORRELATION_ID,
    dependencies: params.dependencies,
    requestedTargets: params.requestedTargets,
    sirConvertJobId: SIR_CONVERT_JOB_ID,
  });
}

describe("correction-session replay orchestration", () => {
  it("loads persisted intents, issues fresh source state, and submits the complete deterministic set", async () => {
    const session = correctionSession([
      intent({
        entry_id: "corr-choice-item-002",
        item_id: "item-002",
        item_type: "gap_fill",
        kind: "manual_gap_open_cloze_answer_key",
        payload: {
          candidate_lineage: null,
          gap_answers: [{ accepted_values: ["kretslopp"], gap_id: "gap-001" }],
          interaction_id: "gap-item-002",
          submission_origin: "teacher_authored",
        },
        sequence: 2,
        source_item_fingerprint: "sha256:item-002",
        target_key: "manual_gap_open_cloze_answer_key:item-002",
      }),
      intent({
        entry_id: "corr-points-item-001",
        kind: "point_correction",
        payload: { max_score: 3 },
        target_key: "point_correction:item-001",
      }),
      intent({
        entry_id: "corr-choice-item-001",
        kind: "manual_choice_answer_key",
        payload: {
          candidate_lineage: null,
          correct_choice_ids: ["choice-001"],
          interaction_id: "choice-item-001",
          submission_origin: "teacher_authored",
        },
        target_key: "manual_choice_answer_key:item-001",
      }),
      intent({
        entry_id: "corr-suppress-item-001",
        kind: "candidate_suppression",
        payload: {
          candidate_lineage: {
            candidate_id: "candidate-item-001",
            candidate_payload_digest: "sha256:candidate-item-001",
            completion_report_sha256: "sha256:completion-report",
            prompt_template_version: "prompt-v1",
            provider_profile_id: "provider-local",
            schema_name: "digiexam_choice_answer_key_decision_v1",
            schema_version: "1",
            validation_state: "valid",
          },
        },
        target_key: "candidate_suppression:item-001",
      }),
      intent({
        entry_id: "corr-text-item-001",
        kind: "item_text_patch",
        payload: { patches: [{ field: "prompt_lines", value: "Updated prompt" }] },
        target_key: "item_text_patch:item-001",
      }),
    ]);
    const dependencies = replayDependencies({ session });

    const result = await replay({ dependencies, requestedTargets: ["qti_package"] });

    expect(dependencies.loadCorrectionSession).toHaveBeenCalledWith({
      conversionHubJobId: CONVERSION_HUB_JOB_ID,
    });
    expect(dependencies.issueSourceState).toHaveBeenCalledWith({
      correlationId: CORRELATION_ID,
      request: {
        expected_source_state_sha256: "sha256:source-state",
        job_id: SIR_CONVERT_JOB_ID,
        schema_version: "exam_authoring_correction_source_state_issue_request_v1",
      },
    });
    expect(dependencies.applyCorrections).toHaveBeenCalledTimes(1);
    const request = vi.mocked(dependencies.applyCorrections).mock.calls[0]?.[0].request;
    expect(request?.requested_targets).toEqual(["qti_package"]);
    expect(request?.corrections.map((correction) => correction.kind)).toEqual([
      "candidate_suppression",
      "item_text_patch",
      "point_correction",
      "manual_choice_answer_key",
      "manual_gap_open_cloze_answer_key",
    ]);
    expect(JSON.stringify(request)).not.toContain("review_decision");
    expect(JSON.stringify(request)).not.toContain("manual_matching_answer_key");
    expect(result).toMatchObject({
      projectionFreshness: "fresh",
      savedIntentCount: 5,
      submittedCorrectionCount: 5,
    });
  });

  it("rejects stale source state before apply when persisted binding no longer matches", async () => {
    const session = correctionSession([
      intent({
        entry_id: "corr-points-item-001",
        kind: "point_correction",
        payload: { max_score: 3 },
      }),
    ]);
    const dependencies = replayDependencies({
      issue: vi.fn(() =>
        Promise.resolve(
          issuedSourceState({
            source_binding: gatewaySourceBinding({
              source_state_sha256: "sha256:new-source-state",
            }),
            source_authoring_state: {
              ...issuedSourceState().source_authoring_state,
              source_state_sha256: "sha256:new-source-state",
            },
          }),
        ),
      ),
      session,
    });

    const result = await replay({ dependencies });

    expect(dependencies.applyCorrections).not.toHaveBeenCalled();
    expect(result).toEqual({
      correctionSession: session,
      projectionFreshness: "stale_source",
      reasonCode: "source_binding_mismatch",
      savedIntentCount: 1,
      staleIntentEntryIds: ["corr-points-item-001"],
    });
  });

  it("rejects mismatched item fingerprints before apply", async () => {
    const session = correctionSession([
      intent({
        entry_id: "corr-points-item-001",
        kind: "point_correction",
        payload: { max_score: 3 },
      }),
    ]);
    const dependencies = replayDependencies({
      issue: vi.fn(() =>
        Promise.resolve(
          issuedSourceState({
            source_authoring_state: {
              ...issuedSourceState().source_authoring_state,
              items: [
                {
                  ...sourceItem("item-001", 1, "multiple_choice"),
                  source_item_fingerprint: "sha256:changed-item-001",
                },
              ],
            },
          }),
        ),
      ),
      session,
    });

    const result = await replay({ dependencies });

    expect(dependencies.applyCorrections).not.toHaveBeenCalled();
    expect(result).toMatchObject({
      projectionFreshness: "stale_source",
      reasonCode: "source_item_mismatch",
      staleIntentEntryIds: ["corr-points-item-001"],
    });
  });

  it("preserves saved-intent truth when source state or apply is unavailable", async () => {
    const session = correctionSession([
      intent({
        entry_id: "corr-points-item-001",
        kind: "point_correction",
        payload: { max_score: 3 },
      }),
    ]);
    const sourceUnavailable = replayDependencies({
      issue: vi.fn().mockRejectedValue(new Error("Gateway unavailable")),
      session,
    });
    const applyUnavailable = replayDependencies({
      apply: vi.fn().mockRejectedValue(new Error("Sir Convert unavailable")),
      session,
    });

    await expect(replay({ dependencies: sourceUnavailable })).resolves.toEqual({
      correctionSession: session,
      projectionFreshness: "unavailable",
      reasonCode: "source_state_unavailable",
      savedIntentCount: 1,
    });
    await expect(replay({ dependencies: applyUnavailable })).resolves.toEqual({
      correctionSession: session,
      projectionFreshness: "unavailable",
      reasonCode: "apply_unavailable",
      savedIntentCount: 1,
    });
  });

  it("returns only Sir Convert replayed effective-state evidence as fresh projection truth", async () => {
    const session = correctionSession([
      intent({
        entry_id: "corr-points-item-001",
        kind: "point_correction",
        payload: { max_score: 3 },
      }),
    ]);
    const dependencies = replayDependencies({ session });

    const result = await replay({ dependencies });

    expect(result.projectionFreshness).toBe("fresh");
    if (result.projectionFreshness !== "fresh") {
      throw new Error("Expected fresh replay projection.");
    }
    expect(result.effectiveState.effective_state_sha256).toBe("sha256:effective-state");
    expect(result.artifactAvailability).toEqual([
      {
        artifact_key: "examnet_pdf",
        availability: "available",
        unavailable_code: null,
      },
    ]);
    expect(result.targetReadiness.targets).toEqual([
      expect.objectContaining({
        export_enabled: true,
        readiness: "ready",
        target: "examnet_pdf",
      }),
    ]);
  });
});
