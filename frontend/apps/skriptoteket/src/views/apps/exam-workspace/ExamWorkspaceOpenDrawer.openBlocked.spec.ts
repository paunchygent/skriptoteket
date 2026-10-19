/**
 * Exam workspace Öppna drawer: a blocked Öppna click gets feedback.
 *
 * Expected behavior (CR1 C1/C2):
 *   While the open exam has a pending save, another operation runs, or the
 *   last save failed/was refused, a click (or Enter/Space) on another saved
 *   exam does not open it. The hint, the entry tooltip and the blocked-click
 *   toast all use one reason per state: the pending-save copy while an edit
 *   is not yet stored, the busy copy for another operation without a pending
 *   save, and the save status's own reason when it reads Inte sparat. The
 *   old "Spara det öppna provet …" copy is gone.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useToastStore } from "../../../stores/toast";
import ExamWorkspaceOpenDrawer from "./ExamWorkspaceOpenDrawer.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";

const PENDING_COPY = "Vänta tills ändringarna har sparats.";
const BUSY_COPY = "En annan åtgärd pågår. Försök igen om en stund.";
const FAILED_REASON = "Ändringen sparades inte eftersom provet redigeras i den andra fliken.";

const DOCUMENTS = [
  buildSavedExamSummary({ lineage_id: "lineage-a", title: "Prov A" }),
  buildSavedExamSummary({ lineage_id: "lineage-b", title: "Prov B" }),
];

type SaveState = "saving" | "saved" | "unsaved";

function mountDrawer(options: {
  currentLineageId: string | null;
  isBusy: boolean;
  isDirty: boolean;
  saveState: SaveState;
  saveDetail: string | null;
}) {
  setActivePinia(createPinia());
  return mount(ExamWorkspaceOpenDrawer, {
    props: {
      conversionError: null,
      conversionMessage: null,
      conversionProgress: null,
      currentExports: [],
      currentLineageId: options.currentLineageId,
      documents: DOCUMENTS,
      importBlocked: false,
      isBusy: options.isBusy,
      isConverting: false,
      isDirty: options.isDirty,
      notes: [],
      ordering: "newest",
      saveDetail: options.saveDetail,
      saveState: options.saveState,
      sourceFileError: null,
    },
    global: {
      plugins: [createPinia(), examWorkspaceProvidersPlugin()],
    },
  });
}

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

describe("ExamWorkspaceOpenDrawer blocked open", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("shows the pending-save copy in the hint, tooltip and toast while an edit is not yet stored", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: null,
      saveState: "saving",
    });

    expect(wrapper.get('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(PENDING_COPY);
    expect(
      wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title"),
    ).toBe(PENDING_COPY);

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(PENDING_COPY);
  });

  it("shows the busy copy when only another operation runs", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: true,
      isDirty: false,
      saveDetail: null,
      saveState: "saved",
    });

    expect(wrapper.get('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(BUSY_COPY);
    expect(
      wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title"),
    ).toBe(BUSY_COPY);

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(BUSY_COPY);
  });

  it("shows the save status reason when the last save failed or was refused", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: FAILED_REASON,
      saveState: "unsaved",
    });

    expect(wrapper.get('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(FAILED_REASON);
    expect(
      wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title"),
    ).toBe(FAILED_REASON);

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(FAILED_REASON);
  });

  it("opens without feedback when nothing blocks it", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: false,
      saveDetail: null,
      saveState: "saved",
    });

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toEqual([["lineage-b"]]);
    expect(toastMessages()).toEqual([]);
  });

  it("stays silent when the open exam itself is clicked", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: null,
      saveState: "saving",
    });

    await wrapper.get('[data-test="exam-workspace-open-lineage-a"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toEqual([]);
  });

  it("never shows the old save-the-open-exam copy", async () => {
    const blocked = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: null,
      saveState: "saving",
    });
    expect(blocked.html()).not.toContain("Spara det öppna provet");
    blocked.unmount();

    const failed = mountDrawer({
      currentLineageId: "lineage-a",
      isBusy: false,
      isDirty: true,
      saveDetail: FAILED_REASON,
      saveState: "unsaved",
    });
    expect(failed.html()).not.toContain("Spara det öppna provet");
    failed.unmount();
  });
});
