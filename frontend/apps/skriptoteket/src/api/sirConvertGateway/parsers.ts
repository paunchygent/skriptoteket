/** Shared HTTP error decoding for the remaining Sir Convert transcript client. */

import { SirConvertGatewayError } from "./errors";

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export async function toGatewayError(response: Response): Promise<SirConvertGatewayError> {
  const fallbackMessage = response.statusText || `Sir Convert request failed (${response.status})`;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = await response.json().catch(() => null);
    if (isRecord(payload) && isRecord(payload.error)) {
      return new SirConvertGatewayError({
        code: typeof payload.error.code === "string" ? payload.error.code : "SIR_CONVERT_ERROR",
        correlationId: typeof payload.correlation_id === "string" ? payload.correlation_id : null,
        details: payload.error.details ?? null,
        message: typeof payload.error.message === "string" ? payload.error.message : fallbackMessage,
        status: response.status,
      });
    }
  }
  return new SirConvertGatewayError({ code: "HTTP_ERROR", message: fallbackMessage, status: response.status });
}

export async function readJsonOrThrow<T>(response: Response, parser: (payload: unknown) => T): Promise<T> {
  if (!response.ok) throw await toGatewayError(response);
  try {
    return parser(await response.json());
  } catch (error: unknown) {
    throw new SirConvertGatewayError({
      code: "SIR_CONVERT_CONTRACT_DRIFT",
      message: error instanceof Error ? error.message : "Sir Convert response contract drift.",
      status: response.status,
    });
  }
}
