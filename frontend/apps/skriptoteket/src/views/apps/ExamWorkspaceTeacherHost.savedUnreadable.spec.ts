/**
 * Teacher host saved-unreadable notice (TASK-SKRIPT-41-02-06, U5).
 *
 * Expected behavior, all under the real Vue Router (memory history) with the
 * real exam workspace view:
 *   A deep link `?document=<lineage>` whose GET fails with 422
 *   `DOCUMENT_SCHEMA_OUTDATED` shows the shared download-or-remove notice
 *   (`saved_unreadable`, copy S1) for that exam, and no toast shows at any
 *   point. The same holds for `DOCUMENT_UNREADABLE` when the exam is present
 *   only in the saved (readable) list: the record resolves from the saved
 *   list. Download calls `downloadSavedExamFile` with that vault file id;
 *   remove calls `removeSavedExamFile`, then the notice clears and the lists
 *   reload. A corrupt current-version file that lives only in the saved list
 *   clears the same way once the server confirms the delete; a failed delete
 *   keeps the notice and the row with the remove-failure toast. An ordinary failure (500) still shows `OPEN_FAILURE_COPY` and no
 *   notice. Opening another readable exam afterwards installs it and clears
 *   the notice. When neither list holds the lineage, the ordinary
 *   open-failure toast shows and no notice appears.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter, type Router } from "vue-router";

import { ApiError } from "../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../api/examWorkspace";
import type { ExamWorkspaceUnreadableDocument } from "../../api/examWorkspaceUnreadableFiles";
import { useToastStore } from "../../stores/toast";
import ExamWorkspaceTeacherHost from "./ExamWorkspaceTeacherHost.vue";
import {
  EXAM_WORKSPACE_FILE_NOTICE_REMOVE_FAILURE_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY,
} from "./exam-workspace/examWorkspaceFileNoticeCopy";
import type { StoredGuestDraft } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import {
  exam,
  response,
} from "./exam-workspace/useExamWorkspaceEditing.history.specSupport";
import { deferred } from "./exam-workspace/useExamWorkspaceSyncGate.specSupport";

const OUTDATED_LINEAGE = "22222222-0000-4000-8000-000000000002";
const CORRUPT_LINEAGE = "33333333-0000-4000-8000-000000000003";
const READABLE_LINEAGE = "44444444-0000-4000-8000-000000000004";
const UNKNOWN_LINEAGE = "55555555-0000-4000-8000-000000000005";
const VAULT_FILE_ID = "66666666-0000-4000-8000-000000000006";

const OPEN_FAILURE_COPY = "Det gick inte att öppna provet. Försök igen.";

const api = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const unreadableApi = vi.hoisted(() => ({
  downloadSavedExamFile: vi.fn(),
  listUnreadableExamWorkspaceDocuments: vi.fn(),
  removeSavedExamFile: vi.fn(),
}));
const downloadSink = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));
const storageMocks = vi.hoisted((): { stored: StoredGuestDraft | null } => ({ stored: null }));

vi.mock("../../api/examWorkspace", async () => ({
  ...api,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));
vi.mock("../../api/examWorkspaceUnreadableFiles", () => unreadableApi);
vi.mock("../../api/examWorkspaceExports", () => ({ downloadExamWorkspaceExport: vi.fn() }));
vi.mock("../../utils/browserDownload", () => downloadSink);
vi.mock("./exam-workspace/examWorkspaceGuestDraftStorage", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./exam-workspace/examWorkspaceGuestDraftStorage")>()),
  createExamWorkspaceGuestDraftStorage: () => ({
    async clearIf(cursor: string) {
      if (storageMocks.stored?.draft.cursor !== cursor) {
        return false;
      }
      storageMocks.stored = null;
      return true;
    },
    async load() {
      return storageMocks.stored;
    },
  }),
}));
vi.mock("./exam-workspace/examWorkspaceGuestHandoffLock", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("./exam-workspace/examWorkspaceGuestHandoffLock")>();
  return {
    ...actual,
    createWebGuestHandoffLock: () => actual.createInMemoryGuestHandoffLock(),
  };
});

function reply(lineageId: string, title: string): ExamWorkspaceDocumentResponse {
  const document: NativeExamDocument = { ...exam(title), document_id: lineageId };
  const payload = response(document, "step-0");
  return {
    ...payload,
    summary: {
      ...payload.summary,
      lineage_id: lineageId,
      title,
      vault_file_id: VAULT_FILE_ID,
    },
  };
}

function unreadableRecord(lineageId: string): ExamWorkspaceUnreadableDocument {
  return {
    lineage_id: lineageId,
    name: "Gammalt prov.provdokument.zip",
    saved_at: "2026-10-11T08:00:00Z",
    title: "Gammalt prov",
    vault_file_id: VAULT_FILE_ID,
  };
}

function outdatedError(): ApiError {
  return new ApiError({
    code: "DOCUMENT_SCHEMA_OUTDATED",
    message: "Native exam document uses an outdated schema version.",
    status: 422,
  });
}

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

/** The saved-unreadable notice in the host's own slot above the view: the
 * handoff notice shares the slot, and the drawer's rows carry the same
 * notice deeper down, so the host's direct child selects it exactly. */
