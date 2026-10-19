/**
 * Exam workspace AI mode.
 *
 * Expected behavior:
 *   A store whose teacher half is null reads "guest" for every role. A
 *   signed-in store reads "allowed" for role "admin" or "superuser" and
 *   "admin_only" for role "user" or "contributor".
 */

import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { defineComponent, h } from "vue";
import { beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import { useAuthStore } from "../../../stores/auth";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { useExamWorkspaceAiMode } from "./useExamWorkspaceAiMode";

type Role = "user" | "contributor" | "admin" | "superuser";

const Probe = defineComponent({
  setup() {
    const mode = useExamWorkspaceAiMode();
    return () => h("span", { "data-test": "ai-mode" }, mode.value);
  },
});

function readMode(pinia: Pinia, store: ExamWorkspaceStore, role: Role): string {
  setActivePinia(pinia);
  useAuthStore().user = { id: "u1", email: "u@example.test", role, auth_provider: "local" };
  const wrapper = mount(Probe, {
    global: {
      plugins: [pinia, examWorkspaceProvidersPlugin({ store })],
    },
  });
  const mode = wrapper.get('[data-test="ai-mode"]').text();
  wrapper.unmount();
  return mode;
}

const GUEST_STORE: ExamWorkspaceStore = { ...serverExamWorkspaceStore, teacher: null };

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
});

describe("useExamWorkspaceAiMode", () => {
  it.each(["user", "contributor", "admin", "superuser"] as const)(
    "reads guest for a teacher-null store with role %s",
    (role) => {
      expect(readMode(pinia, GUEST_STORE, role)).toBe("guest");
    },
  );

  it.each(["user", "contributor"] as const)(
    "reads admin_only for the server store with role %s",
    (role) => {
      expect(readMode(pinia, serverExamWorkspaceStore, role)).toBe("admin_only");
    },
  );

  it.each(["admin", "superuser"] as const)(
    "reads allowed for the server store with role %s",
    (role) => {
      expect(readMode(pinia, serverExamWorkspaceStore, role)).toBe("allowed");
    },
  );
});
