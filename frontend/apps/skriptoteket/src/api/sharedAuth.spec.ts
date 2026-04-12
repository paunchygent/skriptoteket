import { afterEach, describe, expect, it, vi } from "vitest";

import {
  mapBrowserSessionToAuthSnapshot,
  sharedAuthCeremonyUrl,
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

describe("sharedAuthCeremonyUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses a browser-navigable ceremony URL by default", () => {
    const url = sharedAuthCeremonyUrl({
      nextPath: "/editor",
      origin: "https://skriptoteket.hule.education",
    });

    expect(url).toBe(
      "https://api.hule.education/auth/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=https%3A%2F%2Fskriptoteket.hule.education%2Fauth%2Fcallback&next=%2Feditor",
    );
    expect(url).not.toContain("/v1/auth/login");
  });

  it("uses a callback return URL and keeps next as a same-origin path", () => {
    const url = new URL(
      sharedAuthCeremonyUrl({
        nextPath: "/tools?filter=mine",
        origin: "http://127.0.0.1:5173",
      }),
    );

    expect(url.searchParams.get("return_to")).toBe("http://127.0.0.1:5173/auth/callback");
    expect(url.searchParams.get("next")).toBe("/tools?filter=mine");
    expect(url.searchParams.get("product_identity_realm")).toBe("skriptoteket_standalone");
  });

  it("lets deployments provide the browser ceremony URL separately from the API base", () => {
    vi.stubEnv("VITE_HULEEDU_AUTH_BASE_URL", "https://api.example.test/");
    vi.stubEnv("VITE_HULEEDU_AUTH_ENTRY_URL", "https://identity.example.test/login");

    const url = sharedAuthCeremonyUrl({
      nextPath: "/admin/tools",
      origin: "https://skriptoteket.hule.education",
    });

    expect(sharedAuthUrl(SHARED_AUTH_SESSION_PATH)).toBe(
      "https://api.example.test/v1/auth/session",
    );
    expect(url).toBe(
      "https://identity.example.test/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=https%3A%2F%2Fskriptoteket.hule.education%2Fauth%2Fcallback&next=%2Fadmin%2Ftools",
    );
  });

  it("preserves an explicitly configured realm while refreshing return and next", () => {
    vi.stubEnv(
      "VITE_HULEEDU_AUTH_ENTRY_URL",
      "https://identity.example.test/login?app=skriptoteket&product_identity_realm=huleedu_school&next=/stale",
    );

    const url = new URL(
      sharedAuthCeremonyUrl({
        nextPath: "/editor",
        origin: "https://skriptoteket.hule.education",
      }),
    );

    expect(url.searchParams.get("product_identity_realm")).toBe("huleedu_school");
    expect(url.searchParams.get("return_to")).toBe(
      "https://skriptoteket.hule.education/auth/callback",
    );
    expect(url.searchParams.get("next")).toBe("/editor");
  });

  it("drops hostile or looping next values at the ceremony helper boundary", () => {
    const hostileValues = [
      "https://evil.example/tools",
      "//evil.example/tools",
      "/auth/login",
      "/auth/callback",
      "/login",
    ];

    for (const nextPath of hostileValues) {
      const url = new URL(
        sharedAuthCeremonyUrl({
          nextPath,
          origin: "https://skriptoteket.hule.education",
        }),
      );

      expect(url.searchParams.has("next")).toBe(false);
    }
  });

  it("normalizes safe next values at the ceremony helper boundary", () => {
    const url = new URL(
      sharedAuthCeremonyUrl({
        nextPath: "/editor?draft=head#debug",
        origin: "https://skriptoteket.hule.education",
      }),
    );

    expect(url.searchParams.get("next")).toBe("/editor?draft=head#debug");
  });

  it("builds the HuleEdu standalone registration ceremony URL", () => {
    const url = sharedAuthCeremonyUrl({
      kind: "register",
      nextPath: "/apps/classroom.group-seating-studio",
      origin: "https://skriptoteket.hule.education",
    });

    expect(url).toBe(
      "https://api.hule.education/auth/register?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=https%3A%2F%2Fskriptoteket.hule.education%2Fauth%2Fcallback&next=%2Fapps%2Fclassroom.group-seating-studio",
    );
    expect(url).not.toContain("/v1/auth/register");
  });

  it("keeps lifecycle ceremonies on the configured HuleEdu Gateway origin", () => {
    vi.stubEnv("VITE_HULEEDU_AUTH_ENTRY_URL", "http://127.0.0.1:9000/auth/login");

    const url = new URL(
      sharedAuthCeremonyUrl({
        kind: "password-reset",
        nextPath: "/profile",
        origin: "http://127.0.0.1:5173",
        token: "reset-token-123",
      }),
    );

    expect(`${url.origin}${url.pathname}`).toBe("http://127.0.0.1:9000/auth/password-reset");
    expect(url.searchParams.get("app")).toBe("skriptoteket");
    expect(url.searchParams.get("product_identity_realm")).toBe("skriptoteket_standalone");
    expect(url.searchParams.get("return_to")).toBe("http://127.0.0.1:5173/auth/callback");
    expect(url.searchParams.get("next")).toBe("/profile");
    expect(url.searchParams.get("token")).toBe("reset-token-123");
  });

  it("builds email verification handoffs with token continuation and safe next", () => {
    const url = new URL(
      sharedAuthCeremonyUrl({
        kind: "email-verification",
        nextPath: "https://evil.example/callback",
        origin: "https://skriptoteket.hule.education",
        token: " verify-token ",
      }),
    );

    expect(`${url.origin}${url.pathname}`).toBe(
      "https://api.hule.education/auth/email-verification",
    );
    expect(url.searchParams.get("token")).toBe("verify-token");
    expect(url.searchParams.has("next")).toBe(false);
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
