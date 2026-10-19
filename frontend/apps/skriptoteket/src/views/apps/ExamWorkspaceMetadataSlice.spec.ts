/** Title saves and immediate vault renames through the real workspace view. */
import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { useToastStore } from "../../stores/toast";
import { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./exam-workspace/useExamWorkspaceDocument";
import {
  buildResponse,
  mountExamWorkspace,
  saveDocument,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";
import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

const api = vi.hoisted(() => ({
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamCourseCatalog: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));
const rename = vi.hoisted(() => vi.fn());
vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", () => ({ ...api }));
vi.mock("../../api/vault", () => ({ renameVaultFile: rename }));
const wrappers: ViewWrapper[] = [];

function response() {
  const result = buildResponse({ version: 1 });
  result.summary.name = "NO original.provdokument.zip";
  result.summary.vault_file_id = "vault-head-7";
  return result;
}
async function openWorkspace() {
  const mounted = await mountExamWorkspace({ document: "lineage-1" }, "desktop", document.body);
  wrappers.push(mounted.wrapper);
  return mounted.wrapper;
}
/** Open Provets uppgifter through the header title; the title button toggles the drawer. */
async function openMetadata(wrapper: ViewWrapper) {
  if (!wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()) {
    await wrapper.get('[data-test="exam-workspace-title"]').trigger("click");
  }
  expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(true);
}
async function closeMetadata(wrapper: ViewWrapper) {
  await wrapper.get('[data-test="exam-workspace-drawer-close"]').trigger("click");
  expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(false);
}
/** Show the Öppna drawer (it stays open on desktop after an exam opens, so only toggle when closed). */
async function showSavedDocuments(wrapper: ViewWrapper) {
  if (!wrapper.find('[data-test="exam-workspace-saved-documents"]').exists()) {
    await wrapper.get('[data-test="exam-workspace-open"]').trigger("click");
  }
  expect(wrapper.find('[data-test="exam-workspace-saved-documents"]').exists()).toBe(true);
}
/** The header's save state: "Sparar …" while an edit is pending, otherwise "Sparat …". */
function saveState(wrapper: ViewWrapper): string {
  return wrapper.get('[data-test="exam-workspace-save-state"]').text();
}

beforeEach(() => {
  for (const mock of [...Object.values(api), ...Object.values(exportApiMocks)]) mock.mockReset();
  rename.mockReset();
  arrangeStepHistory(api);
  api.getExamCourseCatalog.mockResolvedValue({ courses: [] });
  api.getExamWorkspaceDocument.mockResolvedValue(response());
  api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
});
afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount();
  vi.useRealTimers();
});

describe("ExamWorkspaceView metadata", () => {
  it("edits the title without renaming and stores it as a step", async () => {
    const wrapper = await openWorkspace();
    expect(saveState(wrapper)).toBe("Sparat");
    await openMetadata(wrapper);
    await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue("Vattnets kretslopp – slutprov");
    expect(saveState(wrapper)).toBe("Sparar …");
    expect(api.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(rename).not.toHaveBeenCalled();
    await saveDocument(wrapper);
    const stores = api.storeExamWorkspaceUndoStep.mock.calls;
    expect(stores).toHaveLength(1);
    expect(stores[0]![1].document.title).toBe("Vattnets kretslopp – slutprov");
    expect(saveState(wrapper)).toMatch(/^Sparat /);
  });

  it("stores a blank title, keeps the guidance line, and recovers after correction", async () => {
    const wrapper = await openWorkspace();
    await openMetadata(wrapper);
    const title = wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-title"]');
    await title.setValue("");
    expect(title.element.value).toBe("");
    expect(title.attributes("aria-invalid")).toBe("true");
    await saveDocument(wrapper);
    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    expect(api.storeExamWorkspaceUndoStep.mock.calls[0]?.[1].document.title).toBe("");
    await title.setValue("Korrigerad titel");
    await saveDocument(wrapper);
    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
    expect(api.storeExamWorkspaceUndoStep.mock.calls[1]?.[1].document.title).toBe("Korrigerad titel");
    expect(title.attributes("aria-invalid")).toBeUndefined();
  });

  it("shows one drawer at a time: Öppna and Provets uppgifter replace each other", async () => {
    const wrapper = await openWorkspace();
    await showSavedDocuments(wrapper);
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(false);
    await openMetadata(wrapper);
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(true);
    await wrapper.get('[data-test="exam-workspace-open"]').trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(true);
  });

  it("keeps a pending rename alive after closing the drawer and serializes document writes", async () => {
    const wrapper = await openWorkspace();
    await openMetadata(wrapper);
    await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue("Osparad titel");
    let finish!: (value: unknown) => void;
    rename.mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("Efter stängning");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-drawer-close"]').trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-save-menu"]').attributes("disabled")).toBeDefined();
    await saveDocument(wrapper);
    expect(api.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    finish({ file: { name: "Efter stängning.provdokument.zip" }, renamed_file_ids: ["vault-head-7"] });
    await flushPromises();
    await openMetadata(wrapper);
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("Efter stängning");
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-title"]').element.value)
      .toBe("Osparad titel");
    expect(wrapper.get('[data-test="exam-workspace-save-menu"]').attributes("disabled")).toBeUndefined();
  });

  it("retains a rejected rename after close, notifies the teacher and retries the rejected stem", async () => {
    const wrapper = await openWorkspace();
    await openMetadata(wrapper);
    let reject!: (reason: unknown) => void;
    rename.mockReturnValueOnce(new Promise((_, fail) => { reject = fail; }));
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("Upptaget namn");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-drawer-close"]').trigger("click");
    const message = "En annan fil heter redan Upptaget namn.provdokument.zip.";
    reject(new ApiError({ code: "validation_error", status: 400, message }));
    await flushPromises();
    expect(useToastStore().failure).toHaveBeenCalledWith(message);
    await openMetadata(wrapper);
    expect(wrapper.get('[data-test="exam-workspace-metadata-name-error"]').text()).toBe(message);
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("Upptaget namn");
    rename.mockResolvedValueOnce({ file: { name: "Upptaget namn.provdokument.zip" } });
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await flushPromises();
    expect(rename).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-test="exam-workspace-metadata-name-error"]').exists()).toBe(false);
  });

  it.each(["read-first", "rename-first"] as const)(
    "keeps the successful name and newer head when overlapping responses finish %s", async (order) => {
    vi.useFakeTimers();
    const conversion = {
      job_id: "job-1", lineage_id: "lineage-1", state: "running" as const,
      error_message: null, summary: null, document_revision: 1, questions_total: 8, questions_done: 1,
      units: [{ unit_id: "unit-1", question: true, state: "converting" as const, item_ids: ["item_001"] }],
    };
    const first = buildResponse({ version: 1, conversion });
    first.summary.name = "Original.provdokument.zip";
    first.summary.vault_file_id = "head-1";
    api.getExamWorkspaceDocument.mockResolvedValueOnce(first);
    const other = buildResponse({ version: 1 });
    other.summary.lineage_id = "lineage-2";
    api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [other.summary], ordering: "course" });
    const wrapper = await openWorkspace();
    const nextConversion = { ...conversion, document_revision: 2, questions_done: 2 };
    const next = buildResponse({ version: 2, conversion: nextConversion });
    next.summary.name = "Original.provdokument.zip";
    next.summary.vault_file_id = "head-2";
    let finishRead!: (value: unknown) => void;
    api.getExamWorkspaceConversionStatus.mockResolvedValue(nextConversion);
    api.getExamWorkspaceDocument.mockReturnValueOnce(new Promise((resolve) => { finishRead = resolve; }));
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_CONVERSION_POLL_MS);
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    await openMetadata(wrapper);
    let finishRename!: (value: unknown) => void;
    rename.mockReturnValueOnce(new Promise((resolve) => { finishRename = resolve; }));
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("Nytt namn");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    expect(rename).toHaveBeenCalledWith("head-1", "Nytt namn");
    const completeRead = () => finishRead(next);
    const completeRename = () => finishRename({
      file: { name: "Nytt namn.provdokument.zip" }, renamed_file_ids: ["head-1", "head-2"],
    });
    const completions = order === "read-first"
      ? [completeRead, completeRename] : [completeRename, completeRead];
    for (const complete of completions) {
      complete();
      await flushPromises();
    }
    await wrapper.get('[data-test="exam-workspace-drawer-close"]').trigger("click");
    await openMetadata(wrapper);
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("Nytt namn");
    // The newer head is kept: the next store sends the revision-2 copy with the new title.
    await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue("Titel på ny version");
    await saveDocument(wrapper);
    await closeMetadata(wrapper);
    const stores = api.storeExamWorkspaceUndoStep.mock.calls;
    const saved = stores[stores.length - 1]![1].document;
    expect(saved.revision).toBe(2);
    expect(saved.title).toBe("Titel på ny version");
    await openMetadata(wrapper);
    await wrapper.get('[data-test="exam-workspace-drawer-close"]').trigger("click");
    await showSavedDocuments(wrapper);
    api.getExamWorkspaceDocument.mockResolvedValueOnce(other);
    await wrapper.get('[data-test="exam-workspace-open-lineage-2"]').trigger("click");
    await flushPromises();
    await showSavedDocuments(wrapper);
    expect(wrapper.get('[data-test="exam-workspace-open-lineage-1"]').text()).toContain("Nytt namn");
    expect(wrapper.get('[data-test="exam-workspace-open-lineage-1"]').text()).not.toContain("Original");
    // A request begun after rename completion must accept a new authoritative name.
    const authoritative = buildResponse({ version: 2 });
    authoritative.summary.name = "Serverns namn.provdokument.zip";
    authoritative.summary.vault_file_id = "head-2";
    api.getExamWorkspaceDocument.mockResolvedValueOnce(authoritative);
    await wrapper.get('[data-test="exam-workspace-open-lineage-1"]').trigger("click");
    await flushPromises();
    await openMetadata(wrapper);
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("Serverns namn");
    rename.mockResolvedValueOnce({ file: { name: "Senare namn.provdokument.zip" } });
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("Senare namn");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await flushPromises();
    expect(rename).toHaveBeenLastCalledWith("head-2", "Senare namn");
    await wrapper.get('[data-test="exam-workspace-drawer-close"]').trigger("click");
    await openMetadata(wrapper);
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("Senare namn");
  });

  it("renames the vault head independently of the title and shows it in the saved exam list", async () => {
    const other = buildResponse({ version: 1, title: "Annat prov" });
    other.summary.lineage_id = "lineage-2";
    other.summary.vault_file_id = "vault-other";
    api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [other.summary], ordering: "course" });
    const wrapper = await openWorkspace();
    await openMetadata(wrapper);
    rename.mockResolvedValue({ file: { name: "NO nytt.provdokument.zip" }, renamed_file_ids: ["vault-head-7", "vault-old-2"] });
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("NO nytt");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await flushPromises();
    expect(rename).toHaveBeenCalledWith("vault-head-7", "NO nytt");
    // A successful rename reports through the new file name, not a toast.
    const toasts = useToastStore();
    expect(toasts.success).not.toHaveBeenCalled();
    expect(toasts.info).not.toHaveBeenCalled();
    expect(toasts.failure).not.toHaveBeenCalled();
    expect(wrapper.get('[data-test="exam-workspace-title"]').text()).toBe("NO-prov HT25");
    expect(saveState(wrapper)).toBe("Sparat");
    expect(api.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    await wrapper.get('[data-test="exam-workspace-drawer-close"]').trigger("click");
    await showSavedDocuments(wrapper);
    api.getExamWorkspaceDocument.mockResolvedValueOnce(other);
    await wrapper.get('[data-test="exam-workspace-open-lineage-2"]').trigger("click");
    await flushPromises();
    await showSavedDocuments(wrapper);
    expect(wrapper.get('[data-test="exam-workspace-open-lineage-1"]').text()).toContain("NO nytt");
    expect(wrapper.get('[data-test="exam-workspace-open-lineage-1"]').text()).not.toContain("NO original");
  });
});
