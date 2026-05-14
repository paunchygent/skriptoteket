/**
 * Skriptoteket protected API client.
 *
 * Purpose:
 *   Centralize browser calls to Skriptoteket app APIs, including the
 *   production HuleEdu Gateway protected API base and app-hosted public API
 *   exceptions.
 *
 * Relationships:
 *   - `stores/auth.ts` provides CSRF/session state for protected calls.
 *   - `api/sharedAuth.ts` owns HuleEdu session/csrf/logout endpoints.
 *   - Public `/api/v1/public/...` app APIs remain app-hosted.
 */

import { useAuthStore } from "../stores/auth";
import { resolveProtectedApiUrl } from "./protectedApiBase";
export {
  DEFAULT_PROTECTED_API_BASE_URL,
  resolveProtectedApiUrl,
} from "./protectedApiBase";

export type ApiErrorEnvelope = {
  error: { code: string; message: string; details?: unknown };
  correlation_id?: string | null;
};

type FastApiValidationError = {
  detail?: unknown;
};

export class ApiError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly details: unknown;
  public readonly correlationId: string | null;

  public constructor(params: {
    code: string;
    message: string;
    status: number;
    details?: unknown;
    correlationId?: string | null;
  }) {
    super(params.message);
    this.name = "ApiError";
    this.code = params.code;
    this.status = params.status;
    this.details = params.details ?? null;
    this.correlationId = params.correlationId ?? null;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

type ApiRequestOptions = Omit<RequestInit, "body" | "headers" | "credentials" | "method"> & {
  method?: string;
  body?: unknown;
  headers?: HeadersInit;
};

export type ApiBlobResponse = {
  blob: Blob;
  contentType: string | null;
  filename: string | null;
};

function buildApiRequestBody(body: unknown, headers: Headers): BodyInit | undefined {
  if (body === undefined) {
    return undefined;
  }
  if (
    body instanceof FormData ||
    typeof body === "string" ||
    body instanceof Blob ||
    body instanceof ArrayBuffer
  ) {
    return body;
  }
  headers.set("Content-Type", "application/json");
  return JSON.stringify(body);
}

async function toApiError(response: Response): Promise<ApiError> {
  const contentType = response.headers.get("content-type") ?? "";
  const fallbackMessage = response.statusText || `Request failed (${response.status})`;

  if (contentType.includes("application/json")) {
    const payload = (await response.json().catch(() => null)) as
      | ApiErrorEnvelope
      | FastApiValidationError
      | null;

    if (payload && typeof payload === "object") {
      if ("error" in payload && payload.error) {
        return new ApiError({
          code: payload.error.code,
          message: payload.error.message,
          details: payload.error.details ?? null,
          correlationId: payload.correlation_id ?? null,
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

  return new ApiError({
    code: "HTTP_ERROR",
    message: fallbackMessage,
    details: null,
    correlationId: null,
    status: response.status,
  });
}

export async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const auth = useAuthStore();

  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  const body = buildApiRequestBody(options.body, headers);

  if (method !== "GET" && method !== "HEAD") {
    await auth.ensureCsrfToken();
    if (auth.csrfToken) {
      headers.set("X-CSRF-Token", auth.csrfToken);
    }
  }

  const response = await fetch(resolveProtectedApiUrl(path), {
    ...options,
    method,
    headers,
    body,
    credentials: "include",
  });

  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }

    const contentType = response.headers.get("content-type") ?? "";
    if (!contentType.includes("application/json")) {
      return (await response.text()) as unknown as T;
    }

    return (await response.json()) as T;
  }

  if (response.status === 401) {
    auth.clear();
  }

  throw await toApiError(response);
}

export async function apiGet<T>(path: string): Promise<T> {
  return await apiFetch<T>(path, { method: "GET" });
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return await apiFetch<T>(path, { method: "POST", body });
}

export async function publicApiFetch<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  const body = buildApiRequestBody(options.body, headers);

  const response = await fetch(path, {
    ...options,
    method,
    headers,
    body,
    credentials: "omit",
  });

  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }

    const contentType = response.headers.get("content-type") ?? "";
    if (!contentType.includes("application/json")) {
      return (await response.text()) as unknown as T;
    }

    return (await response.json()) as T;
  }

  throw await toApiError(response);
}

export async function publicApiGet<T>(path: string): Promise<T> {
  return await publicApiFetch<T>(path, { method: "GET" });
}

export async function publicApiPost<T>(path: string, body?: unknown): Promise<T> {
  return await publicApiFetch<T>(path, { method: "POST", body });
}

export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  return await apiFetch<T>(path, { method: "PATCH", body });
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return await apiFetch<T>(path, { method: "PUT", body });
}

export async function apiDelete<T>(path: string): Promise<T> {
  return await apiFetch<T>(path, { method: "DELETE" });
}

export async function apiFetchBlob(path: string, options: ApiRequestOptions = {}): Promise<Blob> {
  const auth = useAuthStore();

  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "*/*");
  }
  const body = buildApiRequestBody(options.body, headers);

  if (method !== "GET" && method !== "HEAD") {
    await auth.ensureCsrfToken();
    if (auth.csrfToken) {
      headers.set("X-CSRF-Token", auth.csrfToken);
    }
  }

  const response = await fetch(resolveProtectedApiUrl(path), {
    ...options,
    method,
    headers,
    body,
    credentials: "include",
  });

  if (response.ok) {
    return await response.blob();
  }

  if (response.status === 401) {
    auth.clear();
  }

  throw await toApiError(response);
}

function parseContentDispositionFilename(headerValue: string | null): string | null {
  if (!headerValue) {
    return null;
  }

  const utf8Match = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }

  const quotedMatch = headerValue.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  const plainMatch = headerValue.match(/filename=([^;]+)/i);
  return plainMatch?.[1]?.trim() ?? null;
}

export async function apiFetchBlobResponse(
  path: string,
  options: ApiRequestOptions = {},
): Promise<ApiBlobResponse> {
  const auth = useAuthStore();

  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "*/*");
  }
  const body = buildApiRequestBody(options.body, headers);

  if (method !== "GET" && method !== "HEAD") {
    await auth.ensureCsrfToken();
    if (auth.csrfToken) {
      headers.set("X-CSRF-Token", auth.csrfToken);
    }
  }

  const response = await fetch(resolveProtectedApiUrl(path), {
    ...options,
    method,
    headers,
    body,
    credentials: "include",
  });

  if (response.ok) {
    return {
      blob: await response.blob(),
      contentType: response.headers.get("content-type"),
      filename: parseContentDispositionFilename(
        response.headers.get("content-disposition"),
      ),
    };
  }

  if (response.status === 401) {
    auth.clear();
  }

  throw await toApiError(response);
}

export async function publicApiFetchBlobResponse(
  path: string,
  options: ApiRequestOptions = {},
): Promise<ApiBlobResponse> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "*/*");
  }
  const body = buildApiRequestBody(options.body, headers);

  const response = await fetch(path, {
    ...options,
    method,
    headers,
    body,
    credentials: "omit",
  });

  if (response.ok) {
    return {
      blob: await response.blob(),
      contentType: response.headers.get("content-type"),
      filename: parseContentDispositionFilename(
        response.headers.get("content-disposition"),
      ),
    };
  }

  throw await toApiError(response);
}
