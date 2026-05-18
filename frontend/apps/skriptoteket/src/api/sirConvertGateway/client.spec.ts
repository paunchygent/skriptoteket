/**
 * Sir Convert Gateway browser client specs.
 *
 * Domain purpose:
 *   Prove authenticated browser transport, artifact loading, and user-file save
 *   behavior for the Skriptoteket Sir Convert Gateway integration.
 *
 * Relationships:
 *   - Complements `completionContract.spec.ts`, which owns reviewed-completion
 *     JobSpec and overlay contract coverage.
 */

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { createTestUser } from "../../stores/authTestHelpers";
import { useAuthStore } from "../../stores/auth";
import {
  applyExamAuthoringCorrections,
  buildSirConvertUserFileSaveMetadata,
  downloadDigiExamMigrationArtifact,
  getDigiExamMigrationJob,
  getDigiExamMigrationResult,
  issueExamAuthoringCorrectionSourceState,
  isSirConvertArtifactAvailable,
  listDigiExamMigrationArtifacts,
  saveDigiExamMigrationArtifactToUserFiles,
} from ".";
import {
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
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

function requestHeaders(callIndex: number): Headers {
  const init = vi.mocked(fetch).mock.calls[callIndex][1] as RequestInit;
  return init.headers as Headers;
}

describe("Sir Convert Gateway browser client", () => {
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

  it("reads status, result, manifest, and named artifacts with one correlation ID", async () => {
    mockJson({ job: { job_id: "job_1", status: "running" } });
    mockJson({
      api_version: "v2",
      job_id: "job_1",
      status: "succeeded",
      result: {
        artifact: {
          filename: "artifact-bundle.json",
          content_type: "application/json",
          sha256: "sha256:abc",
          size_bytes: 3281,
        },
        conversion_metadata: {
          route_key: "digiexam_dxe_to_examnet_migration_bundle",
          bundle_schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
          bundle_status: "partial",
          source_sha256: "sha256:def",
          target_readiness_report_artifact_key: "target_readiness_report",
          manual_follow_up_required: true,
          warning_count: 3,
          artifact_count: 9,
        },
      },
    });
    mockJson({
      schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
      job_id: "job_1",
      source: {
        filename: "exam.dxe",
        sha256: "sha256:def",
        format: "digiexam_dxe",
      },
      bundle_status: "needs_review",
      artifacts: [
        {
          artifact_key: "examnet_pdf",
          filename: "examnet-import.pdf",
          content_type: "application/pdf",
          availability: "unavailable",
          size_bytes: null,
          sha256: null,
          unavailable_code: "unsupported_target_shape",
        },
        {
          artifact_key: "qti_package",
          filename: "qti-package.zip",
          content_type: "application/zip",
          availability: "not_requested",
          size_bytes: null,
          sha256: null,
        },
      ],
      manual_follow_up: {
        required: true,
        artifact_key: "manual_follow_up_report",
        count: 2,
      },
      warnings: {
        artifact_key: "warnings_report",
        count: 3,
      },
      readiness: {
        artifact_key: "target_readiness_report",
        exportable_targets: [],
        review_required: true,
      },
      source_binding: {
        source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
        source_ir_sha256: "sha256:ir",
        effective_exam_schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
        effective_exam_sha256: "sha256:effective",
      },
    });
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(new Blob(["pdf"]), {
        status: 200,
        headers: {
          "content-type": "application/pdf",
          "content-disposition": 'attachment; filename="examnet-import.pdf"',
        },
      }),
    );

    await expect(
      getDigiExamMigrationJob({ jobId: "job_1", correlationId: "corr_1" }),
    ).resolves.toMatchObject({ jobId: "job_1", status: "running" });
    const result = await getDigiExamMigrationResult({
      jobId: "job_1",
      correlationId: "corr_1",
    });
    const manifest = await listDigiExamMigrationArtifacts({
      jobId: "job_1",
      correlationId: "corr_1",
    });
    const artifact = await downloadDigiExamMigrationArtifact({
      jobId: "job_1",
      artifactKey: "examnet_pdf",
      correlationId: "corr_1",
    });

    expect(result.conversion_metadata.bundle_status).toBe("partial");
    expect(manifest.bundle_status).toBe("needs_review");
    expect(isSirConvertArtifactAvailable(manifest.artifacts[0])).toBe(false);
    expect(artifact.filename).toBe("examnet-import.pdf");

    expect(vi.mocked(fetch).mock.calls.map((call) => call[0])).toEqual([
      "/sir-convert/v2/convert/jobs/job_1",
      "/sir-convert/v2/convert/jobs/job_1/result",
      "/sir-convert/v2/convert/jobs/job_1/artifacts",
      "/sir-convert/v2/convert/jobs/job_1/artifacts/examnet_pdf",
    ]);
    for (const index of [0, 1, 2, 3]) {
      expect(requestHeaders(index).get("X-Correlation-ID")).toBe("corr_1");
      expect(requestHeaders(index).get("X-API-Key")).toBeNull();
    }
  });

  it("reads v3 terminal results without obsolete target availability state", async () => {
    mockJson({
      api_version: "v2",
      job_id: "job_1",
      status: "succeeded",
      result: {
        artifact: {
          filename: "artifact-bundle.json",
          content_type: "application/json",
          sha256: "sha256:abc",
          size_bytes: 6300,
        },
        conversion_metadata: {
          route_key: "digiexam_dxe_to_examnet_migration_bundle",
          bundle_schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
          bundle_status: "failed",
          source_sha256: "sha256:def",
          target_readiness_report_artifact_key: "target_readiness_report",
          manual_follow_up_required: true,
          warning_count: 11,
          artifact_count: 13,
        },
      },
    });

    const result = await getDigiExamMigrationResult({
      jobId: "job_1",
      correlationId: "corr_1",
    });

    expect(result.conversion_metadata.bundle_status).toBe("failed");
    expect(result.conversion_metadata.target_readiness_report_artifact_key).toBe(
      "target_readiness_report",
    );
  });

  it("uses a configured Gateway base without changing the route family", async () => {
    vi.stubEnv(
      "VITE_HULEEDU_SIR_CONVERT_BASE_URL",
      "https://api.example.test/sir-convert/v2/convert/",
    );
    mockJson({ job: { job_id: "job_2", status: "queued" } });

    await getDigiExamMigrationJob({ jobId: "job_2", correlationId: "corr_2" });

    expect(fetch).toHaveBeenCalledWith(
      "https://api.example.test/sir-convert/v2/convert/jobs/job_2",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("allows the local HuleEdu Gateway base for explicit browser proof", async () => {
    vi.stubEnv(
      "VITE_HULEEDU_SIR_CONVERT_BASE_URL",
      "http://127.0.0.1:8080/sir-convert/v2/convert/",
    );
    mockJson({ job: { job_id: "job_2", status: "queued" } });

    await getDigiExamMigrationJob({ jobId: "job_2", correlationId: "corr_2" });

    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8080/sir-convert/v2/convert/jobs/job_2",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("submits unified non-matching correction calls through the HuleEdu Gateway edge", async () => {
    mockJson({
      schema_version: "exam_authoring_correction_source_state_issue_result_v1",
      source_binding: {
        source_authoring_schema_version: "exam_authoring_ir_v1",
        source_bundle_id: "job_1",
        source_file_sha256: "sha256:source",
        source_state_sha256: "sha256:source-state",
        source_state_signature: "hmac-sha256:signature",
      },
      source_authoring_state: {
        schema_version: "exam_authoring_correction_source_state_v1",
        source_authoring_schema_version: "exam_authoring_ir_v1",
        source_state_sha256: "sha256:source-state",
        items: [],
      },
    });
    mockJson({
      schema_version: "exam_authoring_corrections_apply_result_v1",
      request_id: "correction-point-item-001",
      source_binding: {
        source_authoring_schema_version: "exam_authoring_ir_v1",
        source_bundle_id: "job_1",
        source_file_sha256: "sha256:source",
        source_state_sha256: "sha256:source-state",
        source_state_signature: "hmac-sha256:signature",
      },
      effective_state: {
        schema_version: "exam_authoring_effective_state_v1",
        effective_state_sha256: "sha256:effective-state",
        items: [],
      },
      correction_report: {
        schema_version: "exam_authoring_correction_report_v1",
        accepted_entries: [
          {
            applied_fields: ["point_correction"],
            entry_id: "corr-1",
            item_id: "item-001",
            kind: "point_correction",
            sequence: 1,
          },
        ],
        rejected_entries: [],
      },
      target_readiness: {
        schema_version: "target_readiness_report_v1",
        targets: [],
      },
      artifact_availability: [],
    });

    const sourceState = await issueExamAuthoringCorrectionSourceState({
      correlationId: "corr_1",
      request: {
        schema_version: "exam_authoring_correction_source_state_issue_request_v1",
        job_id: "job_1",
      },
    });
    await applyExamAuthoringCorrections({
      correlationId: "corr_1",
      request: {
        schema_version: "exam_authoring_corrections_apply_request_v1",
        request_id: "correction-point-item-001",
        source_binding: sourceState.source_binding,
        source_authoring_state: sourceState.source_authoring_state,
        corrections: [
          {
            entry_id: "corr-point-item-001",
            item_id: "item-001",
            item_type: "open_ended",
            kind: "point_correction",
            max_score: 3,
            sequence: 1,
            source_item_fingerprint: "sha256:item",
          },
        ],
        requested_targets: ["examnet_pdf"],
      },
    });

    expect(vi.mocked(fetch).mock.calls.map((call) => call[0])).toEqual([
      "/sir-convert/v2/exam-authoring/corrections/source-state/issue",
      "/sir-convert/v2/exam-authoring/corrections/apply",
    ]);
    for (const index of [0, 1]) {
      expect(requestHeaders(index).get("X-Correlation-ID")).toBe("corr_1");
      expect(requestHeaders(index).get("X-CSRF-Token")).toBe("csrf-token");
      expect(requestHeaders(index).get("X-API-Key")).toBeNull();
    }
    const applyBody = JSON.parse(String(vi.mocked(fetch).mock.calls[1][1]?.body));
    expect(applyBody.corrections[0]).toMatchObject({
      kind: "point_correction",
      item_id: "item-001",
    });
    expect(JSON.stringify(applyBody)).not.toContain("manual_matching_answer_key");
  });

  it.each([
    ["https://convert.hule.education/v2/convert"],
    ["http://127.0.0.1:9010/v2/convert"],
    ["http://localhost:8000/sir-convert/v2/convert"],
    ["https://api.hule.education/v2/convert"],
    ["https://api.example.test/v2/convert"],
  ])("rejects non-Gateway configured base %s", async (configuredBase) => {
    vi.stubEnv("VITE_HULEEDU_SIR_CONVERT_BASE_URL", configuredBase);

    await expect(
      getDigiExamMigrationJob({ jobId: "job_2", correlationId: "corr_2" }),
    ).rejects.toThrow("Invalid Sir Convert Gateway base URL");
    expect(fetch).not.toHaveBeenCalled();
  });

  it.each(["unavailable", "failed"] as const)(
    "rejects %s artifact entries without unavailable_code",
    async (availability) => {
      mockJson({
        schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
        job_id: "job_1",
        source: {
          filename: "exam.dxe",
          sha256: "sha256:def",
          format: "digiexam_dxe",
        },
        bundle_status: "needs_review",
        artifacts: [
          {
            artifact_key: "examnet_pdf",
            filename: "examnet-import.pdf",
            content_type: "application/pdf",
            availability,
            size_bytes: null,
            sha256: null,
          },
        ],
        manual_follow_up: null,
        warnings: null,
        readiness: {
          artifact_key: "target_readiness_report",
          exportable_targets: [],
          review_required: true,
        },
        source_binding: {
          source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
          source_ir_sha256: "sha256:ir",
          effective_exam_schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
          effective_exam_sha256: "sha256:effective",
        },
      });

      await expect(
        listDigiExamMigrationArtifacts({ jobId: "job_1", correlationId: "corr_1" }),
      ).rejects.toMatchObject({
        code: "SIR_CONVERT_CONTRACT_DRIFT",
        message: expect.stringContaining("requires unavailable_code"),
      });
    },
  );

  it("preserves upstream error envelopes", async () => {
    mockJson(
      {
        error: {
          code: "qti_validation_failed",
          message: "QTI package is blocked.",
          details: { artifact_key: "qti_package" },
        },
        correlation_id: "corr_upstream",
      },
      { status: 409, statusText: "Conflict" },
    );

    await expect(
      downloadDigiExamMigrationArtifact({
        jobId: "job_1",
        artifactKey: "qti_package",
        correlationId: "corr_1",
      }),
    ).rejects.toMatchObject({
      status: 409,
      code: "qti_validation_failed",
      correlationId: "corr_upstream",
    });
  });

  it("maps artifact bundle provenance for later user-file persistence", () => {
    const checksum = "79fad2af3f64ab5070a9949a71f7681e2043b5c47606dc70b0e68dc4e83150ba";
    const metadata = buildSirConvertUserFileSaveMetadata({
      jobId: "job_1",
      artifact: {
        artifact_key: "examnet_pdf",
        filename: "examnet-import.pdf",
        content_type: "application/pdf",
        availability: "available",
        size_bytes: 100,
        sha256: `sha256:${checksum}`,
      },
      savedDisplayFilename: "Nationellt prov import.pdf",
      correlationId: "corr_1",
      savedAt: new Date("2026-05-13T12:00:00Z"),
    });

    expect(metadata).toEqual({
      sir_convert_job_id: "job_1",
      artifact_key: "examnet_pdf",
      source_filename: "examnet-import.pdf",
      saved_display_filename: "Nationellt prov import.pdf",
      content_type: "application/pdf",
      size_bytes: 100,
      sha256: checksum,
      bundle_schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
      correlation_id: "corr_1",
      saved_at: "2026-05-13T12:00:00.000Z",
    });
  });

  it("saves downloaded named artifacts through the owner-scoped user-file endpoint", async () => {
    mockJson({
      source_artifact_id: "documents.conversion_hub:job_1:examnet_pdf",
      vault_artifact: {
        bytes: 3,
        created_at: "2026-05-14T10:00:00Z",
        file_id: "vault-file-1",
        name: "examnet-import.pdf",
      },
    });

    const saved = await saveDigiExamMigrationArtifactToUserFiles({
      artifact: {
        artifact_key: "examnet_pdf",
        availability: "available",
        content_type: "application/pdf",
        filename: "examnet-import.pdf",
        sha256: null,
        size_bytes: 3,
      },
      artifactBlob: {
        artifactKey: "examnet_pdf",
        blob: new Blob(["pdf"], { type: "application/pdf" }),
        contentType: "application/pdf",
        filename: "examnet-import.pdf",
      },
      correlationId: "corr_1",
      jobId: "job_1",
      savedAt: new Date("2026-05-14T10:00:00Z"),
    });

    expect(saved.vault_artifact.name).toBe("examnet-import.pdf");
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/exam-converter/artifacts/save",
      expect.objectContaining({
        credentials: "include",
        method: "POST",
      }),
    );
    const init = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    const form = init.body as FormData;
    const metadata = JSON.parse(String(form.get("metadata_json"))) as {
      artifact_key: string;
      saved_display_filename: string;
    };
    expect(headers.get("X-CSRF-Token")).toBe("csrf-token");
    expect(headers.get("Content-Type")).toBeNull();
    expect(metadata.artifact_key).toBe("examnet_pdf");
    expect(metadata.saved_display_filename).toBe("examnet-import.pdf");
    expect(form.get("artifact")).toBeInstanceOf(File);
  });
});
