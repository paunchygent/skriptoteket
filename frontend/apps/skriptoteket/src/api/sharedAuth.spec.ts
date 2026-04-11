import { afterEach, describe, expect, it, vi } from "vitest";

import {
  mapBrowserSessionToAuthSnapshot,
  sharedAuthUrl,
  SHARED_AUTH_CSRF_PATH,
  SHARED_AUTH_SESSION_PATH,
  type BrowserSessionResponse,
} from "./sharedAuth";

function sessionPayload(
  overrides: Partial<BrowserSessionResponse> = {},
): BrowserSessionResponse {
  return {
    authenticated: true,
    user: {
      user_id: "550e8400-e29b-41d4-a716-446655440000",
      email: "teacher@example.com",
      email_verified: true,
    },
    profile: {
      display_name: "Teacher Example",
      locale: "sv-SE",
      person_name: {
        given_name: "Teacher",
        family_name: "Example",
      },
    },
    policy: {
      roles: ["user", "admin"],
      grants: ["tools:run", "tools:run"],
      feature_flags: ["inline-completion"],
    },
    session: {
      transport: "cookie",
      csrf_required: true,
      expires_at: "2026-04-11T12:00:00Z",
    },
    app_flags: {
      shared_browser_session_authority: true,
    },
    ...overrides,
  };
}

describe("sharedAuthUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("targets the public HuleEdu auth edge by default", () => {
    expect(sharedAuthUrl(SHARED_AUTH_SESSION_PATH)).toBe(
      "https://api.hule.education/v1/auth/session",
    );
  });

  it("normalizes an explicit auth base URL", () => {
    vi.stubEnv("VITE_HULEEDU_AUTH_BASE_URL", "http://127.0.0.1:9000/");

    expect(sharedAuthUrl(SHARED_AUTH_CSRF_PATH)).toBe("http://127.0.0.1:9000/v1/auth/csrf");
  });
});

describe("mapBrowserSessionToAuthSnapshot", () => {
  it("maps the HuleEdu shared session into provider metadata without local RBAC", () => {
    const snapshot = mapBrowserSessionToAuthSnapshot(sessionPayload());

    expect(snapshot.user).toEqual(
      expect.objectContaining({
        id: "550e8400-e29b-41d4-a716-446655440000",
        email: "teacher@example.com",
        role: "user",
        auth_provider: "huleedu",
        external_id: "550e8400-e29b-41d4-a716-446655440000",
        email_verified: true,
      }),
    );
    expect(snapshot.profile).toEqual(
      expect.objectContaining({
        user_id: "550e8400-e29b-41d4-a716-446655440000",
        display_name: "Teacher Example",
        first_name: "Teacher",
        last_name: "Example",
        locale: "sv-SE",
      }),
    );
    expect(snapshot.grants).toEqual(["tools:run"]);
    expect(snapshot.featureFlags).toEqual(["inline-completion"]);
    expect(snapshot.aiPolicy).toBeNull();
  });

  it("keeps an authenticated HuleEdu user at the safest local role when no local role matches", () => {
    const snapshot = mapBrowserSessionToAuthSnapshot(
      sessionPayload({
        policy: {
          roles: ["teacher"],
          grants: [],
          feature_flags: [],
        },
      }),
    );

    expect(snapshot.user?.role).toBe("user");
  });

  it("returns an empty local snapshot for anonymous sessions", () => {
    const snapshot = mapBrowserSessionToAuthSnapshot(
      sessionPayload({
        authenticated: false,
        user: null,
        profile: null,
      }),
    );

    expect(snapshot.user).toBeNull();
    expect(snapshot.profile).toBeNull();
    expect(snapshot.grants).toEqual([]);
    expect(snapshot.featureFlags).toEqual([]);
  });
});
