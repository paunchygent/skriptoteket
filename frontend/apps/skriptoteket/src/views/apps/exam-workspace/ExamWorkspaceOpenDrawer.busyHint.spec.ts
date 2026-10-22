/**
 * Exam workspace Öppna drawer: the busy hint must not describe the drawer's own work (U22 fail-first).
 *
 * Expected behavior (TASK-SKRIPT-41-02-06, unit U22a; the lead decides the fix):
 *   - While the drawer's own Word import runs (progress showing), the hint
 *     `data-test="exam-workspace-open-dirty-hint"` does not show
 *     "En annan åtgärd pågår. Försök igen om en stund.", and no saved-entry
 *     tooltip carries it.
 *   - While the drawer's own conversion runs, the same holds.
 *   - In a tab without the edit lock, during an import, the same holds.
 *   - A different operation that blocks opening (here a Spara som copy in
 *     flight) still shows its reason.
 *
 * Each busy state below is produced through the real composables
 * (`useExamWorkspaceEditing` over `useExamWorkspaceDocument` over
 * `useExamWorkspaceConversion`): the drawer is mounted with the session's own
 * `isBusy`, `isDirty`, save status and conversion state, never a hand-set
 * `isBusy` prop. The first three cases fail before the fix; the last one is
 * the control that must keep passing.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Plugin } from "vue";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentResponse,
} from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import ExamWorkspaceOpenDrawer from "./ExamWorkspaceOpenDrawer.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import {
  EXAM_WORKSPACE_UNREADABLE_FILES_KEY,
  useExamWorkspaceUnreadableFiles,
} from "./useExamWorkspaceUnreadableFiles";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExamWorkspaceEditLeaseServer } from "./examWorkspaceEditLeaseDrivers";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import {
  LINEAGE,
  exam,
  fakeServer,
  inScope,
  openEditing,
  response,
  stopScopes,
  type EditingApiMocks,
} from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceQti: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));
vi.mock("../../../composables/useAiAccess", async (original) => ({
  ...(await original<typeof import("../../../composables/useAiAccess")>()),
  useAiAccess: () => ({ canUseAi: { value: true } }),
}));

const unreadableApiMocks = vi.hoisted(() => ({
  downloadSavedExamFile: vi.fn(),
  listUnreadableExamWorkspaceDocuments: vi.fn(),
  removeSavedExamFile: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceUnreadableFiles", () => unreadableApiMocks);

type Editing = ReturnType<typeof useExamWorkspaceEditing>;

const BUSY_COPY = "En annan åtgärd pågår. Försök igen om en stund.";

const DOCUMENTS = [
  buildSavedExamSummary({ lineage_id: "lineage-a", title: "Prov A" }),
  buildSavedExamSummary({ lineage_id: "lineage-b", title: "Prov B" }),
];

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, reject, resolve };
}

/** Mount the drawer with the live values of a real editing session (no hand-set busy flag). */
function mountFromEditing(editing: Editing) {
  setActivePinia(createPinia());
  const unreadable = useExamWorkspaceUnreadableFiles();
  const provideUnreadable: Plugin = {
    install(app) {
      app.provide(EXAM_WORKSPACE_UNREADABLE_FILES_KEY, unreadable);
    },
  };
  const status = editing.history.saveStatus.value;
  return mount(ExamWorkspaceOpenDrawer, {
    props: {
      conversionError: editing.conversionError.value,
      conversionMessage: editing.conversionMessage.value,
      conversionElapsed: editing.conversionElapsed.value,
      conversionProgress: editing.conversionProgress.value,
      currentExports: [],
      currentLineageId: editing.summary.value?.lineage_id ?? null,
      documents: DOCUMENTS,
      importBlocked: editing.importBlocked.value,
      isBusy: editing.isBusy.value,
      isConverting: editing.isConverting.value,
      isImporting: editing.isImporting.value,
      isDirty: editing.isDirty.value,
      isOpenBlockedByOtherOperation: editing.isOpenBlockedByOtherOperation.value,
      notes: editing.notes.value,
      ordering: "newest",
      saveDetail: status.state === "unsaved" ? status.detail : null,
      saveState: status.state,
      sourceFileError: null,
    },
    global: {
      plugins: [createPinia(), examWorkspaceProvidersPlugin(), provideUnreadable],
    },
  });
}

