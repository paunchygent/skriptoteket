/**
 * Guest exam workspace exports (F6): the contracted print PDF and the Exam.net fallback.
 *
 * Expected behavior:
 *   In guest mode the Exportera menu offers QTI, PDF, PDF med facit, DOCX
 *   and PDF för Exam.net as separate choices. Choosing any of them downloads
 *   through the public guest export route with that target and never touches
 *   the teacher export transport. At the store seam every one of the five
 *   targets reaches the public route unchanged.
 */

import { createPinia } from "pinia";
import { flushPromises } from "@vue/test-utils";
import { ref } from "vue";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../api/examWorkspace";
import { createTestRouter, mountWithContext } from "../../test/utils";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import {
  type ExamWorkspaceGuestStoreDeps,
} from "./exam-workspace/examWorkspaceGuestStore";
import { createGuestExamWorkspaceStore } from "./exam-workspace/examWorkspaceGuestStore";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import {
  DOCUMENT_ID,
  exam,
  setupGuestStore,
  startBlank as startBlankStore,
} from "./exam-workspace/examWorkspaceGuestStore.specSupport";
import {
  EXAM_WORKSPACE_LAYOUT_KEY,
  type ExamWorkspaceLayout,
} from "./exam-workspace/useExamWorkspaceLayout";

const teacherApiMocks = vi.hoisted(() => ({
  addExamWorkspaceChild: vi.fn(),
  changeExamWorkspaceItemType: vi.fn(),
  copyExamWorkspaceDocument: vi.fn(),
  createEmptyExamWorkspacePart: vi.fn(),
  createExamWorkspaceParent: vi.fn(),
  deleteExamWorkspaceChild: vi.fn(),
  deleteExamWorkspaceParent: vi.fn(),
  downloadExamWorkspaceExport: vi.fn(),
  examWorkspaceAssetUrl: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamCourseCatalog: vi.fn(),
  getExamCourseContent: vi.fn(),
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceContentSuggestions: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  groupExamWorkspaceItems: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  moveExamWorkspaceItem: vi.fn(),
  reorderExamWorkspaceChildren: vi.fn(),
  requestExamWorkspaceAnswerKeySuggestions: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
  requestExamWorkspaceContentSuggestions: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  saveExamWorkspaceExport: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  updateExamListOrdering: vi.fn(),
}));

vi.mock("../../api/examWorkspace", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/examWorkspace")>()),
  ...teacherApiMocks,
}));

vi.mock("../../api/examWorkspaceStructureCommands", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/examWorkspaceStructureCommands")>()),
  addExamWorkspaceChild: teacherApiMocks.addExamWorkspaceChild,
  changeExamWorkspaceItemType: teacherApiMocks.changeExamWorkspaceItemType,
  createEmptyExamWorkspacePart: teacherApiMocks.createEmptyExamWorkspacePart,
  createExamWorkspaceParent: teacherApiMocks.createExamWorkspaceParent,
  deleteExamWorkspaceChild: teacherApiMocks.deleteExamWorkspaceChild,
  deleteExamWorkspaceParent: teacherApiMocks.deleteExamWorkspaceParent,
  groupExamWorkspaceItems: teacherApiMocks.groupExamWorkspaceItems,
  moveExamWorkspaceItem: teacherApiMocks.moveExamWorkspaceItem,
  reorderExamWorkspaceChildren: teacherApiMocks.reorderExamWorkspaceChildren,
}));

vi.mock("../../api/vault", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/vault")>()),
  renameVaultFile: vi.fn(),
}));

const downloadMocks = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("../../utils/browserDownload", () => downloadMocks);

const previewApiMocks = vi.hoisted(() => ({ fetchExamWorkspacePrintPreview: vi.fn() }));

vi.mock("../../api/examWorkspaceExports", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/examWorkspaceExports")>()),
  ...previewApiMocks,
}));