function viewNotice(wrapper: ReturnType<typeof mount>) {
  return wrapper.find(
    '[data-test="exam-workspace-teacher-host"] > [data-test="exam-workspace-file-notice"]',
  );
}

function viewNoticeText(wrapper: ReturnType<typeof mount>): string {
  return viewNotice(wrapper).get('[data-test="exam-workspace-file-notice-text"]').text();
}

async function settle(): Promise<void> {
  for (let index = 0; index < 12; index += 1) {
    await flushPromises();
  }
}

async function mountAtDocument(document: string): Promise<{
  router: Router;
  wrapper: ReturnType<typeof mount>;
}> {
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ component: { template: "<div />" }, path: "/workspace" }],
  });
  await router.push({ path: "/workspace", query: { document } });
  await router.isReady();
  const wrapper = mount(ExamWorkspaceTeacherHost, { global: { plugins: [pinia, router] } });
  await settle();
  return { router, wrapper };
}

beforeEach(() => {
  localStorage.clear();
  storageMocks.stored = null;
  for (const mock of Object.values(api)) {
    mock.mockReset();
  }
  for (const mock of Object.values(unreadableApi)) {
    mock.mockReset();
  }
  downloadSink.triggerBrowserDownload.mockReset();
  api.getExamWorkspaceHistory.mockResolvedValue({
    baseline_step_id: "step-0",
    cursor: "step-0",
    position_step_id: "step-0",
    step_ids: [],
  });
  api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "newest" });
  unreadableApi.listUnreadableExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
});

