/** Background conversion behavior at the real workspace view boundary. */
import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceConversionStatus } from "../../api/examWorkspace";
import { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./exam-workspace/useExamWorkspaceDocument";
import { buildResponse, importFixtureDocument, mountExamWorkspace } from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

function status(state: ExamWorkspaceConversionStatus["state"], error_message: string | null = null): ExamWorkspaceConversionStatus {
  return {
    job_id: "job-1", lineage_id: "lineage-1", state, error_message, summary: null,
    document_revision: state === "succeeded" ? 1 : null, questions_total: 0, questions_done: 0, units: [],
  };
}

let wrapper: Awaited<ReturnType<typeof mountExamWorkspace>>["wrapper"] | undefined;

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  for (const mock of Object.values(apiMocks)) mock.mockReset();
  apiMocks.importExamWorkspaceDocument.mockResolvedValue(status("queued"));
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(status("queued"));
  apiMocks.getExamWorkspaceDocument.mockResolvedValue(
    buildResponse({ conversion: status("succeeded"), version: 1 }),
  );
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
  vi.useRealTimers();
});

async function upload() {
  const mounted = await mountExamWorkspace();
  wrapper = mounted.wrapper;
  await importFixtureDocument(wrapper);
  return mounted;
}
async function tick(ms = EXAM_WORKSPACE_CONVERSION_POLL_MS) {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

describe("Exam workspace background conversion", () => {
  it("keeps the shell through queued and running, then reads and opens the native exam", async () => {
    const mounted = await mountExamWorkspace();
    wrapper = mounted.wrapper;
    const frame = wrapper.get('[data-test="exam-workspace-frame"]').element;
    const toolbar = wrapper.get('[data-test="exam-workspace-toolbar"]').element;
    await importFixtureDocument(wrapper);
    expect(wrapper.get('[data-test="exam-workspace-conversion-status"]').text()).toContain("Konverterar provet …");
    expect(wrapper.get('[data-test="exam-workspace-source-file-input"]').attributes("disabled")).toBeDefined();
    expect(apiMocks.getExamWorkspaceDocument).not.toHaveBeenCalled();
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("running"));
    await tick();
    expect(wrapper.text()).toContain("Konverterar provet …");
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("succeeded"));
    await tick();
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledExactlyOnceWith("lineage-1");
    expect(wrapper.get('[data-test="exam-workspace-summary-title"]').text()).toBe("NO-prov HT25");
    expect(mounted.router.currentRoute.value.query.document).toBe("lineage-1");
    expect(wrapper.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-frame"]').element).toBe(frame);
    expect(wrapper.get('[data-test="exam-workspace-toolbar"]').element).toBe(toolbar);
    const polls = apiMocks.getExamWorkspaceConversionStatus.mock.calls.length;
    await tick(30_000);
    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(polls);
  });

  it("shows a Swedish job failure and allows a fresh upload to recover", async () => {
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("failed", "Provfilen kunde inte läsas."));
    const { wrapper: view } = await upload();
    expect(view.get('[data-test="exam-workspace-conversion-status"]').text()).toContain("Provfilen kunde inte läsas.");
    expect(view.get('[data-test="exam-workspace-source-file-input"]').attributes("disabled")).toBeUndefined();
    expect(apiMocks.getExamWorkspaceDocument).not.toHaveBeenCalled();
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("succeeded"));
    await importFixtureDocument(view);
    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(view.find('[data-test="exam-workspace-item-editor"]').exists()).toBe(true);
  });

  it("preserves the old exam and disables editing, saving and proposals during conversion", async () => {
    const mounted = await mountExamWorkspace({ document: "lineage-1" });
    wrapper = mounted.wrapper;
    const title = wrapper.get('[data-test="exam-workspace-summary-title"]').text();
    await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");
    await importFixtureDocument(wrapper);
    expect(wrapper.get('[data-test="exam-workspace-summary-title"]').text()).toBe(title);
    expect(wrapper.get('[data-test="exam-workspace-save"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-enrichment-request"]').attributes("disabled")).toBeDefined();
    await wrapper.get('[data-test="exam-workspace-mode-redigera"]').trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-item-points-input"]').attributes("disabled")).toBeDefined();
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("failed", "Konverteringen misslyckades."));
    await tick();
    expect(wrapper.get('[data-test="exam-workspace-summary-title"]').text()).toBe(title);
    expect(wrapper.get('[data-test="exam-workspace-item-points-input"]').attributes("disabled")).toBeUndefined();
  });

  it("retains conversion on status-read errors and recovers using the visible retry", async () => {
    apiMocks.getExamWorkspaceConversionStatus.mockRejectedValueOnce(new Error("network"));
    const { wrapper: view } = await upload();
    expect(view.text()).toContain("Konverterar provet …");
    expect(view.find('[data-test="exam-workspace-conversion-retry"]').exists()).toBe(true);
    expect(apiMocks.getExamWorkspaceDocument).not.toHaveBeenCalled();
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("succeeded"));
    await view.get('[data-test="exam-workspace-conversion-retry"]').trigger("click");
    await flushPromises();
    expect(view.find('[data-test="exam-workspace-item-editor"]').exists()).toBe(true);
    expect(view.find('[data-test="exam-workspace-conversion-retry"]').exists()).toBe(false);
  });

  it("automatically retries transient polling failures with backoff", async () => {
    apiMocks.getExamWorkspaceConversionStatus.mockRejectedValueOnce(new Error("offline")).mockRejectedValueOnce(new Error("offline"));
    await upload();
    await tick();
    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(2);
    await tick();
    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(2);
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("succeeded"));
    await tick();
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("retries completed document readback without re-uploading or falsely finishing", async () => {
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("succeeded"));
    apiMocks.getExamWorkspaceDocument.mockRejectedValueOnce(new Error("network"));
    const { wrapper: view } = await upload();
    expect(view.text()).toContain("Konverterar provet …");
    expect(view.find('[data-test="exam-workspace-item-editor"]').exists()).toBe(false);
    await tick();
    expect(view.find('[data-test="exam-workspace-item-editor"]').exists()).toBe(true);
    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(1);
  });

  it("cancels scheduled polling when the view unmounts", async () => {
    await upload();
    wrapper?.unmount();
    wrapper = undefined;
    await tick(30_000);
    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(1);
    expect(apiMocks.getExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("ignores an in-flight status response after unmount", async () => {
    let resolveStatus!: (value: ExamWorkspaceConversionStatus) => void;
    apiMocks.getExamWorkspaceConversionStatus.mockReturnValueOnce(new Promise((resolve) => { resolveStatus = resolve; }));
    await upload();
    wrapper?.unmount();
    wrapper = undefined;
    resolveStatus(status("succeeded"));
    await flushPromises();
    await tick(30_000);
    expect(apiMocks.getExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(1);
  });
});
