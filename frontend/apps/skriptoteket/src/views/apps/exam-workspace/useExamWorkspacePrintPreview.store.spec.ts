/**
 * Exam workspace Förhandsgranska runs through the store seam (TASK-SKRIPT-41-02-02, R12).
 *
 * Expected behavior:
 *   The preview fetch is a teacher-half store call: with a signed-in store
 *   the open panel renders through `store.teacher.fetchExamWorkspacePrintPreview`,
 *   and with a guest store (`teacher` null) nothing is fetched and no failure
 *   is reported. The composable never imports the teacher transport directly.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import { useToastStore } from "../../../stores/toast";
import {
  PREVIEW_DEBOUNCE_MS,
  useExamWorkspacePrintPreview,
} from "./useExamWorkspacePrintPreview";
import { HISTORY_BASELINE_STEP_ID } from "../ExamWorkspaceHistory.specSupport";
import { arrangeStepHistory } from "../ExamWorkspaceHistory.specSupport";
import {
  arrangeExportApis,
} from "../ExamWorkspaceExportsSlice.specSupport";
import {
  importFixtureDocument,
  mountExamWorkspace,
  type ViewWrapper,
} from "../ExamWorkspaceSlice.specSupport";
import {
  serverExamWorkspaceStore,
  type ExamWorkspaceStore,
} from "./examWorkspaceStore";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  fetchExamWorkspacePrintPreview: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceExports", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../api/examWorkspaceExports")>()),
  ...exportApiMocks,
}));
vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const downloadMocks = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("../../../utils/browserDownload", () => downloadMocks);

function ready(pages: string[]) {
  return { message: null, pages, question_pages: {}, revision: 1, status: "ready" as const };
}

/** A signed-in store whose teacher preview is the given spy. */
function teacherStoreWithPreviewSpy(preview: Mock): ExamWorkspaceStore {
  const teacher = serverExamWorkspaceStore.teacher;
  if (teacher === null) throw new Error("The server store has no teacher half.");
  return {
    ...serverExamWorkspaceStore,
    teacher: { ...teacher, fetchExamWorkspacePrintPreview: preview },
  };
}

function mountPreview(store: ExamWorkspaceStore) {
  const lineageId = ref<string | null>("lineage-1");
  const savedRevision = ref<number | null>(1);
  const historyCursor = ref<string | null>(HISTORY_BASELINE_STEP_ID);
  const historyPosition = ref<string | null>(HISTORY_BASELINE_STEP_ID);
  const open = ref(false);
  const selectedItemId = ref<string | null>(null);
  const scope = effectScope();
  const preview = scope.run(() =>
    useExamWorkspacePrintPreview({
      historyCursor,
      historyPosition,
      lineageId,
      open,
      savedRevision,
      selectedItemId,
      store,
    }),
  );
  if (!preview) throw new Error("preview composable did not mount");
  return { historyCursor, historyPosition, lineageId, open, preview, savedRevision, scope };
}

const mountedViews: ViewWrapper[] = [];

beforeEach(() => {
  setActivePinia(createPinia());
  arrangeExportApis({ api: apiMocks, exportApi: exportApiMocks, download: downloadMocks });
  arrangeStepHistory(apiMocks);
  exportApiMocks.fetchExamWorkspacePrintPreview.mockReset();
  exportApiMocks.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
});

afterEach(() => {
  for (const wrapper of mountedViews.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

async function elapse(ms: number): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

describe("useExamWorkspacePrintPreview through the store seam", () => {
  it("fetches the open panel through the injected store teacher half", async () => {
    vi.useFakeTimers();
    const teacherPreview = vi.fn().mockResolvedValue(ready(["page-1"]));
    const { open, preview, scope } = mountPreview(teacherStoreWithPreviewSpy(teacherPreview));

    open.value = true;
    await nextTick();
    await elapse(PREVIEW_DEBOUNCE_MS);

    expect(teacherPreview).toHaveBeenCalledTimes(1);
    expect(teacherPreview).toHaveBeenCalledWith(
      "lineage-1",
      1,
      HISTORY_BASELINE_STEP_ID,
      HISTORY_BASELINE_STEP_ID,
    );
    expect(exportApiMocks.fetchExamWorkspacePrintPreview).not.toHaveBeenCalled();
    expect(preview.pages.value).toEqual(["page-1"]);
    scope.stop();
  });

  it("fetches nothing and reports nothing with a guest store", async () => {
    vi.useFakeTimers();
    const { open, preview, scope } = mountPreview({ ...serverExamWorkspaceStore, teacher: null });

    open.value = true;
    await nextTick();
    await elapse(PREVIEW_DEBOUNCE_MS + 1000);

    expect(exportApiMocks.fetchExamWorkspacePrintPreview).not.toHaveBeenCalled();
    expect(preview.pages.value).toEqual([]);
    expect(preview.loading.value).toBe(false);
    expect(useToastStore().toasts).toHaveLength(0);
    scope.stop();
  });

  it("renders the signed-in view preview through the store teacher half", async () => {
    const teacher = serverExamWorkspaceStore.teacher;
    if (teacher === null) throw new Error("The server store has no teacher half.");
    const teacherPreview = vi.spyOn(teacher, "fetchExamWorkspacePrintPreview");
    const { wrapper } = await mountExamWorkspace({}, "desktop", document.body);
    mountedViews.push(wrapper);
    await importFixtureDocument(wrapper);

    await wrapper.get('[data-test="exam-workspace-print-preview-toggle"]').trigger("click");
    await flushPromises();
    await new Promise((resolve) => setTimeout(resolve, PREVIEW_DEBOUNCE_MS + 400));
    await flushPromises();

    expect(teacherPreview).toHaveBeenCalledTimes(1);
    expect(teacherPreview).toHaveBeenCalledWith(
      "lineage-1",
      1,
      "00000000-0000-4000-8000-000000000001",
      HISTORY_BASELINE_STEP_ID,
    );
  });
});
