/**
 * Transcript Gateway request-context construction.
 *
 * Purpose:
 *   Generate deterministic transcript correlation and idempotency headers from
 *   the accepted audio JobSpec and uploaded media bytes.
 *
 * Relationships:
 *   - `transcriptOptions.ts` owns JobSpec construction.
 *   - `client.ts` forwards the prepared headers to HuleEdu Gateway.
 */

import {
  sha256HexFromBlob,
  sha256HexFromText,
  stableJsonStringify,
} from "./requestFingerprint";
import { buildTranscriptJobSpec } from "./transcriptOptions";
import type {
  SirConvertTranscriptRequestContext,
  TranscriptSubmitParams,
} from "./transcriptTypes";

const IDEMPOTENCY_PREFIX = "idem_skriptoteket_";
const CORRELATION_PREFIX = "corr_skriptoteket_";

function buildSourceLabel(params: TranscriptSubmitParams): string {
  if (params.sourceLabel?.trim()) {
    return params.sourceLabel.trim();
  }
  return `${params.file.name}:${params.file.size}:${stableJsonStringify(params.speakerControl)}:${
    params.language ?? "auto"
  }`;
}

export async function prepareTranscriptRequestContext(
  params: TranscriptSubmitParams,
): Promise<SirConvertTranscriptRequestContext> {
  const jobSpec = buildTranscriptJobSpec(params);
  const jobSpecJson = stableJsonStringify(jobSpec);
  const correlationId =
    params.correlationId?.trim() ||
    `${CORRELATION_PREFIX}${(await sha256HexFromText(buildSourceLabel(params))).slice(0, 16)}`;
  const idempotencyDigest = await sha256HexFromText(
    [`job_spec:${jobSpecJson}`, `file:${await sha256HexFromBlob(params.file)}`].join("\n"),
  );

  return {
    correlationId,
    idempotencyKey: `${IDEMPOTENCY_PREFIX}${idempotencyDigest.slice(0, 48)}`,
    jobSpec,
  };
}
