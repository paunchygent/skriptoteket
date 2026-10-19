/**
 * The header's "Föreslå facit för frågor som saknar facit" button is admin-only
 * until the AI spend cap ships (TASK-SKRIPT-REP-0044 L3).
 *
 * Expected behavior:
 *   With role "user" or "contributor" the icon button is disabled, its title is
 *   the admin-only note, and the exact note is rendered once as visible inline
 *   text the button points to with aria-describedby. With role "admin" or
 *   "superuser" the note is absent, the button works, and the existing
 *   busy/disabled reasons still hold.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { AI_ADMIN_ONLY_NOTE } from "../../../composables/useAiAccess";
import { useAuthStore } from "../../../stores/auth";
import ExamWorkspaceHeader from "./ExamWorkspaceHeader.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

const SUGGEST_TITLE = "Föreslå facit för frågor som saknar facit";

type HeaderProps = InstanceType<typeof ExamWorkspaceHeader>["$props"];

function props(overrides: Partial<HeaderProps> = {}): HeaderProps {
  return {
    title: "Prov 1",
    saveState: "saved",
    saveText: "Sparat",
    saveTitle: null,
    courseLabel: null,
    total: 0,
    detailsOpen: false,
    openDrawerOpen: false,
    canUndo: false,
    canRedo: false,
    canSaveAs: true,
    suggestBusy: false,
    suggestDisabled: false,
    isPhone: false,
    previewOpen: false,
    ...overrides,
  };
}

function mountHeader(pinia: Pinia, overrides: Partial<HeaderProps> = {}) {
  return mount(ExamWorkspaceHeader, {
    props: props(overrides),
    global: {
      plugins: [pinia, examWorkspaceProvidersPlugin()],
    },
  });
}

/** Elements carrying the exact note as their visible text, found without test hooks. */
function noteElements(wrapper: ReturnType<typeof mountHeader>) {
  return wrapper.findAll("*").filter((element) => element.text().trim() === AI_ADMIN_ONLY_NOTE);
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
});

describe("ExamWorkspaceHeader AI gate", () => {
  it.each(["user", "contributor"] as const)(
    "disables the suggest-all button and shows the note inline for role %s",
    (role) => {
      setActivePinia(pinia);
      useAuthStore().user = { id: "u1", email: "u@example.test", role, auth_provider: "local" };
      const wrapper = mountHeader(pinia);

      const button = wrapper.get('[data-test="exam-workspace-suggest-all"]');
      expect(button.attributes("disabled")).toBeDefined();
      expect(button.attributes("title")).toBe(AI_ADMIN_ONLY_NOTE);

      const notes = noteElements(wrapper);
      expect(notes).toHaveLength(1);
      const note = notes[0]!;
      expect(note.isVisible()).toBe(true);
      expect(button.attributes("aria-describedby")).toBe(note.element.id);
      wrapper.unmount();
    },
  );

  it.each(["admin", "superuser"] as const)(
    "leaves the suggest-all button working without the note for role %s",
    async (role) => {
      setActivePinia(pinia);
      useAuthStore().user = { id: "u1", email: "u@example.test", role, auth_provider: "local" };
      const wrapper = mountHeader(pinia);

      const button = wrapper.get('[data-test="exam-workspace-suggest-all"]');
      expect(button.attributes("disabled")).toBeUndefined();
      expect(button.attributes("title")).toBe(SUGGEST_TITLE);
      expect(button.attributes("aria-describedby")).toBeUndefined();
      expect(noteElements(wrapper)).toHaveLength(0);
      await button.trigger("click");
      expect(wrapper.emitted("suggestAll")).toHaveLength(1);
      wrapper.unmount();
    },
  );

  it("keeps a disabled reason for an admin when the exam is busy", () => {
    setActivePinia(pinia);
    useAuthStore().user = { id: "u1", email: "u@example.test", role: "admin", auth_provider: "local" };
    const wrapper = mountHeader(pinia, { suggestBusy: true });

    const button = wrapper.get('[data-test="exam-workspace-suggest-all"]');
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.attributes("title")).toBe("Facitförslagen tas fram …");
    wrapper.unmount();
  });
});