function runningStatus(lineageId: string): ExamWorkspaceConversionStatus {
  return {
    document_revision: null,
    error_message: null,
    job_id: "job-1",
    lineage_id: lineageId,
    questions_done: 1,
    phase: null,
    phase_started_at: null,
    questions_total: 4,
    state: "running",
    summary: null,
    units: [{ item_ids: ["item_001"], question: true, state: "converting", unit_id: "unit-1" }],
  };
}

function docxFile(): File {
  return new File(["prov"], "Prov.docx", {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
}

function editingApi(): EditingApiMocks {
  return {
    getExamWorkspaceDocument: api.getExamWorkspaceDocument,
    getExamWorkspaceHistory: api.getExamWorkspaceHistory,
    getExamWorkspaceHistoryStep: api.getExamWorkspaceHistoryStep,
    moveExamWorkspaceHistoryPosition: api.moveExamWorkspaceHistoryPosition,
    storeExamWorkspaceUndoStep: api.storeExamWorkspaceUndoStep,
  };
}

function heldBy(holder: string | null) {
  return {
    holder_tab_id: holder,
    renewed_at: "2026-10-20T06:15:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

/** A session in a tab that does not hold the edit lock: its claim is refused, so it stays read-only. */
function openReadOnlyEditing(baseline = exam()): Editing {
  const server: ExamWorkspaceEditLeaseServer = {
    claim: () =>
      Promise.reject(new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 })),
    release: () => Promise.resolve(heldBy(null)),
    renew: () => Promise.resolve(heldBy("other-tab")),
    requestTakeover: () => Promise.resolve(heldBy("other-tab")),
  };
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server,
      tabId: "tab-2",
    }),
  );
  editing.applyCommandResponse(response(baseline, "step-0"));
  return editing;
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const fn of [...Object.values(api), ...Object.values(unreadableApiMocks)]) fn.mockReset();
  unreadableApiMocks.listUnreadableExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

