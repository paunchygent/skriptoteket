/**
 * Sir Convert reviewed-completion browser contract specs.
 *
 * Domain purpose:
 *   Prove authenticated DigiExam migration requests and overlays preserve the
 *   two-pass AI-facit review contract expected by Sir Convert.
 *
 * Relationships:
 *   - Exercises `submitDigiExamMigration` through the Gateway browser client.
 *   - Guards generated reviewed-completion lineage types used by Exam Converter.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { createTestUser } from "../../stores/authTestHelpers";
import { useAuthStore } from "../../stores/auth";
import { submitDigiExamMigration } from ".";
import type {
  DigiExamEffectiveAnswerKey,
  DigiExamEffectiveExam,
  DigiExamEffectivePointCorrection,
  DigiExamIngestionOverlay,
  DigiExamOverlayPointCorrection,
} from "./types";
import {
  DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
} from "./schemaVersions";

function jsonResponse(payload: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  if (!headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  return new Response(JSON.stringify(payload), { ...init, headers });
}

function mockJson(payload: unknown, init: ResponseInit = {}): void {
  vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(payload, init));
}

function dxeFile(): File {
  return new File(["dxe"], "exam.dxe", { type: "application/octet-stream" });
}

function expectFormDataFile(
  value: FormDataEntryValue | null,
  expected: { name: string; type: string },
): void {
  expect(value).toBeInstanceOf(File);
  const file = value as File;
  expect(file.name).toBe(expected.name);
  expect(file.type).toBe(expected.type);
}

function requestHeaders(callIndex: number): Headers {
  const init = vi.mocked(fetch).mock.calls[callIndex][1] as RequestInit;
  return init.headers as Headers;
}

describe("Sir Convert Gateway reviewed-completion contract", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
    const auth = useAuthStore();
    auth.user = createTestUser();
    auth.csrfToken = "csrf-token";
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("submits governed multipart jobs through the HuleEdu Gateway edge", async () => {
    mockJson(
      { job: { job_id: "job_1", status: "queued" } },
      { status: 202, headers: { "X-Idempotent-Replay": "true" } },
    );

    const file = dxeFile();
    const gradedResultPdf = new File(["answers"], "graded-result.pdf", {
      type: "application/pdf",
    });
    const submitted = await submitDigiExamMigration({
      file,
      gradedResultPdf,
      targets: ["examnet_pdf"],
      correlationId: "corr_teacher_action_001",
    });

    expect(submitted).toMatchObject({
      jobId: "job_1",
      status: "queued",
      idempotentReplay: true,
    });
    expect(fetch).toHaveBeenCalledWith(
      "/sir-convert/v2/convert/jobs?wait_seconds=0",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
    expect(vi.mocked(fetch).mock.contexts[0]).toBeUndefined();
    const headers = requestHeaders(0);
    expect(headers.get("X-Correlation-ID")).toBe("corr_teacher_action_001");
    expect(headers.get("Idempotency-Key")).toMatch(/^idem_skriptoteket_[0-9a-f]{48}$/);
    expect(headers.get("X-CSRF-Token")).toBe("csrf-token");
    expect(headers.get("X-API-Key")).toBeNull();
    expect(headers.get("Content-Type")).toBeNull();

    const init = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
    const formData = init.body as FormData;
    expectFormDataFile(formData.get("file"), {
      name: "exam.dxe",
      type: "application/octet-stream",
    });
    expectFormDataFile(formData.get("graded_result_pdf"), {
      name: "graded-result.pdf",
      type: "application/pdf",
    });
    expect(formData.has("parity_pdf")).toBe(false);

    const jobSpec = JSON.parse(String(formData.get("job_spec"))) as {
      conversion: { output_format: string; targets: string[] };
      digiexam_migration_options: {
        completion_mode: string;
        remote_provider_policy: string;
        result_pdf_usage: string;
        manual_follow_up_policy: string;
      };
      source: { format: string };
    };
    expect(jobSpec.source.format).toBe("digiexam_dxe");
    expect(jobSpec.conversion.output_format).toBe("examnet_migration_bundle");
    expect(jobSpec.conversion.targets).toEqual(["examnet_pdf"]);
    expect(jobSpec.digiexam_migration_options).toMatchObject({
      completion_mode: "local_llm_suggest_missing_machine_marked",
      remote_provider_policy: "forbidden",
      result_pdf_usage: "correct_machine_marked_answers_only",
      manual_follow_up_policy: "emit_item_addressable_report",
    });
  });

  it("submits teacher answer-key overlays as a governed multipart JSON part", async () => {
    mockJson({ job: { job_id: "job_overlay", status: "queued" } }, { status: 202 });

    await submitDigiExamMigration({
      completionMode: "source_evidence_only",
      file: dxeFile(),
      ingestionOverlay: {
        schema_version: DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
        source_binding: {
          source_file_sha256: "sha256:source",
          source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
          source_ir_sha256: "sha256:ir",
        },
        items: [
          {
            effective_item_patch: null,
            item_id: "item-001",
            manual_answer_key: {
              correct_alternative_ids: [1],
              kind: "choice",
            },
            point_correction: null,
            sequence: 1,
            item_type: "multiple_choice",
            source_item_fingerprint: "sha256:item",
            review_decision: null,
            reviewed_completion_answer_key: null,
          },
        ],
      },
      targets: ["qti_package"],
    });

    const init = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
    const formData = init.body as FormData;
    const overlay = formData.get("digiexam_ingestion_overlay");
    expect(overlay).toBeInstanceOf(File);
    expect((overlay as File).name).toBe("digiexam-ingestion-overlay.json");

    const jobSpec = JSON.parse(String(formData.get("job_spec"))) as {
      digiexam_migration_options: {
        ingestion_overlay_filename?: string;
        ingestion_overlay_policy?: string;
      };
    };
    expect(jobSpec.digiexam_migration_options.ingestion_overlay_filename).toBe(
      "digiexam-ingestion-overlay.json",
    );
    expect(jobSpec.digiexam_migration_options.ingestion_overlay_policy).toBe(
      "apply_teacher_overlay",
    );
    expect(jobSpec.digiexam_migration_options).toMatchObject({
      completion_mode: "source_evidence_only",
      remote_provider_policy: "forbidden",
    });
  });

  it("keeps Task 306 reviewed-completion fields in the generated Sir Convert contract", () => {
    const reviewedOverlayItem = {
      effective_item_patch: null,
      item_id: "item-001",
      item_type: "multiple_choice",
      manual_answer_key: null,
      point_correction: null,
      review_decision: null,
      reviewed_completion_answer_key: {
        answer_payload: {
          correct_alternative_ids: [1],
          kind: "choice",
        },
        candidate_lineage: {
          candidate_id: "candidate-001",
          candidate_payload_digest: "sha256:candidate",
          completion_report_sha256: "sha256:report",
          prompt_template_version: "digiexam-choice-answer-key-v1",
          provider_profile_id: "local-fixture",
          schema_name: "digiexam_choice_answer_key_decision_v1",
          schema_version: "digiexam_choice_answer_key_decision_v1",
          validation_state: "valid",
        },
        kind: "choice",
        review_decision_id: "review-001",
        review_outcome: "accepted_unchanged",
      },
      sequence: 1,
      source_item_fingerprint: "sha256:item",
    } satisfies DigiExamIngestionOverlay["items"][number];
    const effectiveAnswerKey = {
      correct_alternative_ids: [1],
      lineage: {
        candidate_id: "candidate-001",
        candidate_payload_digest: "sha256:candidate",
        completion_report_sha256: "sha256:report",
        prompt_template_version: "digiexam-choice-answer-key-v1",
        provider_profile_id: "local-fixture",
        review_decision_id: "review-001",
        review_outcome: "accepted_unchanged",
        schema_name: "digiexam_choice_answer_key_decision_v1",
        schema_version: "digiexam_choice_answer_key_decision_v1",
        validation_state: "valid",
      },
      provenance: "reviewed",
    } satisfies DigiExamEffectiveAnswerKey;

    expect(
      reviewedOverlayItem.reviewed_completion_answer_key?.candidate_lineage.validation_state,
    ).toBe("valid");
    expect(effectiveAnswerKey.lineage?.review_outcome).toBe("accepted_unchanged");
  });

  it("keeps Task 322 point-correction fields in the generated Sir Convert contract", () => {
    const pointCorrection = {
      kind: "item_points",
      max_score: 4,
    } satisfies DigiExamOverlayPointCorrection;
    const effectivePointCorrection = {
      effective_max_score: 4,
      kind: "item_points",
      source_item_fingerprint: "sha256:item",
      source_max_score: 2,
    } satisfies DigiExamEffectivePointCorrection;
    const overlayItem = {
      effective_item_patch: null,
      item_id: "item-001",
      item_type: "single_choice",
      manual_answer_key: null,
      point_correction: pointCorrection,
      review_decision: null,
      reviewed_completion_answer_key: null,
      sequence: 1,
      source_item_fingerprint: "sha256:item",
    } satisfies DigiExamIngestionOverlay["items"][number];
    const effectiveExam = {
      answer_key_completion_report_sha256: null,
      ingestion_overlay_sha256: "sha256:overlay",
      items: [
        {
          applied_overlay_entry_ids: ["item-001"],
          effective_answer_key: null,
          effective_item_patch: null,
          effective_point_correction: effectivePointCorrection,
          item_id: "item-001",
          item_type: "single_choice",
          review_decisions: [],
          sequence: 1,
          source_item_fingerprint: "sha256:item",
        },
      ],
      schema_version: "digiexam_effective_exam_v2",
      source_file_sha256: "sha256:source",
      source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
      source_ir_sha256: "sha256:ir",
    } satisfies DigiExamEffectiveExam;

    expect(overlayItem.point_correction.max_score).toBe(4);
    expect(effectiveExam.items[0]?.effective_point_correction?.effective_max_score).toBe(4);
  });
});
