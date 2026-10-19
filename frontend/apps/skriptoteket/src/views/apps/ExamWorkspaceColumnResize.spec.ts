/**
 * Exam workspace column resize wiring (TASK-SKRIPT-41-02-04, ew-splitter-wiring).
 *
 * Expected behavior:
 *   On desktop the question list carries a resize handle on its right edge
 *   and a collapse glyph; the open drawer and the teacher's print preview
 *   each carry a resize handle on their left edge. Dragged widths and the
 *   collapsed list persist per browser through
 *   `skriptoteket.exam-workspace.columns` and appear as inline custom
 *   properties on the workspace root. The collapse glyph swaps the list for
 *   a 44 px rail with an expand glyph; Enter on the list handle collapses
 *   and restores, Enter on a side handle closes its panel, and a
 *   double-click resets the stored width. Tablet and phone render no
 *   handles, no collapse glyph and no rail. A throwing storage still renders
 *   the workspace at defaults with no inline width.
 *
 * Relationships:
 *   - Mounts `ExamWorkspaceView` through the shared slice harness with a
 *     provided layout, so no media queries are involved.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceConversionStatus, NativeExamDocument } from "../../api/examWorkspace";
import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";
import { EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY } from "./exam-workspace/examWorkspaceColumnSizesStorage";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamWorkspaceDocument: apiMocks.getExamWorkspaceDocument,
  getExamWorkspaceConversionStatus: apiMocks.getExamWorkspaceConversionStatus,
  importExamWorkspaceDocument: apiMocks.importExamWorkspaceDocument,
  listExamWorkspaceDocuments: apiMocks.listExamWorkspaceDocuments,
  saveExamWorkspaceDocument: apiMocks.saveExamWorkspaceDocument,
  findExamWorkspaceAnswerKeySuggestions: apiMocks.findExamWorkspaceAnswerKeySuggestions,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const mounted: Array<{ unmount: () => void }> = [];

/** Resolved desktop tracks [list, editor, side] for the handle bounds read. */
const GRID = "260px 700px 320px";

function stubGridTracks(): void {
  vi.spyOn(window, "getComputedStyle").mockReturnValue({
    gridTemplateColumns: GRID,
  } as CSSStyleDeclaration);
}

async function mountImported(layout: ExamWorkspaceLayout): Promise<ViewWrapper> {
  const slot = globalThis.document.createElement("div");
  slot.id = "app-topbar-page-slot";
  globalThis.document.body.append(slot);
  const host = globalThis.document.createElement("div");
  globalThis.document.body.append(host);
  const mountedWorkspace = await mountExamWorkspace({}, layout, host);
  mounted.push(mountedWorkspace.wrapper);
  await importFixtureDocument(mountedWorkspace.wrapper);
  return mountedWorkspace.wrapper;
}

function frameOf(wrapper: ViewWrapper): HTMLElement {
  return wrapper.get('[data-test="exam-workspace-frame"]').element as HTMLElement;
}

/** The finished import: its poll status, and the conversion its fetched document carries. */
const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  globalThis.document.body.replaceChildren();
  vi.restoreAllMocks();
});

beforeEach(() => {
  localStorage.clear();
  for (const mock of [...Object.values(apiMocks), ...Object.values(exportApiMocks)]) {
    mock.mockReset();
  }
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    const response = buildResponse({ conversion: succeededConversion, version: 1 });
    const document: NativeExamDocument = {
      ...response.document,
      items: response.document.items.map((item) =>
        item.item_id === "item_004"
          ? { ...item, answer_key: { ...item.answer_key, origin: "source_provided" } }
          : item,
      ),
    };
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce({
      ...response,
      document,
      saved_document: document,
    });
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
});

