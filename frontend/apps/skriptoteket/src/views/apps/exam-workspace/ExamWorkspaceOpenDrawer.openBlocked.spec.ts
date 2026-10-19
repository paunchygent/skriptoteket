/**
 * Exam workspace Öppna drawer: a blocked Öppna click gets feedback.
 *
 * Expected behavior (unit D1o):
 *   While the open exam has unsaved changes or another operation runs, a
 *   click (or Enter/Space) on another saved exam does not open it and tells
 *   the teacher to wait until the changes are saved. The feedback reuses the
 *   drawer's workspace-wide toast channel, the same channel an open failure
 *   reports through. Clicking the already open exam stays silent.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useToastStore } from "../../../stores/toast";
import ExamWorkspaceOpenDrawer from "./ExamWorkspaceOpenDrawer.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";

const BLOCKED_COPY = "Vänta tills ändringarna har sparats.";

const DOCUMENTS = [
  buildSavedExamSummary({ lineage_id: "lineage-a", title: "Prov A" }),
  buildSavedExamSummary({ lineage_id: "lineage-b", title: "Prov B" }),
];

function mountDrawer(options: { currentLineageId: string | null; isBusy: boolean; isDirty: boolean }) {
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

  it("tells the teacher to wait instead of opening while edits are unsaved", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", isBusy: false, isDirty: true });

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(BLOCKED_COPY);
  });

  it("tells the teacher to wait instead of opening while another operation runs", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", isBusy: true, isDirty: false });

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toContain(BLOCKED_COPY);
  });

  it("opens without feedback when nothing blocks it", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", isBusy: false, isDirty: false });

    await wrapper.get('[data-test="exam-workspace-open-lineage-b"]').trigger("click");

    expect(wrapper.emitted("open")).toEqual([["lineage-b"]]);
    expect(toastMessages()).toEqual([]);
  });

  it("stays silent when the open exam itself is clicked", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", isBusy: false, isDirty: true });

    await wrapper.get('[data-test="exam-workspace-open-lineage-a"]').trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(toastMessages()).toEqual([]);
  });
});