describe("ExamWorkspaceOpenDrawer busy hint fail-first (U22)", () => {
  it("shows no busy hint for the drawer's own Word import while its progress shows", async () => {
    const mocks = editingApi();
    fakeServer(mocks, exam());
    const { editing: live } = await openEditing(mocks, exam());

    const upload = deferred<ExamWorkspaceConversionStatus>();
    const statusRequest = deferred<ExamWorkspaceConversionStatus>();
    api.importExamWorkspaceDocument.mockReturnValue(upload.promise);
    api.getExamWorkspaceConversionStatus.mockReturnValue(statusRequest.promise);

    const importing = live.importDocument(docxFile(), null);
    await Promise.resolve();
    expect(live.isConverting.value).toBe(false);
    expect(live.isOperationBusy.value).toBe(true);
    expect(live.isBusy.value).toBe(true);

    upload.resolve(runningStatus("lineage-new"));
    await flushPromises();
    await flushPromises();

    expect(live.isConverting.value).toBe(true);
    expect(live.conversionMessage.value).toContain("Konverterar provet");
    expect(live.isBusy.value).toBe(true);

    const wrapper = mountFromEditing(live);
    expect(wrapper.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(true);
    const hint = wrapper.find('[data-test="exam-workspace-open-dirty-hint"]');
    expect(hint.exists() ? hint.text() : "").not.toContain(BUSY_COPY);
    expect(
      wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title") ?? "",
    ).not.toBe(BUSY_COPY);
    wrapper.unmount();
    statusRequest.resolve(runningStatus("lineage-new"));
    await importing;
  });

  it("shows no busy hint for the drawer's own conversion", async () => {
    const mocks = editingApi();
    fakeServer(mocks, exam());
    const { editing: live } = await openEditing(mocks, exam());

    const upload = deferred<ExamWorkspaceConversionStatus>();
    const statusRequest = deferred<ExamWorkspaceConversionStatus>();
    api.importExamWorkspaceDocument.mockReturnValue(upload.promise);
    api.getExamWorkspaceConversionStatus.mockReturnValue(statusRequest.promise);

    const importing = live.importDocument(docxFile(), null);
    await Promise.resolve();
    upload.resolve(runningStatus("lineage-new"));
    await flushPromises();
    statusRequest.resolve(runningStatus("lineage-new"));
    await importing;
    await flushPromises();

    expect(live.isOperationBusy.value).toBe(true);
    expect(live.isConverting.value).toBe(true);
    expect(live.isBusy.value).toBe(true);

    const wrapper = mountFromEditing(live);
    const hint = wrapper.find('[data-test="exam-workspace-open-dirty-hint"]');
    expect(hint.exists() ? hint.text() : "").not.toContain(BUSY_COPY);
    expect(
      wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title") ?? "",
    ).not.toBe(BUSY_COPY);
    wrapper.unmount();
  });

  it("shows no busy hint for an import in a tab without the edit lock", async () => {
    const mocks = editingApi();
    fakeServer(mocks, exam());
    const live = openReadOnlyEditing(exam());
    await flushPromises();
    expect(live.leaseReadOnly.value).toBe(true);

    const upload = deferred<ExamWorkspaceConversionStatus>();
    const statusRequest = deferred<ExamWorkspaceConversionStatus>();
    api.importExamWorkspaceDocument.mockReturnValue(upload.promise);
    api.getExamWorkspaceConversionStatus.mockReturnValue(statusRequest.promise);

    const importing = live.importDocument(docxFile(), null);
    await Promise.resolve();
    expect(live.isOperationBusy.value).toBe(true);
    expect(live.isBusy.value).toBe(true);

    upload.resolve(runningStatus("lineage-new"));
    await flushPromises();

    const wrapper = mountFromEditing(live);
    const hint = wrapper.find('[data-test="exam-workspace-open-dirty-hint"]');
    expect(hint.exists() ? hint.text() : "").not.toContain(BUSY_COPY);
    expect(
      wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title") ?? "",
    ).not.toBe(BUSY_COPY);
    wrapper.unmount();
    statusRequest.resolve(runningStatus("lineage-new"));
    await importing;
  });

  it("still shows its reason while a Spara som copy blocks opening", async () => {
    const mocks = editingApi();
    fakeServer(mocks, exam());
    const { editing: live } = await openEditing(mocks, exam());

    const copying = deferred<ExamWorkspaceDocumentResponse>();
    api.copyExamWorkspaceDocument.mockReturnValue(copying.promise);
    const pending = live.beginCopy(LINEAGE, "Kopia");
    expect(pending).not.toBeNull();
    expect(live.isBusy.value).toBe(true);

    const wrapper = mountFromEditing(live);
    expect(wrapper.get('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(BUSY_COPY);
    expect(wrapper.get('[data-test="exam-workspace-open-lineage-b"]').attributes("title")).toBe(
      BUSY_COPY,
    );
    wrapper.unmount();
    copying.resolve(response(exam("Kopia"), "step-1"));
    if (pending !== null) await pending;
  });

  it("shows no toast on a blocked click during the drawer's own import", async () => {
    const mocks = editingApi();
    fakeServer(mocks, exam());
    const { editing: live } = await openEditing(mocks, exam());

    const upload = deferred<ExamWorkspaceConversionStatus>();
    const statusRequest = deferred<ExamWorkspaceConversionStatus>();
    api.importExamWorkspaceDocument.mockReturnValue(upload.promise);
    api.getExamWorkspaceConversionStatus.mockReturnValue(statusRequest.promise);

    const importing = live.importDocument(docxFile(), null);
    await Promise.resolve();
    upload.resolve(runningStatus("lineage-new"));
    await flushPromises();
    await flushPromises();

    expect(live.isBusy.value).toBe(true);
    expect(live.isOpenBlockedByOtherOperation.value).toBe(false);

    const wrapper = mountFromEditing(live);
    const entry = wrapper.get('[data-test="exam-workspace-open-lineage-b"]');
    expect(entry.attributes("aria-disabled")).toBe("true");
    expect(entry.attributes("title") ?? "").not.toContain(BUSY_COPY);

    await entry.trigger("click");

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(useToastStore().toasts.map((toast) => toast.message)).toEqual([]);
    wrapper.unmount();
    statusRequest.resolve(runningStatus("lineage-new"));
    await importing;
  });
});
