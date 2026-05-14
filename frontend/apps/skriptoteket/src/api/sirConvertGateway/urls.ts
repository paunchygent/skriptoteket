/**
 * Sir Convert Gateway URL resolution.
 *
 * Purpose:
 *   Keep authenticated browser traffic on the HuleEdu-owned
 *   `/sir-convert/v2/convert` product edge in production and local proxy paths
 *   in development.
 *
 * Relationships:
 *   - `client.ts` uses this boundary for every Sir Convert request.
 *   - `vite.config.ts` proxies the local `/sir-convert` path to HuleEdu Gateway.
 */

export const DEFAULT_SIR_CONVERT_GATEWAY_BASE_URL =
  "https://api.hule.education/sir-convert/v2/convert";
export const DEV_SIR_CONVERT_GATEWAY_BASE_PATH = "/sir-convert/v2/convert";

const REQUIRED_GATEWAY_PATH = "/sir-convert/v2/convert";
const LOCAL_GATEWAY_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);
const EXPLICIT_TEST_GATEWAY_HOSTS = new Set(["api.example.test"]);

function normalizeBaseUrl(value: string): string {
  const trimmed = value.trim();
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

function isTestMode(): boolean {
  return import.meta.env.MODE === "test";
}

function isProductionMode(): boolean {
  return import.meta.env.PROD;
}

function isAllowedAbsoluteGatewayBase(value: string): boolean {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return false;
  }
  if (parsed.pathname !== REQUIRED_GATEWAY_PATH || parsed.search || parsed.hash) {
    return false;
  }
  const hostname = parsed.hostname.toLowerCase();
  if (parsed.protocol === "https:" && hostname === "api.hule.education" && !parsed.port) {
    return true;
  }
  if (isProductionMode()) {
    return false;
  }
  if (parsed.protocol === "http:" && LOCAL_GATEWAY_HOSTS.has(hostname) && parsed.port === "8080") {
    return true;
  }
  return isTestMode() && parsed.protocol === "https:" && EXPLICIT_TEST_GATEWAY_HOSTS.has(hostname);
}

function assertAllowedGatewayBaseUrl(value: string): string {
  const normalized = normalizeBaseUrl(value);
  if (normalized.startsWith("/")) {
    if (!isProductionMode() && normalized === REQUIRED_GATEWAY_PATH) return normalized;
  } else if (isAllowedAbsoluteGatewayBase(normalized)) {
    return normalized;
  }
  throw new Error(
    "Invalid Sir Convert Gateway base URL: expected the HuleEdu Gateway /sir-convert/v2/convert edge.",
  );
}

export function resolveSirConvertGatewayBaseUrl(): string {
  const configured = import.meta.env.VITE_HULEEDU_SIR_CONVERT_BASE_URL?.trim();
  if (configured) {
    return assertAllowedGatewayBaseUrl(configured);
  }
  if (import.meta.env.PROD) {
    return DEFAULT_SIR_CONVERT_GATEWAY_BASE_URL;
  }
  return DEV_SIR_CONVERT_GATEWAY_BASE_PATH;
}

export function toSirConvertGatewayUrl(path: string): string {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${resolveSirConvertGatewayBaseUrl()}${suffix}`;
}
