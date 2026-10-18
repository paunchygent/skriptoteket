/**
 * Exam workspace export menu with an ordering blocker.
 *
 * Expected behavior:
 *   A red ordering row in the blocker list disables every format before any
 *   click, and an exam without blockers leaves them enabled.
 */

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ExamWorkspaceExportMenu from "./ExamWorkspaceExportMenu.vue";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";

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
    props: {
      blockers,
      checklistCount: 0,
      disabled: false,
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
  const row = document.body.querySelector(`[data-test="exam-workspace-export-${target}"]`);
  const save = document.body.querySelector(`[data-test="exam-workspace-export-save-${target}"]`);
  return {
    ariaDisabled: row?.getAttribute("aria-disabled"),
    saveDisabled: (save as HTMLButtonElement | null)?.disabled,
  };
}

afterEach(() => document.body.replaceChildren());

describe("ExamWorkspaceExportMenu ordering blocker", () => {
  it("disables every format while an ordering row is listed", async () => {
    const wrapper = mountMenu([ORDERING_ROW]);
    await openMenu(wrapper);

    expect(document.body.textContent).toContain("för få steg");
    for (const target of ["qti", "pdf", "docx"]) {
      expect(formatState(target)).toEqual({ ariaDisabled: "true", saveDisabled: true });
    }
    wrapper.unmount();
  });

  it("emits no download when a disabled format is clicked", async () => {
    const wrapper = mountMenu([ORDERING_ROW]);
    await openMenu(wrapper);
    (document.body.querySelector('[data-test="exam-workspace-export-qti"]') as HTMLElement).click();

    expect(wrapper.emitted("download")).toBeUndefined();
    wrapper.unmount();
  });

  it("enables the formats without blocker rows", async () => {
    const wrapper = mountMenu([]);
    await openMenu(wrapper);

    for (const target of ["qti", "pdf", "docx"]) {
      expect(formatState(target)).toEqual({ ariaDisabled: null, saveDisabled: false });
    }
    wrapper.unmount();
  });
});
