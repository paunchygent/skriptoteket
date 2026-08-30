/**
 * Sir Convert transcript parser scalar readers.
 *
 * Domain purpose:
 *   Validate primitive JSON fields shared by transcript job, progress,
 *   manifest, and canonical transcript payload parsers.
 *
 * Relationships:
 *   - Used by `transcriptParsers.ts` and `transcriptProgressParsers.ts`.
 *   - Keeps Gateway contract drift errors close to the transcript boundary.
 */

import type { SirConvertJobStatus } from "./transcriptTypes";

export type JsonRecord = Record<string, unknown>;

export function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function hasOwnField(record: JsonRecord, fieldName: string): boolean {
  return Object.prototype.hasOwnProperty.call(record, fieldName);
}

export function readRecord(value: unknown, fieldName: string): JsonRecord {
  if (isRecord(value)) return value;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not an object.`);
}

export function readString(value: unknown, fieldName: string): string {
  if (typeof value === "string" && value.length > 0) return value;
  throw new Error(`Sir Convert transcript field '${fieldName}' is missing.`);
}

export function readNullableString(value: unknown, fieldName: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not a string.`);
}

export function readNumber(value: unknown, fieldName: string): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not a number.`);
}

export function readNullableNumber(value: unknown, fieldName: string): number | null {
  if (value === null || value === undefined) return null;
  return readNumber(value, fieldName);
}

export function readNullableNonNegativeNumber(
  value: unknown,
  fieldName: string,
): number | null {
  const numberValue = readNullableNumber(value, fieldName);
  if (numberValue === null || numberValue >= 0) return numberValue;
  throw new Error(`Sir Convert transcript field '${fieldName}' is negative.`);
}

export function readNullablePercent(value: unknown, fieldName: string): number | null {
  const numberValue = readNullableNonNegativeNumber(value, fieldName);
  if (numberValue === null || numberValue <= 100) return numberValue;
  throw new Error(`Sir Convert transcript field '${fieldName}' is outside 0..100.`);
}

export function readNullableNonNegativeInteger(
  value: unknown,
  fieldName: string,
): number | null {
  const numberValue = readNullableNonNegativeNumber(value, fieldName);
  if (numberValue === null || Number.isInteger(numberValue)) return numberValue;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not an integer.`);
}

export function readNullableDateTime(value: unknown, fieldName: string): string | null {
  const stringValue = readNullableString(value, fieldName);
  if (stringValue === null) return null;
  if (stringValue.length > 0 && Number.isFinite(Date.parse(stringValue))) return stringValue;
  throw new Error(`Sir Convert transcript field '${fieldName}' is not a datetime.`);
}

export function readStatus(value: unknown): SirConvertJobStatus {
  const status = readString(value, "status");
  if (
    status === "submitted" ||
    status === "queued" ||
    status === "running" ||
    status === "processing" ||
    status === "succeeded" ||
    status === "failed" ||
    status === "canceled" ||
    status === "cancelled"
  ) {
    return status;
  }
  throw new Error(`Unknown Sir Convert transcript status '${status}'.`);
}
