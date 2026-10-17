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

const api = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamCourseCatalog: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
const rename = vi.hoisted(() => vi.fn());
vi.mock("../../api/examWorkspace", () => ({ ...api, EXAM_PARENT_DELETE_READY: false }));
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
async function openMetadata(wrapper: ViewWrapper) {
  await wrapper.get('[data-test="exam-workspace-summary-title"]').trigger("click");
}

beforeEach(() => {
  for (const mock of Object.values(api)) mock.mockReset();
  rename.mockReset();
  api.getExamCourseCatalog.mockResolvedValue({ courses: [] });
  api.getExamWorkspaceDocument.mockResolvedValue(response());
  api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
});
afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount();
  vi.useRealTimers();
});

describe("ExamWorkspaceView metadata", () => {
  it("edits the title without renaming and saves it with the document revision", async () => {
    const wrapper = await openWorkspace();
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
    await openMetadata(wrapper);
    await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue("Vattnets kretslopp – slutprov");
    expect(wrapper.get('[data-test="exam-workspace-dirty-pill"]').text()).toContain("Osparat");
    expect(api.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(rename).not.toHaveBeenCalled();
    api.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2, title: "Vattnets kretslopp – slutprov" }));
    await saveDocument(wrapper);
    expect(api.saveExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1", expect.objectContaining({
      expectedRevision: 1,
      document: expect.objectContaining({ title: "Vattnets kretslopp – slutprov", revision: 2 }),
    }));
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
  });

  it("keeps blank title input local and refuses to send it, then recovers after correction", async () => {
    const wrapper = await openWorkspace();
    await openMetadata(wrapper);
    const title = wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-title"]');
    await title.setValue("");
    expect(title.element.value).toBe("");
    expect(title.attributes("aria-invalid")).toBe("true");
    await saveDocument(wrapper);
    expect(api.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    await title.setValue("   ");
    await saveDocument(wrapper);
    expect(api.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    await title.setValue("Korrigerad titel");
    api.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2, title: "Korrigerad titel" }));
    await saveDocument(wrapper);
    expect(api.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("never opens item details and document metadata together, in either direction", async () => {
    const wrapper = await openWorkspace();
    const details = wrapper.get('[data-test="exam-workspace-item-details-toggle"]');
    await details.trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-item-drawer-frame"]').exists()).toBe(true);
    await openMetadata(wrapper);
    expect(wrapper.find('[data-test="exam-workspace-item-drawer-frame"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-metadata-drawer-frame"]').exists()).toBe(true);
    await details.trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-metadata-drawer-frame"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-item-drawer-frame"]').exists()).toBe(true);
  });

  it("keeps a pending rename alive after closing the drawer and serializes document writes", async () => {
    const wrapper = await openWorkspace();
    await openMetadata(wrapper);
    await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue("Osparad titel");
    let finish!: (value: unknown) => void;
    rename.mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("Efter stängning");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-metadata-drawer-close"]').trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-metadata-drawer-frame"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-save"]').attributes("disabled")).toBeDefined();
    await saveDocument(wrapper);
    expect(api.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    finish({ file: { name: "Efter stängning.provdokument.zip" }, renamed_file_ids: ["vault-head-7"] });
    await flushPromises();
    await openMetadata(wrapper);
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("Efter stängning");
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-title"]').element.value)
      .toBe("Osparad titel");
    expect(wrapper.get('[data-test="exam-workspace-save"]').attributes("disabled")).toBeUndefined();
  });

  it("retains a rejected rename after close, notifies the teacher and retries the rejected stem", async () => {
    const wrapper = await openWorkspace();
    await openMetadata(wrapper);
    let reject!: (reason: unknown) => void;
    rename.mockReturnValueOnce(new Promise((_, fail) => { reject = fail; }));
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("Upptaget namn");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-metadata-drawer-close"]').trigger("click");
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
    api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [other.summary] });
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
    expect(wrapper.get('[data-test="exam-workspace-summary-version"]').text()).toContain("2");
    await wrapper.get('[data-test="exam-workspace-metadata-drawer-close"]').trigger("click");
    await openMetadata(wrapper);
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("Nytt namn");
    await wrapper.get('[data-test="exam-workspace-metadata-drawer-close"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");
    api.getExamWorkspaceDocument.mockResolvedValueOnce(other);
    await wrapper.get('[data-test="exam-workspace-open-lineage-2"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");
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
    await wrapper.get('[data-test="exam-workspace-metadata-drawer-close"]').trigger("click");
    await openMetadata(wrapper);
    expect(wrapper.get<HTMLInputElement>('[data-test="exam-workspace-metadata-name"]').element.value)
      .toBe("Senare namn");
  });

  it("renames the vault head independently of the title and shows it in the saved exam list", async () => {
    const other = buildResponse({ version: 1, title: "Annat prov" });
    other.summary.lineage_id = "lineage-2";
    other.summary.vault_file_id = "vault-other";
    api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [other.summary] });
    const wrapper = await openWorkspace();
    await openMetadata(wrapper);
    rename.mockResolvedValue({ file: { name: "NO nytt.provdokument.zip" }, renamed_file_ids: ["vault-head-7", "vault-old-2"] });
    await wrapper.get('[data-test="exam-workspace-metadata-name"]').setValue("NO nytt");
    await wrapper.get('[data-test="exam-workspace-metadata-rename"]').trigger("click");
    await flushPromises();
    expect(rename).toHaveBeenCalledWith("vault-head-7", "NO nytt");
    expect(wrapper.get('[data-test="exam-workspace-summary-title"]').text()).toBe("NO-prov HT25");
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
    expect(api.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    await wrapper.get('[data-test="exam-workspace-metadata-drawer-close"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");
    api.getExamWorkspaceDocument.mockResolvedValueOnce(other);
    await wrapper.get('[data-test="exam-workspace-open-lineage-2"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-open-lineage-1"]').text()).toContain("NO nytt");
    expect(wrapper.get('[data-test="exam-workspace-open-lineage-1"]').text()).not.toContain("NO original");
  });
});
