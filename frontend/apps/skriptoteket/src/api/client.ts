import { useAuthStore } from "../stores/auth";

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

function isJsonSerializableBody(body: unknown): body is Record<string, unknown> {
  if (body === null) {
    return false;
  }
  if (typeof body !== "object") {
    return false;
  }
  if (body instanceof FormData) {
    return false;
  }
  if (body instanceof Blob) {
    return false;
  }
  if (body instanceof ArrayBuffer) {
    return false;
  }
  return true;
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

  let body: BodyInit | undefined = undefined;
  if (options.body !== undefined) {
    if (options.body instanceof FormData) {
      body = options.body;
    } else if (typeof options.body === "string") {
      body = options.body;
    } else if (options.body instanceof Blob) {
      body = options.body;
    } else if (options.body instanceof ArrayBuffer) {
      body = options.body;
    } else if (isJsonSerializableBody(options.body)) {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(options.body);
    } else {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(options.body);
    }
  }

  if (method !== "GET" && method !== "HEAD") {
    await auth.ensureCsrfToken();
    if (auth.csrfToken) {
      headers.set("X-CSRF-Token", auth.csrfToken);
    }
  }

  const response = await fetch(path, {
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

  throw await toApiError(response);
}

export async function apiGet<T>(path: string): Promise<T> {
  return await apiFetch<T>(path, { method: "GET" });
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return await apiFetch<T>(path, { method: "POST", body });
}

