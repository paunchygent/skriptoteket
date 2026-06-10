/**
 * Sir Convert request-context construction.
 *
 * Purpose:
 *   Generate deterministic correlation and idempotency headers from the
 *   governed DigiExam migration request payload.
 *
 * Relationships:
 *   - `jobSpec.ts` owns JobSpec construction.
 *   - `client.ts` forwards the resulting headers unchanged across the edge.
 */

import {
  DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
} from "./contractValues";
import { DEFAULT_DIGIEXAM_MIGRATION_TARGETS, buildDigiExamMigrationJobSpec } from "./jobSpec";
import {
  sha256HexFromBlob,
  sha256HexFromText,
  stableJsonStringify,
} from "./requestFingerprint";
import type { DigiExamMigrationSubmitParams, SirConvertRequestContext } from "./types";

const IDEMPOTENCY_PREFIX = "idem_skriptoteket_";
const CORRELATION_PREFIX = "corr_skriptoteket_";

export { stableJsonStringify };

function buildSourceLabel(params: DigiExamMigrationSubmitParams): string {
  if (params.sourceLabel?.trim()) {
    return params.sourceLabel.trim();
  }
  const targets = (params.targets ?? DEFAULT_DIGIEXAM_MIGRATION_TARGETS).join(",");
  const graded = params.gradedResultPdf
    ? `${params.gradedResultPdf.name}:${params.gradedResultPdf.size}`
    : "none";
  const parity = params.parityPdf ? `${params.parityPdf.name}:${params.parityPdf.size}` : "none";
  const overlay = params.ingestionOverlay ? stableJsonStringify(params.ingestionOverlay) : "none";
  return `${params.file.name}:${params.file.size}:${targets}:${graded}:${parity}:${overlay}`;
}

async function buildDigestParts(
  params: DigiExamMigrationSubmitParams,
  jobSpecJson: string,
): Promise<string[]> {
  const digestParts = [`job_spec:${jobSpecJson}`, `file:${await sha256HexFromBlob(params.file)}`];
  if (params.gradedResultPdf) {
    digestParts.push(`graded_result_pdf:${await sha256HexFromBlob(params.gradedResultPdf)}`);
  }
  if (params.parityPdf) {
    digestParts.push(`parity_pdf:${await sha256HexFromBlob(params.parityPdf)}`);
  }
  if (params.ingestionOverlay) {
    digestParts.push(`digiexam_ingestion_overlay:${stableJsonStringify(params.ingestionOverlay)}`);
  }
  if (params.advisoryRetryAttempt !== null && params.advisoryRetryAttempt !== undefined) {
    digestParts.push(`advisory_retry_attempt:${params.advisoryRetryAttempt}`);
  }
  return digestParts;
}

function validateAdvisoryRetryAttempt(
  params: DigiExamMigrationSubmitParams,
  jobSpec: SirConvertRequestContext["jobSpec"],
): void {
  if (params.advisoryRetryAttempt === null || params.advisoryRetryAttempt === undefined) {
    return;
  }
  if (!Number.isSafeInteger(params.advisoryRetryAttempt) || params.advisoryRetryAttempt < 1) {
    throw new Error("advisoryRetryAttempt must be a positive integer.");
  }
  if (
    jobSpec.digiexam_migration_options.completion_mode !==
    DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED
  ) {
    throw new Error("advisoryRetryAttempt is only valid for advisory completion submits.");
  }
}

export async function prepareDigiExamMigrationRequestContext(
  params: DigiExamMigrationSubmitParams,
): Promise<SirConvertRequestContext> {
  const jobSpec = buildDigiExamMigrationJobSpec(params);
  validateAdvisoryRetryAttempt(params, jobSpec);
  const sourceLabel = buildSourceLabel(params);
  const jobSpecJson = stableJsonStringify(jobSpec);
  const correlationId =
    params.correlationId?.trim() ||
    `${CORRELATION_PREFIX}${(await sha256HexFromText(sourceLabel)).slice(0, 16)}`;
  const digestParts = await buildDigestParts(params, jobSpecJson);
  const idempotencyDigest = await sha256HexFromText(digestParts.join("\n"));

  return {
    correlationId,
    idempotencyKey: `${IDEMPOTENCY_PREFIX}${idempotencyDigest.slice(0, 48)}`,
    jobSpec,
  };
}
