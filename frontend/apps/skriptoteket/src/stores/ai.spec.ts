import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAiStore } from "./ai";
import { useAuthStore } from "./auth";

describe("useAiStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
  });

  it("fails closed for remote providers while app-local AI policy is missing", () => {
    const auth = useAuthStore();
    auth.profile = {
      user_id: "550e8400-e29b-41d4-a716-446655440000",
      locale: "sv-SE",
      allow_remote_fallback: true,
      inline_completion_provider: "external",
    };

    const ai = useAiStore();

    expect(ai.remoteProvidersEnabled).toBe(false);
    expect(ai.completionExternalAvailable).toBe(false);
    expect(ai.allowRemoteFallback).toBe(true);
    expect(ai.allowRemoteProviders).toBe(false);
    expect(ai.inlineCompletionProviderPreference).toBe("external");
  });

  it("allows remote providers only when policy and user preference both allow them", () => {
    const auth = useAuthStore();
    auth.aiPolicy = {
      remote_providers_enabled: true,
      completion_external_available: true,
      completion_local_available: true,
    };
    auth.profile = {
      user_id: "550e8400-e29b-41d4-a716-446655440000",
      locale: "sv-SE",
      allow_remote_fallback: true,
      inline_completion_provider: "external",
    };

    const ai = useAiStore();

    expect(ai.remoteProvidersEnabled).toBe(true);
    expect(ai.completionExternalAvailable).toBe(true);
    expect(ai.completionLocalAvailable).toBe(true);
    expect(ai.remoteFallbackPreference).toBe("allow");
    expect(ai.allowRemoteProviders).toBe(true);
  });
});