describe("ExamWorkspaceTeacherHost saved-unreadable notice", () => {
  it("an outdated deep link shows the download-or-remove notice with no toast", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(outdatedError());
    unreadableApi.listUnreadableExamWorkspaceDocuments.mockResolvedValue({
      documents: [unreadableRecord(OUTDATED_LINEAGE)],
    });
    const { wrapper } = await mountAtDocument(OUTDATED_LINEAGE);
    try {
      expect(viewNotice(wrapper).exists()).toBe(true);
      expect(viewNoticeText(wrapper)).toBe(EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY);
      expect(
        viewNotice(wrapper).find('[data-test="exam-workspace-file-notice-download"]').exists(),
      ).toBe(true);
      expect(
        viewNotice(wrapper).find('[data-test="exam-workspace-file-notice-remove"]').exists(),
      ).toBe(true);
      expect(toastMessages()).toEqual([]);
    } finally {
      wrapper.unmount();
    }
  });

  it("a corrupt current-version file resolves from the saved list with no toast", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "DOCUMENT_UNREADABLE",
        message: "Stored exam file cannot be read.",
        status: 422,
      }),
    );
    const saved = reply(CORRUPT_LINEAGE, "Korrupt prov");
    api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [saved.summary], ordering: "newest" });
    const { wrapper } = await mountAtDocument(CORRUPT_LINEAGE);
    try {
      expect(viewNoticeText(wrapper)).toBe(EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY);
      expect(toastMessages()).toEqual([]);
    } finally {
      wrapper.unmount();
    }
  });

  it("download fetches the stored file unchanged", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(outdatedError());
    unreadableApi.listUnreadableExamWorkspaceDocuments.mockResolvedValue({
      documents: [unreadableRecord(OUTDATED_LINEAGE)],
    });
    const pending = deferred<{ blob: Blob; filename: string | null }>();
    unreadableApi.downloadSavedExamFile.mockReturnValue(pending.promise);
    const { wrapper } = await mountAtDocument(OUTDATED_LINEAGE);
    try {
      const downloadButton = '[data-test="exam-workspace-file-notice-download"]';
      await viewNotice(wrapper).get(downloadButton).trigger("click");
      await flushPromises();
      expect(viewNotice(wrapper).get(downloadButton).attributes("disabled")).toBeDefined();
      pending.resolve({ blob: new Blob(["prov"]), filename: "Gammalt prov.provdokument.zip" });
      await settle();
      expect(unreadableApi.downloadSavedExamFile).toHaveBeenCalledWith(VAULT_FILE_ID);
      expect(downloadSink.triggerBrowserDownload).toHaveBeenCalledTimes(1);
      expect(toastMessages()).toEqual([]);
    } finally {
      wrapper.unmount();
    }
  });

  it("remove deletes the file, clears the notice and reloads the lists", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(outdatedError());
    let unreadableRows = [unreadableRecord(OUTDATED_LINEAGE)];
    unreadableApi.listUnreadableExamWorkspaceDocuments.mockImplementation(async () => ({
      documents: [...unreadableRows],
    }));
    unreadableApi.removeSavedExamFile.mockImplementation(async () => {
      unreadableRows = [];
      return { file_id: VAULT_FILE_ID };
    });
    const { wrapper } = await mountAtDocument(OUTDATED_LINEAGE);
    try {
      expect(viewNotice(wrapper).exists()).toBe(true);
      expect(wrapper.find(`[data-test="exam-workspace-unreadable-${OUTDATED_LINEAGE}"]`).exists()).toBe(true);
      const unreadableCalls = unreadableApi.listUnreadableExamWorkspaceDocuments.mock.calls.length;
      const savedCalls = api.listExamWorkspaceDocuments.mock.calls.length;
      await viewNotice(wrapper).get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
      await settle();
      expect(unreadableApi.removeSavedExamFile).toHaveBeenCalledWith(VAULT_FILE_ID);
      expect(viewNotice(wrapper).exists()).toBe(false);
      expect(wrapper.find(`[data-test="exam-workspace-unreadable-${OUTDATED_LINEAGE}"]`).exists()).toBe(false);
      expect(unreadableApi.listUnreadableExamWorkspaceDocuments.mock.calls.length).toBeGreaterThan(unreadableCalls);
      expect(api.listExamWorkspaceDocuments.mock.calls.length).toBeGreaterThan(savedCalls);
    } finally {
      wrapper.unmount();
    }
  });

  it("remove clears a corrupt current-version file from the notice and the saved rows", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "DOCUMENT_UNREADABLE",
        message: "Stored exam file cannot be read.",
        status: 422,
      }),
    );
    const saved = reply(CORRUPT_LINEAGE, "Korrupt prov");
    let savedRows = [saved.summary];
    api.listExamWorkspaceDocuments.mockImplementation(async () => ({
      documents: [...savedRows],
      ordering: "newest",
    }));
    unreadableApi.removeSavedExamFile.mockImplementation(async () => {
      savedRows = [];
      return { file_id: VAULT_FILE_ID };
    });
    const { wrapper } = await mountAtDocument(CORRUPT_LINEAGE);
    try {
      expect(viewNotice(wrapper).exists()).toBe(true);
      expect(wrapper.find(`[data-test="exam-workspace-open-${CORRUPT_LINEAGE}"]`).exists()).toBe(true);
      await viewNotice(wrapper).get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
      await settle();
      expect(unreadableApi.removeSavedExamFile).toHaveBeenCalledWith(VAULT_FILE_ID);
      expect(savedRows).toEqual([]);
      expect(viewNotice(wrapper).exists()).toBe(false);
      expect(wrapper.find(`[data-test="exam-workspace-open-${CORRUPT_LINEAGE}"]`).exists()).toBe(false);
    } finally {
      wrapper.unmount();
    }
  });

  it("a failed remove keeps the corrupt file's notice and saved row", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "DOCUMENT_UNREADABLE",
        message: "Stored exam file cannot be read.",
        status: 422,
      }),
    );
    const saved = reply(CORRUPT_LINEAGE, "Korrupt prov");
    api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [saved.summary], ordering: "newest" });
    unreadableApi.removeSavedExamFile.mockRejectedValueOnce(new Error("nätet är nere"));
    const { wrapper } = await mountAtDocument(CORRUPT_LINEAGE);
    try {
      expect(viewNotice(wrapper).exists()).toBe(true);
      await viewNotice(wrapper).get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
      await settle();
      expect(unreadableApi.removeSavedExamFile).toHaveBeenCalledWith(VAULT_FILE_ID);
      expect(viewNotice(wrapper).exists()).toBe(true);
      expect(wrapper.find(`[data-test="exam-workspace-open-${CORRUPT_LINEAGE}"]`).exists()).toBe(true);
      expect(toastMessages()).toContain(EXAM_WORKSPACE_FILE_NOTICE_REMOVE_FAILURE_COPY);
    } finally {
      wrapper.unmount();
    }
  });

  it("an ordinary failure still shows the open-failure toast and no notice", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(
      new ApiError({ code: "SERVER_ERROR", message: " exploded", status: 500 }),
    );
    const { wrapper } = await mountAtDocument(OUTDATED_LINEAGE);
    try {
      expect(viewNotice(wrapper).exists()).toBe(false);
      expect(toastMessages()).toContain(OPEN_FAILURE_COPY);
    } finally {
      wrapper.unmount();
    }
  });

  it("opening another readable exam afterwards installs it and clears the notice", async () => {
    api.getExamWorkspaceDocument.mockImplementation(async (lineageId: string) => {
      if (lineageId === READABLE_LINEAGE) {
        return reply(READABLE_LINEAGE, "Läsbart prov");
      }
      throw outdatedError();
    });
    unreadableApi.listUnreadableExamWorkspaceDocuments.mockResolvedValue({
      documents: [unreadableRecord(OUTDATED_LINEAGE)],
    });
    const { router, wrapper } = await mountAtDocument(OUTDATED_LINEAGE);
    try {
      expect(viewNotice(wrapper).exists()).toBe(true);
      await router.push({ path: "/workspace", query: { document: READABLE_LINEAGE } });
      await settle();
      expect(viewNotice(wrapper).exists()).toBe(false);
      expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(true);
      expect(toastMessages()).not.toContain(OPEN_FAILURE_COPY);
    } finally {
      wrapper.unmount();
    }
  });

  it("an unknown lineage falls back to the open-failure toast with no notice", async () => {
    api.getExamWorkspaceDocument.mockRejectedValue(outdatedError());
    const { wrapper } = await mountAtDocument(UNKNOWN_LINEAGE);
    try {
      expect(viewNotice(wrapper).exists()).toBe(false);
      expect(toastMessages()).toContain(OPEN_FAILURE_COPY);
    } finally {
      wrapper.unmount();
    }
  });
});
