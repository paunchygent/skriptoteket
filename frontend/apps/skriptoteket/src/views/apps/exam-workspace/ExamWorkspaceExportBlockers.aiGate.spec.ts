/**
 * The export blockers' answer-key fixes are admin-only until the AI spend cap
 * ships (TASK-SKRIPT-REP-0044 L3).
 *
 * Expected behavior:
 *   With role "user" or "contributor" the "Föreslå facit för alla" and the
 *   per-question "Föreslå facit" buttons are disabled, carry the admin-only
 *   note (inline and in the title), and clicking them emits nothing. The other
 *   fixes (Godkänn, Markera som granskad, …) stay available. The note appears
 *   only while one of those key controls is on screen: a panel whose blockers
 *   carry no answer-key control shows no note. With role "admin" or
 *   "superuser" the note is gone and both buttons work.
 */

import { mount } from "@vue/test-utils";
import type { DOMWrapper, VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { AI_ADMIN_ONLY_NOTE } from "../../../composables/useAiAccess";
import { useAuthStore } from "../../../stores/auth";
import ExamWorkspaceExportBlockers from "./ExamWorkspaceExportBlockers.vue";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

type Role = "user" | "contributor" | "admin" | "superuser";

function findNotes(wrapper: VueWrapper): DOMWrapper<Element>[] {
  return wrapper
    .findAll("p, small, span")
    .filter((node) => node.text().trim() === AI_ADMIN_ONLY_NOTE);
}

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

describe("ExamWorkspaceExportBlockers AI gate", () => {
  it.each(["user", "contributor"] as const)(
    "disables both key buttons, shows the note once and emits nothing for role %s",
    async (role) => {
      signIn(pinia, role);
      const wrapper = mountBlockers(pinia, TWO_KEYLESS);

      const notes = findNotes(wrapper);
      expect(notes).toHaveLength(1);
      const note = notes[0]!;
      expect(note.text()).toBe(AI_ADMIN_ONLY_NOTE);

      const all = wrapper.get('[data-test="exam-workspace-blocker-suggest-all"]');
      expect(all.attributes("disabled")).toBeDefined();
      expect(all.attributes("title")).toBe(AI_ADMIN_ONLY_NOTE);
      expect(all.attributes("aria-describedby")).toBe(note.attributes("id"));
      await all.trigger("click");
      expect(wrapper.emitted("suggestAll")).toBeUndefined();

      const fix = wrapper.get('[data-test="exam-workspace-blocker-fix-item_001"]');
      expect(fix.attributes("disabled")).toBeDefined();
      expect(fix.attributes("title")).toBe(AI_ADMIN_ONLY_NOTE);
      expect(fix.attributes("aria-describedby")).toBe(note.attributes("id"));
      await fix.trigger("click");
      expect(wrapper.emitted("fix")).toBeUndefined();
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

  it("shows no note for a non-admin whose blockers carry no AI control", () => {
    signIn(pinia, "user");
    const wrapper = mountBlockers(pinia, [
      { fix: "review", focus: null, itemId: "item_001", label: "1", problem: "kunde inte konverteras", reason: "unbuilt_question" },
    ]);

    expect(findNotes(wrapper)).toHaveLength(0);
    expect(wrapper.find('[data-test="exam-workspace-blocker-suggest-all"]').exists()).toBe(false);
    const fix = wrapper.get('[data-test="exam-workspace-blocker-fix-item_001"]');
    expect(fix.attributes("disabled")).toBeUndefined();
    expect(fix.attributes("aria-describedby")).toBeUndefined();
    wrapper.unmount();
  });

  it.each(["user", "contributor"] as const)(
    "shows the note with one disabled key fix and no batch button for role %s",
    (role) => {
      signIn(pinia, role);
      const wrapper = mountBlockers(pinia, [keyBlocker("item_001", "1")]);

      expect(wrapper.find('[data-test="exam-workspace-blocker-suggest-all"]').exists()).toBe(false);
      const notes = findNotes(wrapper);
      expect(notes).toHaveLength(1);
      const note = notes[0]!;
      expect(note.text()).toBe(AI_ADMIN_ONLY_NOTE);

      const fix = wrapper.get('[data-test="exam-workspace-blocker-fix-item_001"]');
      expect(fix.attributes("disabled")).toBeDefined();
      expect(fix.attributes("aria-describedby")).toBe(note.attributes("id"));
      wrapper.unmount();
    },
  );

  it.each(["admin", "superuser"] as const)(
    "leaves both key buttons working without the note for role %s",
    async (role) => {
      signIn(pinia, role);
      const wrapper = mountBlockers(pinia, TWO_KEYLESS);

      expect(findNotes(wrapper)).toHaveLength(0);

      const all = wrapper.get('[data-test="exam-workspace-blocker-suggest-all"]');
      expect(all.attributes("disabled")).toBeUndefined();
      await all.trigger("click");
      expect(wrapper.emitted("suggestAll")).toHaveLength(1);

      const fix = wrapper.get('[data-test="exam-workspace-blocker-fix-item_001"]');
      expect(fix.attributes("disabled")).toBeUndefined();
      await fix.trigger("click");
      expect(wrapper.emitted("fix")).toHaveLength(1);
      wrapper.unmount();
    },
  );
});
