/**
 * The export blockers' answer-key fixes run for every signed-in user.
 *
 * Expected behavior:
 *   With role "user" or "contributor" the "Föreslå facit för alla" and the
 *   per-question "Föreslå facit" buttons are enabled, carry no admin-only
 *   note (inline or in the title), and clicking them emits. The other fixes
 *   (Godkänn, Markera som granskad, …) stay available as before.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useAuthStore } from "../../../stores/auth";
import ExamWorkspaceExportBlockers from "./ExamWorkspaceExportBlockers.vue";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

/** Distinctive fragment of the removed admin-only note; the full note must not render. */
const REMOVED_ADMIN_NOTE = "bara tillgängliga för administratörer";

type Role = "user" | "contributor";

function keyBlocker(itemId: string, label: string): ExamWorkspaceBlockerEntry {
  return {
    fix: "suggest_key",
    focus: null,
    itemId,
    label,
    problem: "facit saknas",
    reason: "missing_answer_key",
  };
}

function signIn(pinia: Pinia, role: Role): void {
  setActivePinia(pinia);
  useAuthStore().user = { id: "u1", email: "u@example.test", role, auth_provider: "local" };
}

function mountBlockers(pinia: Pinia, blockers: ExamWorkspaceBlockerEntry[]) {
  return mount(ExamWorkspaceExportBlockers, {
    props: { blockers, fixDisabled: false, suggestBusy: false, testId: "exam-workspace-blockers" },
    global: {
      plugins: [pinia, examWorkspaceProvidersPlugin()],
    },
  });
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
});

const TWO_KEYLESS = [keyBlocker("item_001", "1"), keyBlocker("item_002", "2")];

describe("ExamWorkspaceExportBlockers non-admin AI", () => {
  it.each(["user", "contributor"] as const)(
    "leaves both key buttons working without the admin-only note for role %s",
    async (role) => {
      signIn(pinia, role);
      const wrapper = mountBlockers(pinia, TWO_KEYLESS);

      expect(wrapper.text()).not.toContain(REMOVED_ADMIN_NOTE);

      const all = wrapper.get('[data-test="exam-workspace-blocker-suggest-all"]');
      expect(all.attributes("disabled")).toBeUndefined();
      expect(all.attributes("title")).toBeUndefined();
      await all.trigger("click");
      expect(wrapper.emitted("suggestAll")).toHaveLength(1);

      const fix = wrapper.get('[data-test="exam-workspace-blocker-fix-item_001"]');
      expect(fix.attributes("disabled")).toBeUndefined();
      expect(fix.attributes("title")).toBeUndefined();
      await fix.trigger("click");
      expect(wrapper.emitted("fix")).toHaveLength(1);
      wrapper.unmount();
    },
  );

  it("keeps a non-AI fix available for a non-admin", async () => {
    signIn(pinia, "user");
    const wrapper = mountBlockers(pinia, [
      { fix: "review", focus: null, itemId: "item_001", label: "1", problem: "kunde inte konverteras", reason: "unbuilt_question" },
    ]);

    const fix = wrapper.get('[data-test="exam-workspace-blocker-fix-item_001"]');
    expect(fix.attributes("disabled")).toBeUndefined();
    expect(fix.attributes("title")).toBeUndefined();
    await fix.trigger("click");
    expect(wrapper.emitted("fix")).toHaveLength(1);
    wrapper.unmount();
  });

  it("shows the batch button alongside one key fix for a non-admin", () => {
    signIn(pinia, "user");
    const wrapper = mountBlockers(pinia, TWO_KEYLESS);

    expect(wrapper.text()).not.toContain(REMOVED_ADMIN_NOTE);
    expect(wrapper.find('[data-test="exam-workspace-blocker-suggest-all"]').exists()).toBe(true);
    const fix = wrapper.get('[data-test="exam-workspace-blocker-fix-item_001"]');
    expect(fix.attributes("disabled")).toBeUndefined();
    expect(fix.attributes("aria-describedby")).toBeUndefined();
    wrapper.unmount();
  });
});
