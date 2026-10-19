/**
 * Exam workspace header save state (TASK-SKRIPT-40-04-14, items 1 and 6).
 *
 * Expected behavior:
 *   There is no Spara button and no Spara menu item: the menu holds only
 *   Spara som. The header shows the one save status as plain text in the
 *   existing slot: `Sparar …` while storing, `Sparat HH:MM` after a store,
 *   and `Inte sparat` with the reason as its tooltip when a store failed or
 *   was refused.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import ExamWorkspaceHeader from "./ExamWorkspaceHeader.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

type HeaderProps = InstanceType<typeof ExamWorkspaceHeader>["$props"];

function props(overrides: Partial<HeaderProps> = {}): HeaderProps {
  return {
    title: "Prov 1",
    saveState: "saved",
    saveText: "Sparat 14:05",
    saveTitle: null,
    courseLabel: "Kurs",
    total: 3,
    detailsOpen: false,
    openDrawerOpen: false,
    canUndo: true,
    canRedo: false,
    canSaveAs: true,
    suggestBusy: false,
    suggestDisabled: false,
    isPhone: false,
    previewOpen: false,
    ...overrides,
  };
}

function mountHeader(overrides: Partial<HeaderProps> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(ExamWorkspaceHeader, {
    props: props(overrides),
    global: {
      plugins: [pinia, examWorkspaceProvidersPlugin()],
    },
  });
}

beforeEach(() => {
  setActivePinia(createPinia());
});

describe("ExamWorkspaceHeader save state", () => {
  it("shows the saving, saved and unsaved texts with the tooltip on Inte sparat", () => {
    const saving = mountHeader({ saveState: "saving", saveText: "Sparar …" });
    expect(saving.get('[data-test="exam-workspace-save-state"]').text()).toBe("Sparar …");
    saving.unmount();

    const saved = mountHeader({ saveState: "saved", saveText: "Sparat 14:05", saveTitle: null });
    const savedState = saved.get('[data-test="exam-workspace-save-state"]');
    expect(savedState.text()).toBe("Sparat 14:05");
    expect(savedState.attributes("title")).toBeUndefined();
    saved.unmount();

    const reason = "Provet sparades inte: frågor som fortfarande konverteras går inte att ändra.";
    const unsaved = mountHeader({ saveState: "unsaved", saveText: "Inte sparat", saveTitle: reason });
    const unsavedState = unsaved.get('[data-test="exam-workspace-save-state"]');
    expect(unsavedState.text()).toBe("Inte sparat");
    expect(unsavedState.attributes("title")).toBe(reason);
    unsaved.unmount();
  });

  it("has no Spara button and no Spara menu item, only Spara som", async () => {
    const wrapper = mountHeader();

    expect(wrapper.find('[data-test="exam-workspace-save"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-save-menu"]').trigger("click");
    expect(document.querySelector('[data-test="exam-workspace-save-option"]')).toBeNull();
    const saveAs = document.querySelector<HTMLElement>('[data-test="exam-workspace-save-as-option"]');
    expect(saveAs).not.toBeNull();

    saveAs!.click();
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("saveAs")).toHaveLength(1);
    expect(wrapper.emitted("save")).toBeUndefined();
    wrapper.unmount();
    document.body.innerHTML = "";
  });
});
