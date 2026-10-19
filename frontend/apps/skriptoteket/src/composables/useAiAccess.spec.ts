import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import type { components } from "../api/openapi";
import { useAuthStore } from "../stores/auth";
import { AI_ADMIN_ONLY_NOTE, useAiAccess } from "./useAiAccess";

type ApiRole = components["schemas"]["Role"];

function seedRole(role: ApiRole): void {
  useAuthStore().user = {
    id: "user-1",
    email: "teacher@example.com",
    role,
    auth_provider: "huleedu",
  };
}

describe("useAiAccess", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("keeps the exact temporary admin-only note", () => {
    expect(AI_ADMIN_ONLY_NOTE).toBe(
      "AI-funktionerna är tillfälligt bara tillgängliga för administratörer.",
    );
  });

  it.each(["user", "contributor"] as const)("blocks AI for role %s", (role) => {
    seedRole(role);
    expect(useAiAccess().canUseAi.value).toBe(false);
  });

  it.each(["admin", "superuser"] as const)("allows AI for role %s", (role) => {
    seedRole(role);
    expect(useAiAccess().canUseAi.value).toBe(true);
  });

  it("blocks AI when no user is signed in", () => {
    expect(useAiAccess().canUseAi.value).toBe(false);
  });

  it("re-evaluates when the signed-in role changes", () => {
    seedRole("user");
    const { canUseAi } = useAiAccess();
    expect(canUseAi.value).toBe(false);

    seedRole("admin");
    expect(canUseAi.value).toBe(true);
  });
});
