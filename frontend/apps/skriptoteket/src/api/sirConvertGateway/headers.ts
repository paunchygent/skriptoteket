/**
 * Sir Convert Gateway request header helpers.
 *
 * Purpose:
 *   Centralize browser-session Gateway headers for authenticated Sir Convert
 *   calls so route-specific clients share CSRF, correlation, and idempotency
 *   behavior.
 *
 * Relationships:
 *   - Used by `client.ts` and transcript replay companion clients.
 *   - Keeps transport modules aligned with HuleEdu Gateway write semantics.
 */

export type CsrfTokenProvider = () => Promise<string | null>;

export function buildJsonHeaders(correlationId: string): Headers {
  const headers = new Headers();
  headers.set("Accept", "application/json");
  headers.set("X-Correlation-ID", correlationId);
  return headers;
}

export async function buildUnsafeHeaders(params: {
  correlationId: string;
  idempotencyKey: string;
  ensureCsrfToken: CsrfTokenProvider;
}): Promise<Headers> {
  const headers = buildJsonHeaders(params.correlationId);
  headers.set("Idempotency-Key", params.idempotencyKey);
  const csrfToken = await params.ensureCsrfToken();
  if (csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  return headers;
}

export async function buildUnsafeJsonHeaders(params: {
  correlationId: string;
  ensureCsrfToken: CsrfTokenProvider;
}): Promise<Headers> {
  const headers = buildJsonHeaders(params.correlationId);
  headers.set("Content-Type", "application/json");
  const csrfToken = await params.ensureCsrfToken();
  if (csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  return headers;
}

export async function buildUnsafeActionHeaders(params: {
  correlationId: string;
  ensureCsrfToken: CsrfTokenProvider;
}): Promise<Headers> {
  const headers = buildJsonHeaders(params.correlationId);
  const csrfToken = await params.ensureCsrfToken();
  if (csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  return headers;
}

export function normalizeWaitSeconds(value: number | undefined): number {
  const waitSeconds = value ?? 0;
  if (!Number.isInteger(waitSeconds) || waitSeconds < 0 || waitSeconds > 20) {
    throw new Error("waitSeconds must be an integer between 0 and 20.");
  }
  return waitSeconds;
}
