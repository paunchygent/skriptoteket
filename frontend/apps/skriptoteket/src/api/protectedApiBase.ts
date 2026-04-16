/**
 * Protected Skriptoteket API base resolution.
 *
 * Purpose:
 *   Resolve browser-facing Skriptoteket protected API paths to the HuleEdu
 *   Gateway production edge while preserving local development and public app
 *   host exceptions.
 *
 * Relationships:
 *   - `api/client.ts` uses this for typed JSON and blob helpers.
 *   - `stores/authBootstrap.ts` uses this for app-continuation bootstrap.
 *   - Public `/api/v1/public/...` routes remain app-hosted.
 */

export const DEFAULT_PROTECTED_API_BASE_URL = "https://api.hule.education/api";
const APP_API_PREFIX = "/api/";
const PUBLIC_APP_API_PREFIX = "/api/v1/public/";

function isProtectedAppApiPath(path: string): boolean {
  return path.startsWith(APP_API_PREFIX) && !path.startsWith(PUBLIC_APP_API_PREFIX);
}

function normalizeBaseUrl(value: string): string {
  const trimmed = value.trim();
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

function configuredProtectedApiBaseUrl(): string | null {
  const configured = import.meta.env.VITE_HULEEDU_PROTECTED_API_BASE_URL?.trim();
  if (configured) {
    return normalizeBaseUrl(configured);
  }
  if (import.meta.env.PROD) {
    return DEFAULT_PROTECTED_API_BASE_URL;
  }
  return null;
}

export function resolveProtectedApiUrl(path: string): string {
  if (!isProtectedAppApiPath(path)) {
    return path;
  }

  const baseUrl = configuredProtectedApiBaseUrl();
  if (!baseUrl) {
    return path;
  }

  const suffix = baseUrl.endsWith("/api") ? path.slice("/api".length) : path;
  return `${baseUrl}${suffix}`;
}
