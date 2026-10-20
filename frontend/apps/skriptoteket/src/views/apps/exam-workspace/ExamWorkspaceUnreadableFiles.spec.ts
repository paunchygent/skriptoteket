/**
 * Unreadable saved exams rows (TASK-SKRIPT-41-02-06, U4).
 *
 * Expected behavior:
 *   Each unreadable exam renders as a row that is not a button: the document
 *   glyph, the title, the saved date and the shared file notice below. A row
 *   click opens nothing and fetches nothing. The notice shows S1 with
 *   glyph-only download and remove named in tooltip and aria-label; while a
 *   row action runs that row's buttons are disabled. The component reports
 *   its row count after every load and remove.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Plugin } from "vue";

import type { ExamWorkspaceUnreadableDocument } from "../../../api/examWorkspaceUnreadableFiles";
import {
  downloadSavedExamFile,
  listUnreadableExamWorkspaceDocuments,
  removeSavedExamFile,
} from "../../../api/examWorkspaceUnreadableFiles";
import {
  EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVE_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY,
} from "./examWorkspaceFileNoticeCopy";
import { examWorkspaceDocumentLabel } from "./examWorkspaceRows";
import {
  EXAM_WORKSPACE_UNREADABLE_FILES_KEY,
  useExamWorkspaceUnreadableFiles,
} from "./useExamWorkspaceUnreadableFiles";
import ExamWorkspaceUnreadableFiles from "./ExamWorkspaceUnreadableFiles.vue";

vi.mock("../../../api/examWorkspaceUnreadableFiles", () => ({
  downloadSavedExamFile: vi.fn(),
  listUnreadableExamWorkspaceDocuments: vi.fn(),
  removeSavedExamFile: vi.fn(),
}));

const downloadFile = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("../../../utils/browserDownload", () => downloadFile);

const listMock = vi.mocked(listUnreadableExamWorkspaceDocuments);
const downloadMock = vi.mocked(downloadSavedExamFile);
const removeMock = vi.mocked(removeSavedExamFile);

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

function rowTestId(lineageId: string): string {
  return `[data-test="exam-workspace-unreadable-${lineageId}"]`;
}

async function mountRows(documents: ExamWorkspaceUnreadableDocument[]) {
  setActivePinia(createPinia());
  listMock.mockResolvedValue({ documents });
  const unreadable = useExamWorkspaceUnreadableFiles();
  const provideUnreadable: Plugin = {
    install(app) {
      app.provide(EXAM_WORKSPACE_UNREADABLE_FILES_KEY, unreadable);
    },
  };
  const wrapper = mount(ExamWorkspaceUnreadableFiles, {
    global: { plugins: [provideUnreadable] },
  });
  await flushPromises();
  return wrapper;
}

describe("ExamWorkspaceUnreadableFiles", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a row that is not a button with title, saved date and the S1 notice", async () => {
    const wrapper = await mountRows([buildRow()]);

    const row = wrapper.get(rowTestId("lineage-1"));
    expect(row.attributes("role")).toBeUndefined();
    expect(row.attributes("tabindex")).toBeUndefined();
    expect(row.classes()).toContain("file--unreadable");
    expect(row.text()).toContain("Prov");
    expect(row.text()).toContain("Sparad");
    expect(row.text()).toContain(examWorkspaceDocumentLabel("Prov.provdokument.zip"));
    expect(row.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY,
    );

    const download = row.get('[data-test="exam-workspace-file-notice-download"]');
    expect(download.attributes("title")).toBe(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME);
    expect(download.attributes("aria-label")).toBe(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME);
    expect(download.text().trim()).toBe("");
    const remove = row.get('[data-test="exam-workspace-file-notice-remove"]');
    expect(remove.attributes("title")).toBe(EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVE_NAME);
    expect(remove.attributes("aria-label")).toBe(EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVE_NAME);
    expect(remove.text().trim()).toBe("");
    wrapper.unmount();
  });

  it("does nothing when the row itself is clicked", async () => {
    const wrapper = await mountRows([buildRow()]);

    await wrapper.get(rowTestId("lineage-1")).trigger("click");
    await flushPromises();

    expect(wrapper.emitted("open")).toBeUndefined();
    expect(downloadMock).not.toHaveBeenCalled();
    expect(removeMock).not.toHaveBeenCalled();
    expect(listMock).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("disables the row buttons while its download runs", async () => {
    const wrapper = await mountRows([buildRow()]);
    let finish!: (response: { blob: Blob; contentType: string | null; filename: string | null }) => void;
    downloadMock.mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );

    const row = wrapper.get(rowTestId("lineage-1"));
    await row.get('[data-test="exam-workspace-file-notice-download"]').trigger("click");
    await flushPromises();

    const busyButtons = row.findAll("button");
    expect(busyButtons.length).toBeGreaterThan(0);
    for (const button of busyButtons) {
      expect(button.attributes("disabled")).toBeDefined();
    }

    finish({ blob: new Blob(["provdokument"]), contentType: "application/zip", filename: "Prov.provdokument.zip" });
    await flushPromises();
    for (const button of row.findAll("button")) {
      expect(button.attributes("disabled")).toBeUndefined();
    }
    wrapper.unmount();
  });

  it("reports its row count after the load and after a remove", async () => {
    const remaining = buildRow({ lineage_id: "lineage-2", vault_file_id: "vault-2" });
    setActivePinia(createPinia());
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
    const unreadable = useExamWorkspaceUnreadableFiles();
    const provideUnreadable: Plugin = {
      install(app) {
        app.provide(EXAM_WORKSPACE_UNREADABLE_FILES_KEY, unreadable);
      },
    };
    const wrapper = mount(ExamWorkspaceUnreadableFiles, {
      global: { plugins: [provideUnreadable] },
    });
    await flushPromises();
    expect(wrapper.emitted("count")).toEqual([[2]]);

    await wrapper
      .get(rowTestId("lineage-1"))
      .get('[data-test="exam-workspace-file-notice-remove"]')
      .trigger("click");
    await flushPromises();

    expect(removeMock).toHaveBeenCalledTimes(1);
    expect(wrapper.emitted("count")).toEqual([[2], [1]]);
    expect(wrapper.find(rowTestId("lineage-1")).exists()).toBe(false);
    expect(wrapper.find(rowTestId("lineage-2")).exists()).toBe(true);
    wrapper.unmount();
  });

  it("disables only the busy row while its download runs", async () => {
    const rowA = buildRow();
    const rowB = buildRow({ lineage_id: "lineage-2", vault_file_id: "vault-2" });
    const wrapper = await mountRows([rowA, rowB]);
    let finish!: (response: { blob: Blob; contentType: string | null; filename: string | null }) => void;
    downloadMock.mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );

    await wrapper
      .get(rowTestId("lineage-1"))
      .get('[data-test="exam-workspace-file-notice-download"]')
      .trigger("click");
    await flushPromises();

    const busyRow = wrapper.get(rowTestId("lineage-1"));
    const busyButtons = busyRow.findAll("button");
    expect(busyButtons.length).toBeGreaterThan(0);
    for (const button of busyButtons) {
      expect(button.attributes("disabled")).toBeDefined();
    }
    const idleRow = wrapper.get(rowTestId("lineage-2"));
    const idleButtons = idleRow.findAll("button");
    expect(idleButtons.length).toBeGreaterThan(0);
    for (const button of idleButtons) {
      expect(button.attributes("disabled")).toBeUndefined();
    }

    finish({ blob: new Blob(["provdokument"]), contentType: "application/zip", filename: "Prov.provdokument.zip" });
    await flushPromises();
    for (const button of wrapper.get(rowTestId("lineage-1")).findAll("button")) {
      expect(button.attributes("disabled")).toBeUndefined();
    }
    wrapper.unmount();
  });

  it("stacks each row notice above its glyph actions in the narrow drawer", async () => {
    const rowB = buildRow({ lineage_id: "lineage-2", vault_file_id: "vault-2" });
    const wrapper = await mountRows([buildRow(), rowB]);

    for (const lineageId of ["lineage-1", "lineage-2"]) {
      const row = wrapper.get(rowTestId(lineageId));
      expect(row.element.children).toHaveLength(2);
      expect(row.get('[data-test="exam-workspace-file-notice"]').classes()).toContain(
        "xw-notice--stack",
      );
    }
    wrapper.unmount();
  });
});
