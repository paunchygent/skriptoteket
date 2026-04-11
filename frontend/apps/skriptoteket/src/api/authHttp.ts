/**
 * Shared auth HTTP helpers.
 *
 * Purpose:
 *   Keep timeout handling and backend error parsing out of Pinia store modules.
 *
 * Relationships:
 *   - Used by `stores/auth.ts` for legacy local auth actions.
 *   - Used by `stores/authBootstrap.ts` for HuleEdu shared-session bootstrap.
 */

import { ApiError } from "./client";

type FetchTimeoutOptions = {
  timeoutMs?: number;
  timeoutMessage?: string;
};

export async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit,
  options: FetchTimeoutOptions = {},
): Promise<Response> {
  const timeoutMs = options.timeoutMs ?? 15000;
  const timeoutMessage = options.timeoutMessage ?? "Request timed out";

  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error: unknown) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(timeoutMessage);
    }
    throw error;
  } finally {
    globalThis.clearTimeout(timeoutId);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export async function readAuthError(response: Response): Promise<Error> {
  const contentType = response.headers.get("content-type") ?? "";
  const fallbackMessage = response.statusText || `Request failed (${response.status})`;

  if (contentType.includes("application/json")) {
    const payload: unknown = await response.json().catch(() => null);

    if (isRecord(payload)) {
      const error = payload.error;
      if (isRecord(error) && typeof error.code === "string" && typeof error.message === "string") {
        return new ApiError({
          code: error.code,
          message: error.message,
          details: error.details ?? null,
          correlationId:
            typeof payload.correlation_id === "string" ? payload.correlation_id : null,
          status: response.status,
        });
      }

      if ("detail" in payload && payload.detail) {
        return new ApiError({
          code: "VALIDATION_ERROR",
          message: "Validation error",
          details: payload.detail,
          correlationId: null,
          status: response.status,
        });
      }
    }
  }

  return new Error(fallbackMessage);
}

export async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return response.statusText || `Request failed (${response.status})`;
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!isRecord(payload)) {
    return response.statusText || `Request failed (${response.status})`;
  }

  const error = payload.error;
  if (isRecord(error) && typeof error.message === "string") {
    return error.message;
  }

  if ("detail" in payload && payload.detail) {
    return "Validation error";
  }

  return response.statusText || `Request failed (${response.status})`;
}
