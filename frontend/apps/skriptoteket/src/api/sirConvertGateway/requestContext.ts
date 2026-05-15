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

import { DEFAULT_DIGIEXAM_MIGRATION_TARGETS, buildDigiExamMigrationJobSpec } from "./jobSpec";
import type { DigiExamMigrationSubmitParams, SirConvertRequestContext } from "./types";

const IDEMPOTENCY_PREFIX = "idem_skriptoteket_";
const CORRELATION_PREFIX = "corr_skriptoteket_";

export function stableJsonStringify(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableJsonStringify(item)).join(",")}]`;
  }
  const entries = Object.entries(value).sort(([left], [right]) => left.localeCompare(right));
  return `{${entries
    .map(([key, item]) => `${JSON.stringify(key)}:${stableJsonStringify(item)}`)
    .join(",")}}`;
}

async function sha256HexFromBytes(bytes: BufferSource): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function sha256HexFromText(value: string): Promise<string> {
  return await sha256HexFromBytes(new TextEncoder().encode(value));
}

async function blobBytes(blob: Blob): Promise<BufferSource> {
  const readableBlob = blob as Blob & {
    arrayBuffer?: () => Promise<ArrayBuffer>;
    text?: () => Promise<string>;
  };
  if (typeof readableBlob.arrayBuffer === "function") {
    return await readableBlob.arrayBuffer();
  }
  if (typeof readableBlob.text === "function") {
    return new TextEncoder().encode(await readableBlob.text());
  }
  return await new Promise<BufferSource>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (reader.result instanceof ArrayBuffer) {
        resolve(reader.result);
        return;
      }
      resolve(new TextEncoder().encode(String(reader.result ?? "")));
    };
    reader.onerror = () => reject(reader.error ?? new Error("Could not read upload bytes."));
    reader.readAsArrayBuffer(blob);
  });
}

async function sha256HexFromBlob(blob: Blob): Promise<string> {
  return await sha256HexFromBytes(await blobBytes(blob));
}

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
  return digestParts;
}

export async function prepareDigiExamMigrationRequestContext(
  params: DigiExamMigrationSubmitParams,
): Promise<SirConvertRequestContext> {
  const jobSpec = buildDigiExamMigrationJobSpec(params);
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