beforeAll(() => {
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:picture");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

type PublicApi = ExamWorkspaceGuestStoreDeps["api"];

/** The five contracted guest export targets in menu order. */
const CONTRACTED_TARGETS = ["qti", "pdf", "pdf_facit", "docx", "examnet_pdf"] as const;

function setupGuest() {
  const storage = createInMemoryExamWorkspaceGuestDraftStorage();
  const publicMocks = {
    addPublicExamWorkspaceChild: vi.fn(),
    changePublicExamWorkspaceItemType: vi.fn(),
    createEmptyPublicExamWorkspacePart: vi.fn(),
    createPublicExamWorkspaceBlank: vi.fn(),
    createPublicExamWorkspaceParent: vi.fn(),
    deletePublicExamWorkspaceChild: vi.fn(),
    deletePublicExamWorkspaceParent: vi.fn(),
    downloadPublicExamWorkspaceExport: vi.fn(),
    getPublicExamCourseCatalog: vi.fn(),
    getPublicExamWorkspaceExportChecklist: vi.fn(),
    groupPublicExamWorkspaceItems: vi.fn(),
    importPublicExamWorkspaceQti: vi.fn(),
    movePublicExamWorkspaceItem: vi.fn(),
    reorderPublicExamWorkspaceChildren: vi.fn(),
    requestPublicExamWorkspaceAnswerMisspellings: vi.fn(),
  };
  const document: NativeExamDocument = exam("Original");
  publicMocks.createPublicExamWorkspaceBlank.mockResolvedValue({
    document,
    export_blockers: [],
  });
  publicMocks.getPublicExamCourseCatalog.mockResolvedValue({
    courses: [],
    generated_at: "2026-10-18T00:00:00Z",
    registered_course_keys: [],
  });
  publicMocks.getPublicExamWorkspaceExportChecklist.mockResolvedValue({
    entries: [],
    inline_choice_min_options: 2,
  });
  const api = publicMocks as unknown as PublicApi;
  let counter = 0;
  const guest = createGuestExamWorkspaceStore({
    api,
    ids: {
      now: () => "2026-10-18T10:00:00.000Z",
      uuid: () => {
        counter += 1;
        return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
      },
    },
    onLimit: () => undefined,
    storage,
  });
  return { document, guest, publicMocks };
}

async function mountGuestView(store: ReturnType<typeof createGuestExamWorkspaceStore>["store"]) {
  const layout = ref<ExamWorkspaceLayout>("desktop");
  const wrapper = mountWithContext(ExamWorkspaceView, {
    props: { store },
    global: {
      plugins: [createPinia(), createTestRouter()],
      provide: { [EXAM_WORKSPACE_LAYOUT_KEY]: layout },
    },
  });
  await flushPromises();
  return wrapper;
}

function menuRow(target: string): HTMLElement | null {
  return document.body.querySelector<HTMLElement>(`[data-test="exam-workspace-export-${target}"]`);
}

beforeEach(() => {
  for (const mock of Object.values(teacherApiMocks)) {
    mock.mockReset();
  }
  previewApiMocks.fetchExamWorkspacePrintPreview.mockReset();
  downloadMocks.triggerBrowserDownload.mockReset();
  document.body.replaceChildren();
  window.history.replaceState({}, "", "/");
});

describe("ExamWorkspaceView guest exports", () => {
  it.each(CONTRACTED_TARGETS)(
    "offers %s in the guest Exportera menu and downloads it through the public route",
    async (target) => {
      const { guest, publicMocks } = setupGuest();
      const wrapper = await mountGuestView(guest.store);
      await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
      await flushPromises();

      await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
      await flushPromises();

      const row = menuRow(target);
      expect(row).not.toBeNull();

      publicMocks.downloadPublicExamWorkspaceExport.mockResolvedValue({
        blob: new Blob(["export"]),
        contentType: target === "qti" ? "application/zip" : "application/octet-stream",
        filename: `prov.${target === "qti" ? "zip" : "pdf"}`,
      });
      row!.click();
      await flushPromises();

      expect(publicMocks.downloadPublicExamWorkspaceExport).toHaveBeenCalledTimes(1);
      const [calledTarget, request] =
        publicMocks.downloadPublicExamWorkspaceExport.mock.calls[0]!;
      expect(calledTarget).toBe(target);
      expect(request.document.title).toBe("Original");
      expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledTimes(1);
      for (const mock of Object.values(teacherApiMocks)) {
        expect(mock).not.toHaveBeenCalled();
      }
      expect(previewApiMocks.fetchExamWorkspacePrintPreview).not.toHaveBeenCalled();
      wrapper.unmount();
      document.body.replaceChildren();
    },
  );

  it("hides the teacher-only Förhandsgranska toggle in guest mode without calling its render", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    expect(
      wrapper.find('[data-test="exam-workspace-print-preview-toggle"]').exists(),
    ).toBe(false);
    expect(previewApiMocks.fetchExamWorkspacePrintPreview).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("names the print PDF and the Exam.net fallback as separate guest choices", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();

    expect(document.body.textContent).toContain("PDF för Exam.net");
    expect(menuRow("pdf")).not.toBeNull();
    expect(menuRow("examnet_pdf")).not.toBeNull();
    expect(menuRow("pdf")).not.toBe(menuRow("examnet_pdf"));
    expect(
      wrapper.find('[data-test="exam-workspace-print-preview-toggle"]').exists(),
    ).toBe(false);
    expect(previewApiMocks.fetchExamWorkspacePrintPreview).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});

describe("examWorkspaceGuestStore export targets", () => {
  it.each(CONTRACTED_TARGETS)(
    "passes the %s target to the public export route unchanged",
    async (target) => {
      const context = setupGuestStore();
      await startBlankStore(context);
      context.mocks.exportDownload.mockResolvedValue({
        blob: new Blob(["export"]),
        contentType: "application/octet-stream",
        filename: "prov",
      });

      await context.store.store.shared.downloadExamWorkspaceExport(DOCUMENT_ID, target, 1);

      expect(context.mocks.exportDownload).toHaveBeenCalledTimes(1);
      const [calledTarget, request] = context.mocks.exportDownload.mock.calls[0]!;
      expect(calledTarget).toBe(target);
      expect(request.document.title).toBe("Original");
    },
  );
});