describe("ExamWorkspaceView column resize wiring", () => {
  it("renders the list handle on desktop with a drawer open", async () => {
    const wrapper = await mountImported("desktop");

    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-column-handle-list"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-column-handle-side"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-list-collapse"]').exists()).toBe(true);
  });

  it("renders the side handle with a teacher preview open on desktop", async () => {
    const wrapper = await mountImported("desktop");

    await wrapper.get('[data-test="exam-workspace-print-preview-toggle"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-print-preview"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-column-handle-side"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-column-handle-list"]').exists()).toBe(true);
  });

  it("renders no handle, collapse glyph or rail on tablet and phone", async () => {
    for (const layout of ["tablet", "phone"] as const) {
      const wrapper = await mountImported(layout);

      expect(wrapper.find('[data-test="exam-workspace-column-handle-list"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="exam-workspace-column-handle-side"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="exam-workspace-list-collapse"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="exam-workspace-list-expand"]').exists()).toBe(false);
      expect(frameOf(wrapper).dataset["list"]).toBeUndefined();
    }
  });

  it("applies stored widths as inline custom properties on mount", async () => {
    localStorage.setItem(
      EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY,
      JSON.stringify({ drawer: 340, list: 300 }),
    );

    const wrapper = await mountImported("desktop");
    const frame = frameOf(wrapper);

    expect(frame.style.getPropertyValue("--xw-list-size")).toBe("300px");
    expect(frame.style.getPropertyValue("--xw-drawer-size")).toBe("340px");
  });

  it("collapses the list to a rail with the expand glyph and restores it", async () => {
    const wrapper = await mountImported("desktop");

    await wrapper.get('[data-test="exam-workspace-list-collapse"]').trigger("click");

    expect(frameOf(wrapper).dataset["list"]).toBe("collapsed");
    expect(wrapper.find('[data-test="exam-workspace-list-expand"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-list-collapse"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-list-expand"]').trigger("click");

    expect(frameOf(wrapper).dataset["list"]).toBe("open");
    expect(wrapper.find('[data-test="exam-workspace-list-collapse"]').exists()).toBe(true);
  });

  it("toggles collapse with Enter on the list handle", async () => {
    stubGridTracks();
    const wrapper = await mountImported("desktop");
    const handle = () => wrapper.get('[data-test="exam-workspace-column-handle-list"]');

    await handle().trigger("keydown", { key: "Enter" });
    expect(frameOf(wrapper).dataset["list"]).toBe("collapsed");

    await handle().trigger("keydown", { key: "Enter" });
    expect(frameOf(wrapper).dataset["list"]).toBe("open");
  });

  it("persists a set from the handle and removes the stored width on double-click", async () => {
    stubGridTracks();
    const wrapper = await mountImported("desktop");
    const handle = wrapper.get('[data-test="exam-workspace-column-handle-list"]');

    await handle.trigger("keydown", { key: "ArrowRight" });

    const stored = localStorage.getItem(EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY);
    expect(stored).not.toBeNull();
    expect(JSON.parse(stored ?? "")["list"]).toBe(276);
    expect(frameOf(wrapper).style.getPropertyValue("--xw-list-size")).toBe("276px");

    await handle.trigger("dblclick");

    expect(localStorage.getItem(EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY)).toBeNull();
  });

  it("closes the drawer with Enter on the side handle", async () => {
    stubGridTracks();
    const wrapper = await mountImported("desktop");

    await wrapper.get('[data-test="exam-workspace-column-handle-side"]').trigger("keydown", { key: "Enter" });
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-column-handle-side"]').exists()).toBe(false);
  });

  it("renders at defaults with no inline width when storage throws", async () => {
    vi.spyOn(localStorage, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(localStorage, "setItem").mockImplementation(() => {
      throw new Error("full");
    });

    const wrapper = await mountImported("desktop");
    const frame = frameOf(wrapper);

    expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(true);
    expect(frame.style.getPropertyValue("--xw-list-size")).toBe("");
    expect(frame.style.getPropertyValue("--xw-drawer-size")).toBe("");
    expect(frame.dataset["list"]).toBe("open");
  });
});
