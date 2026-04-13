/**
 * Shared auth store spec fixtures.
 *
 * Purpose:
 *   Provide typed user/profile factories and Response helpers for focused auth
 *   store specs without duplicating OpenAPI-shaped payload setup.
 *
 * Relationships:
 *   - Used by `auth.spec.ts`, `auth.csrf.spec.ts`, and `auth.logout.spec.ts`.
 *   - Mirrors the generated Skriptoteket OpenAPI types consumed by `auth.ts`.
 */

import type { components } from "../api/openapi";

type ApiUser = components["schemas"]["User"];
type ApiUserProfile = components["schemas"]["UserProfile"];

export function createTestUser(overrides: Partial<ApiUser> = {}): ApiUser {
  return {
    id: "550e8400-e29b-41d4-a716-446655440000",
    email: "test@test.com",
    role: "user",
    auth_provider: "local",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    email_verified: true,
    failed_login_attempts: 0,
    is_active: true,
    ...overrides,
  };
}

export function createTestProfile(
  overrides: Partial<ApiUserProfile> = {},
): ApiUserProfile {
  return {
    user_id: "550e8400-e29b-41d4-a716-446655440000",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    locale: "sv-SE",
    display_name: null,
    first_name: null,
    last_name: null,
    ...overrides,
  };
}

export const TEST_AI_POLICY = {
  remote_providers_enabled: true,
  completion_external_available: true,
  completion_local_available: true,
};

export function mockJsonResponse(
  payload: unknown,
  status = 200,
  statusText?: string,
): Response {
  return new Response(JSON.stringify(payload), {
    status,
    statusText,
    headers: { "content-type": "application/json" },
  });
}

export function mockEmptyResponse(status: number, statusText?: string): Response {
  return new Response(null, { status, statusText });
}
