import { describe, expect, it } from "vitest";

import { SirConvertGatewayError } from "./errors";
import { buildDigiExamMigrationJobSpec } from "./jobSpec";
import { prepareDigiExamMigrationRequestContext, stableJsonStringify } from "./requestContext";
import {
  DIGIEXAM_COMPLETION_MODE_APPLY_REVIEWED_MISSING_MACHINE_MARKED,
  DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
} from "./contractValues";

function dxeFile(content = "exam"): File {
  return new File([content], "exam.dxe", { type: "application/octet-stream" });
}

describe("Sir Convert DigiExam request context", () => {
  it("builds the governed DigiExam migration JobSpec only", () => {
    const gradedResultPdf = new File(["answers"], "graded-result.pdf", {
      type: "application/pdf",
    });
    const jobSpec = buildDigiExamMigrationJobSpec({
      file: dxeFile(),
      gradedResultPdf,
      targets: ["examnet_pdf"],
      artifactLanguage: "sv-SE",
    });

    expect(jobSpec).toEqual({
      api_version: "v2",
      source: {
        kind: "upload",
        filename: "exam.dxe",
        format: "digiexam_dxe",
      },
      conversion: {
        output_format: "examnet_migration_bundle",
        targets: ["examnet_pdf"],
        artifact_language: "sv-SE",
        reference_docx_filename: null,
      },
      digiexam_migration_options: {
        completion_mode: "local_llm_suggest_missing_machine_marked",
        graded_result_pdf_filename: "graded-result.pdf",
        remote_provider_policy: "forbidden",
        result_pdf_usage: "correct_machine_marked_answers_only",
        manual_follow_up_policy: "emit_item_addressable_report",
      },
      retention: { pin: false },
    });
  });

  it("generates deterministic idempotency and fallback correlation headers", async () => {
    const params = {
      file: dxeFile("same payload"),
      gradedResultPdf: new File(["same result"], "graded-result.pdf", {
        type: "application/pdf",
      }),
    };

    const first = await prepareDigiExamMigrationRequestContext(params);
    const second = await prepareDigiExamMigrationRequestContext({
      file: dxeFile("same payload"),
      gradedResultPdf: new File(["same result"], "graded-result.pdf", {
        type: "application/pdf",
      }),
    });

    expect(second.idempotencyKey).toBe(first.idempotencyKey);
    expect(second.correlationId).toBe(first.correlationId);
    expect(first.idempotencyKey).toMatch(/^idem_skriptoteket_[0-9a-f]{48}$/);
    expect(first.correlationId).toMatch(/^corr_skriptoteket_[0-9a-f]{16}$/);
  });

  it("changes idempotency when companion evidence changes", async () => {
    const first = await prepareDigiExamMigrationRequestContext({
      file: dxeFile("same payload"),
      gradedResultPdf: new File(["answer A"], "graded-result.pdf", {
        type: "application/pdf",
      }),
    });
    const second = await prepareDigiExamMigrationRequestContext({
      file: dxeFile("same payload"),
      gradedResultPdf: new File(["answer B"], "graded-result.pdf", {
        type: "application/pdf",
      }),
    });

    expect(second.idempotencyKey).not.toBe(first.idempotencyKey);
  });

  it("preserves caller-provided correlation IDs", async () => {
    const context = await prepareDigiExamMigrationRequestContext({
      file: dxeFile(),
      correlationId: "corr_teacher_action_001",
    });

    expect(context.correlationId).toBe("corr_teacher_action_001");
  });

  it("scopes advisory retry attempts to deterministic idempotency only", async () => {
    const file = dxeFile("same payload");
    const firstSubmit = await prepareDigiExamMigrationRequestContext({
      completionMode: DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
      file,
    });
    const firstRetry = await prepareDigiExamMigrationRequestContext({
      advisoryRetryAttempt: 1,
      completionMode: DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
      file: dxeFile("same payload"),
    });
    const duplicateFirstRetry = await prepareDigiExamMigrationRequestContext({
      advisoryRetryAttempt: 1,
      completionMode: DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
      file: dxeFile("same payload"),
    });
    const secondRetry = await prepareDigiExamMigrationRequestContext({
      advisoryRetryAttempt: 2,
      completionMode: DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
      file: dxeFile("same payload"),
    });

    expect(firstRetry.idempotencyKey).not.toBe(firstSubmit.idempotencyKey);
    expect(duplicateFirstRetry.idempotencyKey).toBe(firstRetry.idempotencyKey);
    expect(secondRetry.idempotencyKey).not.toBe(firstRetry.idempotencyKey);
    expect(firstRetry.correlationId).toBe(firstSubmit.correlationId);
    expect(firstRetry.jobSpec).toEqual(firstSubmit.jobSpec);
    expect(stableJsonStringify(firstRetry.jobSpec)).not.toContain("advisoryRetryAttempt");
  });

  it("rejects invalid or non-advisory retry attempts", async () => {
    await expect(
      prepareDigiExamMigrationRequestContext({
        advisoryRetryAttempt: 0,
        file: dxeFile(),
      }),
    ).rejects.toThrow("advisoryRetryAttempt must be a positive integer.");
    await expect(
      prepareDigiExamMigrationRequestContext({
        advisoryRetryAttempt: 1,
        completionMode: DIGIEXAM_COMPLETION_MODE_APPLY_REVIEWED_MISSING_MACHINE_MARKED,
        file: dxeFile(),
      }),
    ).rejects.toThrow("advisoryRetryAttempt is only valid for advisory completion submits.");
  });

  it("serializes JobSpec keys stably for hashing and multipart submission", () => {
    expect(stableJsonStringify({ b: 2, a: { d: 4, c: 3 } })).toBe(
      '{"a":{"c":3,"d":4},"b":2}',
    );
  });

  it("rejects non-DigiExam source files before transport", () => {
    expect(() =>
      buildDigiExamMigrationJobSpec({
        file: new File(["pdf"], "exam.pdf", { type: "application/pdf" }),
      }),
    ).toThrow(SirConvertGatewayError);
  });
});
