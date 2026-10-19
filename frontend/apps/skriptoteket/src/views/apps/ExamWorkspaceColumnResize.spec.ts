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
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceConversionStatus, NativeExamDocument } from "../../api/examWorkspace";
import { UiGlyph } from "../../components/ui/shared";
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
  const style = globalThis.document.createElement("div").style;
  style.gridTemplateColumns = GRID;
  style.setProperty("--xw-list-min", "260px");
  style.setProperty("--xw-drawer-min", "300px");
  style.setProperty("--xw-preview-min", "300px");
  style.setProperty("--xw-editor-min", "400px");
  vi.spyOn(window, "getComputedStyle").mockReturnValue(style);
}

function stubPointerCapture(): void {
  HTMLElement.prototype.setPointerCapture = vi.fn();
  HTMLElement.prototype.releasePointerCapture = vi.fn();
}

function requireHtmlElement(value: Element | null, description: string): HTMLElement {
  if (!(value instanceof HTMLElement)) {
    throw new Error(`${description} is not an HTMLElement`);
  }
  return value;
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
  return requireHtmlElement(
    wrapper.get('[data-test="exam-workspace-frame"]').element,
    "exam-workspace-frame",
  );
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

  it("renders the expand glyph on the rail and the toggle-sidebar glyph on the collapse control", async () => {
    const wrapper = await mountImported("desktop");

    expect(
      wrapper.get('[data-test="exam-workspace-list-collapse"]').getComponent(UiGlyph).props("meaning"),
    ).toBe("toggle-sidebar");

    await wrapper.get('[data-test="exam-workspace-list-collapse"]').trigger("click");

    expect(
      wrapper.get('[data-test="exam-workspace-list-expand"]').getComponent(UiGlyph).props("meaning"),
    ).toBe("expand");
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

  it("keeps the same list handle element with focus across keyboard collapse and restore", async () => {
    stubGridTracks();
    const wrapper = await mountImported("desktop");
    const listHandleSelector = '[data-test="exam-workspace-column-handle-list"]';
    const openHandle = requireHtmlElement(wrapper.get(listHandleSelector).element, "open list handle");
    openHandle.focus();

    await wrapper.get(listHandleSelector).trigger("keydown", { key: "Enter" });
    expect(frameOf(wrapper).dataset["list"]).toBe("collapsed");

    const collapsedHandle = requireHtmlElement(wrapper.get(listHandleSelector).element, "collapsed rail handle");
    expect(collapsedHandle).toBe(openHandle);
    expect(openHandle.isConnected).toBe(true);
    expect(globalThis.document.activeElement).toBe(openHandle);

    const focused = globalThis.document.activeElement;
    if (focused === null) {
      throw new Error("no focused element after the keyboard collapse");
    }
    focused.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await nextTick();
    expect(frameOf(wrapper).dataset["list"]).toBe("open");
  });

  it("keeps the same list handle element across a rail drag that expands the list", async () => {
    stubGridTracks();
    stubPointerCapture();
    const wrapper = await mountImported("desktop");

    await wrapper.get('[data-test="exam-workspace-list-collapse"]').trigger("click");
    expect(frameOf(wrapper).dataset["list"]).toBe("collapsed");

    const listHandleSelector = '[data-test="exam-workspace-column-handle-list"]';
    const railHandle = requireHtmlElement(wrapper.get(listHandleSelector).element, "collapsed rail handle");
    railHandle.dispatchEvent(
      new MouseEvent("pointerdown", { bubbles: true, cancelable: true, button: 0, clientX: 100 }),
    );
    await nextTick();
    railHandle.dispatchEvent(
      new MouseEvent("pointermove", { bubbles: true, cancelable: true, clientX: 200 }),
    );
    await nextTick();

    expect(frameOf(wrapper).dataset["list"]).toBe("open");
    const expandedHandle = requireHtmlElement(wrapper.get(listHandleSelector).element, "expanded list handle");
    expect(expandedHandle).toBe(railHandle);
    expect(railHandle.isConnected).toBe(true);
  });

  it("moves focus between the collapse and expand glyphs on glyph click", async () => {
    const wrapper = await mountImported("desktop");

    await wrapper.get('[data-test="exam-workspace-list-collapse"]').trigger("click");
    await flushPromises();
    const expandGlyph = requireHtmlElement(
      globalThis.document.querySelector('[data-test="exam-workspace-list-expand"]'),
      "exam-workspace-list-expand",
    );
    expect(globalThis.document.activeElement).toBe(expandGlyph);

    await wrapper.get('[data-test="exam-workspace-list-expand"]').trigger("click");
    await flushPromises();
    const collapseGlyph = requireHtmlElement(
      globalThis.document.querySelector('[data-test="exam-workspace-list-collapse"]'),
      "exam-workspace-list-collapse",
    );
    expect(globalThis.document.activeElement).toBe(collapseGlyph);
  });

  it("keeps the list handle outside the list scroll frame on desktop", async () => {
    const wrapper = await mountImported("desktop");

    const listRoot = requireHtmlElement(
      wrapper.get('[data-test="exam-workspace-question-list"]').element,
      "exam-workspace-question-list",
    );
    const listHandle = requireHtmlElement(
      wrapper.get('[data-test="exam-workspace-column-handle-list"]').element,
      "exam-workspace-column-handle-list",
    );
    const listFrame = listRoot.querySelector(".list__frame");
    if (listFrame === null) {
      throw new Error("list scroll frame is missing");
    }

    expect(listHandle.parentElement).toBe(listRoot);
    expect(listFrame.contains(listHandle)).toBe(false);
  });

  it("keeps the drawer handle outside the drawer scroll frame on desktop", async () => {
    const wrapper = await mountImported("desktop");

    const drawerRoot = requireHtmlElement(
      wrapper.get('[data-test="exam-workspace-drawer-open"]').element,
      "exam-workspace-drawer-open",
    );
    const drawerHandle = drawerRoot.querySelector<HTMLElement>(
      '[data-test="exam-workspace-column-handle-side"]',
    );
    const drawerFrame = drawerRoot.querySelector(".drawer__frame");
    if (drawerHandle === null || drawerFrame === null) {
      throw new Error("drawer handle or scroll frame is missing");
    }

    expect(drawerHandle.parentElement).toBe(drawerRoot);
    expect(drawerFrame.contains(drawerHandle)).toBe(false);
  });

  it("keeps the preview handle outside the preview scroll frame on desktop", async () => {
    const wrapper = await mountImported("desktop");

    await wrapper.get('[data-test="exam-workspace-print-preview-toggle"]').trigger("click");
    await flushPromises();

    const previewRoot = requireHtmlElement(
      wrapper.get('[data-test="exam-workspace-print-preview"]').element,
      "exam-workspace-print-preview",
    );
    const previewHandle = previewRoot.querySelector<HTMLElement>(
      '[data-test="exam-workspace-column-handle-side"]',
    );
    const previewFrame = previewRoot.querySelector(".pp__frame");
    if (previewHandle === null || previewFrame === null) {
      throw new Error("preview handle or scroll frame is missing");
    }

    expect(previewHandle.parentElement).toBe(previewRoot);
    expect(previewFrame.contains(previewHandle)).toBe(false);
  });
});
