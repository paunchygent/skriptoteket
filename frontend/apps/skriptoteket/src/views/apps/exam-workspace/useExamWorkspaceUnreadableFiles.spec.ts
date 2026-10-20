/**
 * Unreadable saved exams rows state (TASK-SKRIPT-41-02-06, U4).
 *
 * Expected behavior:
 *   Loading fills the rows; a failed load keeps the old rows and shows the
 *   saved-list failure toast once. Download saves the stored file unchanged
 *   under the server's file name, falling back to the row's name, and a
 *   failed download shows S6 without downloading anything. Remove posts once
 *   to the vault delete, drops the row, shows S4 and reloads the list; a
 *   failed remove keeps the row and shows S5. Nothing is ever retried.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";
import { flushPromises } from "@vue/test-utils";

import type { ExamWorkspaceUnreadableDocument } from "../../../api/examWorkspaceUnreadableFiles";
import {
  downloadSavedExamFile,
  listUnreadableExamWorkspaceDocuments,
  removeSavedExamFile,
} from "../../../api/examWorkspaceUnreadableFiles";
import { useToastStore } from "../../../stores/toast";
import {
  EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_REMOVE_FAILURE_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVED_COPY,
} from "./examWorkspaceFileNoticeCopy";
import { LIST_FAILURE_COPY } from "./useExamWorkspaceSavedList";
import { useExamWorkspaceUnreadableFiles } from "./useExamWorkspaceUnreadableFiles";

vi.mock("../../../api/examWorkspaceUnreadableFiles", () => ({
  downloadSavedExamFile: vi.fn(),
  listUnreadableExamWorkspaceDocuments: vi.fn(),
  removeSavedExamFile: vi.fn(),
}));

const listMock = vi.mocked(listUnreadableExamWorkspaceDocuments);
const downloadMock = vi.mocked(downloadSavedExamFile);
const removeMock = vi.mocked(removeSavedExamFile);

const downloadFile = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("../../../utils/browserDownload", () => downloadFile);

function buildRow(overrides: Partial<ExamWorkspaceUnreadableDocument> = {}): ExamWorkspaceUnreadableDocument {
  return {
    lineage_id: "lineage-1",
    name: "Prov.provdokument.zip",
    saved_at: "2026-10-11T08:00:00Z",
    title: "Prov",
    vault_file_id: "vault-1",
    ...overrides,
  };
}

function mountState() {
  const scope = effectScope();
  const state = scope.run(() => useExamWorkspaceUnreadableFiles());
  if (!state) {
    throw new Error("expected the unreadable files state to be created");
  }
  return { scope, state };
}

function toastMessages(): Array<{ message: string; variant: string }> {
  return useToastStore().toasts.map((toast) => ({ message: toast.message, variant: toast.variant }));
}

describe("useExamWorkspaceUnreadableFiles", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("fills the rows on load", async () => {
    const rows = [buildRow(), buildRow({ lineage_id: "lineage-2", vault_file_id: "vault-2" })];
    listMock.mockResolvedValueOnce({ documents: rows });
    const { state, scope } = mountState();
    try {
      await state.load();
      await flushPromises();

      expect(state.files.value).toEqual(rows);
      expect(listMock).toHaveBeenCalledTimes(1);
      expect(toastMessages()).toEqual([]);
    } finally {
      scope.stop();
    }
  });

  it("shows the saved-list failure toast once when the load fails", async () => {
    const before = [buildRow()];
    listMock.mockResolvedValueOnce({ documents: before });
    listMock.mockRejectedValueOnce(new Error("nätet är nere"));
    const { state, scope } = mountState();
    try {
      await state.load();
      await state.load();
      await flushPromises();

      expect(state.files.value).toEqual(before);
      expect(listMock).toHaveBeenCalledTimes(2);
      expect(toastMessages()).toEqual([{ message: LIST_FAILURE_COPY, variant: "failure" }]);
    } finally {
      scope.stop();
    }
  });

  it("downloads the stored blob unchanged under the server file name", async () => {
    listMock.mockResolvedValue({ documents: [buildRow()] });
    const blob = new Blob(["provdokument"]);
    downloadMock.mockResolvedValueOnce({
      blob,
      contentType: "application/zip",
      filename: "Server.provdokument.zip",
    });
    const { state, scope } = mountState();
    try {
      await state.load();
      await state.download(state.files.value[0]);
      await flushPromises();

      expect(downloadMock).toHaveBeenCalledTimes(1);
      expect(downloadMock).toHaveBeenCalledWith("vault-1");
      expect(downloadFile.triggerBrowserDownload).toHaveBeenCalledTimes(1);
      expect(downloadFile.triggerBrowserDownload).toHaveBeenCalledWith(blob, "Server.provdokument.zip");
      expect(state.busyIds.value.size).toBe(0);
    } finally {
      scope.stop();
    }
  });

  it("falls back to the row name when the download response names no file", async () => {
    listMock.mockResolvedValue({ documents: [buildRow({ name: "Eget namn.provdokument.zip" })] });
    const blob = new Blob(["provdokument"]);
    downloadMock.mockResolvedValueOnce({ blob, contentType: "application/zip", filename: null });
    const { state, scope } = mountState();
    try {
      await state.load();
      await state.download(state.files.value[0]);
      await flushPromises();

      expect(downloadFile.triggerBrowserDownload).toHaveBeenCalledTimes(1);
      expect(downloadFile.triggerBrowserDownload).toHaveBeenCalledWith(
        blob,
        "Eget namn.provdokument.zip",
      );
    } finally {
      scope.stop();
    }
  });

  it("shows S6 and downloads nothing when the download fails", async () => {
    listMock.mockResolvedValue({ documents: [buildRow()] });
    downloadMock.mockRejectedValueOnce(new Error("nätet är nere"));
    const { state, scope } = mountState();
    try {
      await state.load();
      await state.download(state.files.value[0]);
      await flushPromises();

      expect(downloadFile.triggerBrowserDownload).not.toHaveBeenCalled();
      expect(toastMessages()).toEqual([
        { message: EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY, variant: "failure" },
      ]);
      expect(state.busyIds.value.size).toBe(0);
    } finally {
      scope.stop();
    }
  });

  it("removes the row once through the vault delete, shows S4 and reloads", async () => {
    const remaining = buildRow({ lineage_id: "lineage-2", vault_file_id: "vault-2" });
    listMock.mockResolvedValueOnce({ documents: [buildRow(), remaining] });
    listMock.mockResolvedValueOnce({ documents: [remaining] });
    removeMock.mockResolvedValueOnce({
      bytes: 4,
      created_at: "2026-10-11T08:00:00Z",
      id: "vault-1",
      is_missing_on_disk: false,
      name: "Prov.provdokument.zip",
      ref: "vault-file-ref",
    });
    const { state, scope } = mountState();
    try {
      await state.load();
      await state.remove(buildRow());
      await flushPromises();

      expect(removeMock).toHaveBeenCalledTimes(1);
      expect(removeMock).toHaveBeenCalledWith("vault-1");
      expect(state.files.value).toEqual([remaining]);
      expect(toastMessages()).toEqual([
        { message: EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVED_COPY, variant: "success" },
      ]);
      expect(listMock).toHaveBeenCalledTimes(2);
      expect(state.busyIds.value.size).toBe(0);
    } finally {
      scope.stop();
    }
  });

  it("keeps the row and shows S5 when the remove fails", async () => {
    const rows = [buildRow()];
    listMock.mockResolvedValue({ documents: rows });
    removeMock.mockRejectedValueOnce(new Error("nätet är nere"));
    const { state, scope } = mountState();
    try {
      await state.load();
      await state.remove(rows[0]);
      await flushPromises();

      expect(removeMock).toHaveBeenCalledTimes(1);
      expect(state.files.value).toEqual(rows);
      expect(toastMessages()).toEqual([
        { message: EXAM_WORKSPACE_FILE_NOTICE_REMOVE_FAILURE_COPY, variant: "failure" },
      ]);
      expect(listMock).toHaveBeenCalledTimes(1);
    } finally {
      scope.stop();
    }
  });

  it("runs row B's download while row A's download is pending", async () => {
    const rowA = buildRow();
    const rowB = buildRow({ lineage_id: "lineage-2", name: "Andra.provdokument.zip", vault_file_id: "vault-2" });
    let finishA!: (response: { blob: Blob; contentType: string | null; filename: string | null }) => void;
    const blobB = new Blob(["andra"]);
    downloadMock.mockReturnValueOnce(
      new Promise((resolve) => {
        finishA = resolve;
      }),
    );
    downloadMock.mockResolvedValueOnce({ blob: blobB, contentType: "application/zip", filename: "Andra.provdokument.zip" });
    const { state, scope } = mountState();
    try {
      const pendingA = state.download(rowA);
      await flushPromises();
      expect(downloadMock).toHaveBeenCalledTimes(1);
      expect(state.busyIds.value.has("lineage-1")).toBe(true);

      await state.download(rowB);
      await flushPromises();

      expect(downloadMock).toHaveBeenCalledTimes(2);
      expect(downloadMock).toHaveBeenNthCalledWith(2, "vault-2");
      expect(downloadFile.triggerBrowserDownload).toHaveBeenCalledWith(blobB, "Andra.provdokument.zip");

      finishA({ blob: new Blob(["provdokument"]), contentType: "application/zip", filename: "Prov.provdokument.zip" });
      await pendingA;
      await flushPromises();
      expect(state.busyIds.value.size).toBe(0);
    } finally {
      scope.stop();
    }
  });

  it("ignores a second download click on the busy row", async () => {
    const rowA = buildRow();
    let finishA!: (response: { blob: Blob; contentType: string | null; filename: string | null }) => void;
    downloadMock.mockReturnValueOnce(
      new Promise((resolve) => {
        finishA = resolve;
      }),
    );
    const { state, scope } = mountState();
    try {
      const pendingA = state.download(rowA);
      await flushPromises();
      expect(downloadMock).toHaveBeenCalledTimes(1);

      await state.download(rowA);
      await flushPromises();

      expect(downloadMock).toHaveBeenCalledTimes(1);

      finishA({ blob: new Blob(["provdokument"]), contentType: "application/zip", filename: "Prov.provdokument.zip" });
      await pendingA;
      await flushPromises();
      expect(state.busyIds.value.size).toBe(0);
    } finally {
      scope.stop();
    }
  });

  it("runs row B's remove while row A's remove is pending", async () => {
    const rowA = buildRow();
    const rowB = buildRow({ lineage_id: "lineage-2", vault_file_id: "vault-2" });
    listMock.mockResolvedValue({ documents: [] });
    let finishA!: (response: { bytes: number; created_at: string; id: string; is_missing_on_disk: boolean; name: string; ref: string }) => void;
    removeMock.mockReturnValueOnce(
      new Promise((resolve) => {
        finishA = resolve;
      }),
    );
    removeMock.mockResolvedValueOnce({
      bytes: 4,
      created_at: "2026-10-11T08:00:00Z",
      id: "vault-2",
      is_missing_on_disk: false,
      name: "Andra.provdokument.zip",
      ref: "vault-file-ref-2",
    });
    const { state, scope } = mountState();
    try {
      const pendingA = state.remove(rowA);
      await flushPromises();
      expect(removeMock).toHaveBeenCalledTimes(1);
      expect(state.busyIds.value.has("lineage-1")).toBe(true);

      await state.remove(rowB);
      await flushPromises();

      expect(removeMock).toHaveBeenCalledTimes(2);
      expect(removeMock).toHaveBeenNthCalledWith(2, "vault-2");

      finishA({
        bytes: 4,
        created_at: "2026-10-11T08:00:00Z",
        id: "vault-1",
        is_missing_on_disk: false,
        name: "Prov.provdokument.zip",
        ref: "vault-file-ref",
      });
      await pendingA;
      await flushPromises();
      expect(state.busyIds.value.size).toBe(0);
    } finally {
      scope.stop();
    }
  });

  it("drops an older reload that arrives after both removes", async () => {
    const rowA = buildRow();
    const rowB = buildRow({ lineage_id: "lineage-2", vault_file_id: "vault-2" });
    listMock.mockResolvedValueOnce({ documents: [rowA, rowB] });
    let releaseOld!: (response: { documents: ExamWorkspaceUnreadableDocument[] }) => void;
    listMock.mockReturnValueOnce(
      new Promise((resolve) => {
        releaseOld = resolve;
      }),
    );
    listMock.mockResolvedValueOnce({ documents: [] });
    removeMock.mockResolvedValue({
      bytes: 4,
      created_at: "2026-10-11T08:00:00Z",
      id: "vault-1",
      is_missing_on_disk: false,
      name: "Prov.provdokument.zip",
      ref: "vault-file-ref",
    });
    const { state, scope } = mountState();
    try {
      await state.load();
      const pendingA = state.remove(rowA);
      await flushPromises();
      await state.remove(rowB);
      await flushPromises();

      expect(state.files.value).toEqual([]);

      releaseOld({ documents: [rowB] });
      await pendingA;
      await flushPromises();

      expect(state.files.value).toEqual([]);
    } finally {
      scope.stop();
    }
  });

  it("keeps a removed row out of a reload that started before the removal", async () => {
    const rowA = buildRow();
    const rowB = buildRow({ lineage_id: "lineage-2", vault_file_id: "vault-2" });
    listMock.mockResolvedValueOnce({ documents: [rowA, rowB] });
    let releaseStale!: (response: { documents: ExamWorkspaceUnreadableDocument[] }) => void;
    listMock.mockReturnValueOnce(
      new Promise((resolve) => {
        releaseStale = resolve;
      }),
    );
    listMock.mockResolvedValueOnce({ documents: [rowB] });
    removeMock.mockResolvedValueOnce({
      bytes: 4,
      created_at: "2026-10-11T08:00:00Z",
      id: "vault-1",
      is_missing_on_disk: false,
      name: "Prov.provdokument.zip",
      ref: "vault-file-ref",
    });
    const { state, scope } = mountState();
    try {
      await state.load();
      const staleLoad = state.load();
      await flushPromises();
      await state.remove(rowA);
      await flushPromises();

      expect(state.files.value).toEqual([rowB]);

      releaseStale({ documents: [rowA, rowB] });
      await staleLoad;
      await flushPromises();

      expect(state.files.value).toEqual([rowB]);
    } finally {
      scope.stop();
    }
  });
});
