/**
 * Exam workspace export menu with an ordering blocker.
 *
 * Expected behavior:
 *   A red ordering row in the blocker list marks every split part
 *   aria-disabled before any click, and an exam without blockers leaves them
 *   enabled. Parts never take the native disabled attribute, so focus stays
 *   on the running part.
 */

import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { adminUser } from "../ExamWorkspaceSlice.specSupport";
import ExamWorkspaceExportMenu from "./ExamWorkspaceExportMenu.vue";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import { EXAM_WORKSPACE_EXPORT_FORMATS } from "./examWorkspaceExportFormats";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

const ORDERING_ROW: ExamWorkspaceBlockerEntry = {
  fix: null,
  focus: '[data-test="exam-workspace-ordering-add-step"]',
  itemId: "item_001",
  label: "1",
  problem: "för få steg",
  reason: "ordering_too_few_steps",
};

function mountMenu(blockers: ExamWorkspaceBlockerEntry[]) {
  return mount(ExamWorkspaceExportMenu, {
    attachTo: document.body,
    global: {
      // The export menu mounts signed in; every signed-in user runs the AI
      // controls, so the default stubbed auth store is enough for these cases.
      plugins: [
        createTestingPinia({
          createSpy: vi.fn,
          initialState: { auth: { user: adminUser } },
        }),
        examWorkspaceProvidersPlugin(),
      ],
    },
    props: {
      blockers,
      checklistCount: 0,
      disabled: false,
      exportingDestination: null,
      exportingTarget: null,
      fixDisabled: false,
      isPhone: false,
      result: null,
      savedExports: {},
      suggestBusy: false,
      zeroPoints: false,
    },
  });
}

async function openMenu(wrapper: ReturnType<typeof mountMenu>): Promise<void> {
  await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
}

function formatState(target: string) {
  const download = document.body.querySelector(`[data-test="exam-workspace-export-${target}"]`);
  const save = document.body.querySelector(`[data-test="exam-workspace-export-save-${target}"]`);
  return {
    downloadAriaDisabled: download?.getAttribute("aria-disabled"),
    downloadNativeDisabled: download?.hasAttribute("disabled"),
    saveAriaDisabled: save?.getAttribute("aria-disabled"),
    saveNativeDisabled: save?.hasAttribute("disabled"),
  };
}

afterEach(() => document.body.replaceChildren());

describe("ExamWorkspaceExportMenu ordering blocker", () => {
  it("disables every format while an ordering row is listed", async () => {
    const wrapper = mountMenu([ORDERING_ROW]);
    await openMenu(wrapper);

    expect(document.body.textContent).toContain("för få steg");
    for (const { target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      expect(formatState(target)).toEqual({
        downloadAriaDisabled: "true",
        downloadNativeDisabled: false,
        saveAriaDisabled: "true",
        saveNativeDisabled: false,
      });
    }
    wrapper.unmount();
  });

  it("emits no download when a disabled format is clicked", async () => {
    const wrapper = mountMenu([ORDERING_ROW]);
    await openMenu(wrapper);
    const qti = document.body.querySelector<HTMLElement>('[data-test="exam-workspace-export-qti"]');
    expect(qti).not.toBeNull();
    qti?.click();

    expect(wrapper.emitted("download")).toBeUndefined();
    wrapper.unmount();
  });

  it("enables the formats without blocker rows", async () => {
    const wrapper = mountMenu([]);
    await openMenu(wrapper);

    for (const { target } of EXAM_WORKSPACE_EXPORT_FORMATS) {
      expect(formatState(target)).toEqual({
        downloadAriaDisabled: null,
        downloadNativeDisabled: false,
        saveAriaDisabled: null,
        saveNativeDisabled: false,
      });
    }
    wrapper.unmount();
  });
});
