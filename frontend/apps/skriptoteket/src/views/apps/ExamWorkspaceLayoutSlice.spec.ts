/**
 * Exam workspace frame layout slice.
 *
 * Domain purpose:
 *   Lock the frame composition: with no exam the Öppna drawer is open beside
 *   an empty state, an imported exam opens its question list and editor with
 *   the save state in the header, the export drawer lists the questions that
 *   stop an export and jumps to them, desktop and tablet show the question
 *   list beside the editor, and the phone makes the editor the screen behind
 *   a question strip whose list is a layer. Drawers are docked on desktop,
 *   floating on tablet and full screen on phone; leaving the phone layout
 *   closes the list layer.
 *
 * Relationships:
 *   - Mounts `ExamWorkspaceView` through the shared slice harness with a
 *     provided layout, so no media queries are involved.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceConversionStatus, NativeExamDocument } from "../../api/examWorkspace";
import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const mounted: Array<{ unmount: () => void }> = [];

async function mountWithLayout(layout: ExamWorkspaceLayout) {
  // The shell's top bar slot receives the header's title and Spara on a phone.
  const slot = globalThis.document.createElement("div");
  slot.id = "app-topbar-page-slot";
  globalThis.document.body.append(slot);
  const host = globalThis.document.createElement("div");
  globalThis.document.body.append(host);
  const mountedWorkspace = await mountExamWorkspace({}, layout, host);
  mounted.push(mountedWorkspace.wrapper);
  await importFixtureDocument(mountedWorkspace.wrapper);
  return mountedWorkspace;
}

async function mountImported(layout: ExamWorkspaceLayout) {
  return (await mountWithLayout(layout)).wrapper;
}

/** The title button lives in the shell's top bar on a phone, outside the wrapper. */
async function clickTitle(): Promise<void> {
  document.querySelector<HTMLElement>('[data-test="exam-workspace-title"]')?.click();
  await flushPromises();
}

function pressEscape(target: EventTarget = document): void {
  target.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
}

type Mounted = Awaited<ReturnType<typeof mountImported>>;

function editorText(wrapper: Mounted): string {
  return wrapper.get('[data-test="exam-workspace-item-editor"]').text();
}

/** The phone list is a layer: the list carries the overlay class only while it is open. */
function isListLayerOpen(wrapper: Mounted): boolean {
  return wrapper.get('[data-test="exam-workspace-question-list"]').classes().includes("list--overlay");
}

/** The finished import: its poll status, and the conversion its fetched document carries. */
const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  globalThis.document.body.replaceChildren();
});

beforeEach(() => {
  for (const mock of [...Object.values(apiMocks), ...Object.values(exportApiMocks)]) {
    mock.mockReset();
  }
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    const response = buildResponse({ conversion: succeededConversion, version: 1 });
    // Layout proof needs one export blocker: question 4 has a source key but still needs review.
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

describe("ExamWorkspaceView frame layout", () => {
  it("opens the Öppna drawer beside an empty state until an exam is open", async () => {
    const { wrapper } = await mountExamWorkspace();

    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-item-editor"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-title"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-save-menu"]').attributes("disabled")).toBeDefined();
  });

  it("opens an imported exam with its list and editor and keeps the Öppna drawer docked on desktop", async () => {
    const wrapper = await mountImported("desktop");

    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(true);
    expect(editorText(wrapper)).toContain("Fråga 1");
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(true);
    expect(document.querySelector('[data-test="exam-workspace-title"]')?.textContent).toContain(
      "NO-prov HT25",
    );
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toContain("Sparat");
    expect(wrapper.find('[data-test="exam-workspace-save-menu"]').exists()).toBe(true);
  });

  it("closes the Öppna drawer after an import on tablet", async () => {
    const wrapper = await mountImported("tablet");

    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(false);
    expect(editorText(wrapper)).toContain("Fråga 1");
  });

  it("lists questions that stop an export in the export drawer and jumps to one", async () => {
    const wrapper = await mountImported("desktop");
    await wrapper.get('[data-test="exam-workspace-open"]').trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    const more = document.body.querySelector<HTMLElement>('[data-test="exam-workspace-export-more"]');
    expect(more).not.toBeNull();
    more?.click();
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-drawer-export"]').exists()).toBe(true);
    const blockers = wrapper.get('[data-test="exam-workspace-export-drawer-blockers"]');
    expect(wrapper.get('[data-test="exam-workspace-blocker-item_003"]').text()).toBe("Fråga 3: facit ej granskat");
    expect(blockers.text()).toContain("Kan inte exporteras ännu");
    // Question 4 only needs review, which never stops an export (D1).
    expect(wrapper.find('[data-test="exam-workspace-blocker-item_004"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-blocker-item_003"]').trigger("click");

    await flushPromises();
    expect(editorText(wrapper)).toContain("Fråga 3");
    expect(document.activeElement?.getAttribute("data-test")).toBe("exam-workspace-review");
    // On desktop the export drawer stays docked while the teacher fixes the question.
    expect(wrapper.find('[data-test="exam-workspace-drawer-export"]').exists()).toBe(true);
  });

  it("steps between questions with the arrow keys outside text fields", async () => {
    const wrapper = await mountImported("desktop");

    window.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowDown" }));
    await flushPromises();
    expect(editorText(wrapper)).toContain("Fråga 2");

    window.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowUp" }));
    await flushPromises();
    expect(editorText(wrapper)).toContain("Fråga 1");

    // The exam instruction sits above the first question, and nothing above it.
    window.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowUp" }));
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-exam-instruction-editor"]').exists()).toBe(true);
    window.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowUp" }));
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-exam-instruction-editor"]').exists()).toBe(true);
  });

  it("does not step questions when an arrow key is pressed inside a text field", async () => {
    const wrapper = await mountImported("desktop");
    const input = wrapper.get('[data-test="exam-workspace-item-points-input"]').element;

    input.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowDown" }));
    await flushPromises();

    expect(editorText(wrapper)).toContain("Fråga 1");
  });

  it("keeps the question list beside the editor on tablet", async () => {
    const wrapper = await mountImported("tablet");

    expect(wrapper.get('[data-test="exam-workspace-frame"]').attributes("data-layout")).toBe(
      "tablet",
    );
    expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-phone-strip"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-list-back"]').exists()).toBe(false);
  });

  it("orders the desktop toolbar Öppna, Spara som, Exportera, AI facit, Ångra and Gör om", async () => {
    const wrapper = await mountImported("desktop");
    const order = [
      "exam-workspace-open", "exam-workspace-save-menu", "exam-workspace-export",
      "exam-workspace-suggest-all", "exam-workspace-undo", "exam-workspace-redo",
    ];
    const found = wrapper.get('[data-test="exam-workspace-header"]').findAll("[data-test]")
      .map((element) => element.attributes("data-test"))
      .filter((testId): testId is string => order.includes(testId ?? ""));
    expect(found).toEqual(order);
  });

  it("puts the phone strip's state icon before Fråga N and the list chevron after it", async () => {
    const wrapper = await mountImported("phone");
    const parts = [...wrapper.get('[data-test="exam-workspace-phone-list"]').element.children];
    const label = parts.findIndex((element) => element.classList.contains("strip__label"));
    expect(label).toBe(1);
    expect(parts[label]!.textContent).toBe("Fråga 1");
    expect(parts[label + 1]!.classList.contains("strip__chevron")).toBe(true);
  });

  it("makes the editor the phone screen behind a question strip that opens the list layer", async () => {
    const wrapper = await mountImported("phone");

    expect(wrapper.get('[data-test="exam-workspace-frame"]').attributes("data-layout")).toBe(
      "phone",
    );
    expect(isListLayerOpen(wrapper)).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-list-back"]').exists()).toBe(false);
    const strip = wrapper.get('[data-test="exam-workspace-phone-list"]');
    expect(strip.text()).toContain("Fråga 1");
    // The exam's instruction sits above the first question.
    expect(
      wrapper.get('[data-test="exam-workspace-phone-previous"]').attributes("disabled"),
    ).toBeUndefined();

    await wrapper.get('[data-test="exam-workspace-phone-next"]').trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-phone-list"]').text()).toContain("Fråga 2");
    expect(editorText(wrapper)).toContain("Fråga 2");

    await strip.trigger("click");
    expect(isListLayerOpen(wrapper)).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-list-back"]').exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-row-item_005"]').trigger("click");
    await flushPromises();

    expect(isListLayerOpen(wrapper)).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-phone-list"]').text()).toContain("Fråga 5");
    expect(editorText(wrapper)).toContain("Fråga 5");
  });

  it("closes the phone list layer with Tillbaka and with Escape without changing the question", async () => {
    const wrapper = await mountImported("phone");

    await wrapper.get('[data-test="exam-workspace-phone-list"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-list-back"]').trigger("click");
    expect(isListLayerOpen(wrapper)).toBe(false);

    await wrapper.get('[data-test="exam-workspace-phone-list"]').trigger("click");
    expect(isListLayerOpen(wrapper)).toBe(true);
    pressEscape(window);
    await flushPromises();

    expect(isListLayerOpen(wrapper)).toBe(false);
    expect(editorText(wrapper)).toContain("Fråga 1");
  });

  it("shows the phone details drawer as a full-screen modal dialog that Escape closes", async () => {
    const wrapper = await mountImported("phone");

    await clickTitle();

    const drawer = wrapper.get('[data-test="exam-workspace-drawer-details"]');
    expect(drawer.attributes("role")).toBe("dialog");
    expect(drawer.attributes("aria-modal")).toBe("true");
    expect(drawer.classes()).toContain("drawer--phone");
    const titleId = drawer.attributes("aria-labelledby");
    expect(titleId).toBeTruthy();
    expect(wrapper.get(`[id="${titleId}"]`).text()).toContain("Provets uppgifter");
    expect(wrapper.find('[data-test="exam-workspace-drawer-back"]').exists()).toBe(true);

    pressEscape();
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(false);
  });

  it("closes the phone drawer with Tillbaka", async () => {
    const wrapper = await mountImported("phone");
    await clickTitle();

    await wrapper.get('[data-test="exam-workspace-drawer-back"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(false);
  });

  it("closes the tablet floating drawer on Escape from inside it, not from the editor", async () => {
    const wrapper = await mountImported("tablet");

    await clickTitle();
    const drawer = wrapper.get('[data-test="exam-workspace-drawer-details"]');
    expect(drawer.attributes("role")).toBe("complementary");
    expect(drawer.attributes("aria-modal")).toBeUndefined();
    expect(drawer.classes()).toContain("drawer--tablet");

    pressEscape(wrapper.get('[data-test="exam-workspace-item-points-input"]').element);
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(true);

    pressEscape(wrapper.get('[data-test="exam-workspace-drawer-close"]').element);
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(false);
  });

  it("docks the desktop drawer without taking focus", async () => {
    const { wrapper } = await mountExamWorkspace({}, "desktop", document.body);
    await importFixtureDocument(wrapper);
    const title = wrapper.get('[data-test="exam-workspace-title"]').element as HTMLButtonElement;
    title.focus();

    await clickTitle();

    const drawer = wrapper.get('[data-test="exam-workspace-drawer-details"]');
    expect(drawer.classes()).toContain("drawer--desktop");
    expect(drawer.attributes("role")).toBe("complementary");
    expect(document.activeElement).toBe(title);
    wrapper.unmount();
  });

  it("returns focus to the title button when Escape closes the tablet drawer", async () => {
    const { wrapper } = await mountExamWorkspace({}, "tablet", document.body);
    await importFixtureDocument(wrapper);
    const title = wrapper.get('[data-test="exam-workspace-title"]').element as HTMLButtonElement;

    // A click that does not focus its button (Safari) leaves focus on the page.
    (document.activeElement as HTMLElement | null)?.blur();
    await clickTitle();
    const drawer = wrapper.get('[data-test="exam-workspace-drawer-details"]').element;
    expect(document.activeElement).toBe(drawer);

    pressEscape(drawer);
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(false);
    expect(document.activeElement).toBe(title);
    wrapper.unmount();
  });

  it("applies the floating focus contract when a desktop drawer is resized to tablet", async () => {
    const { layout, wrapper } = await mountExamWorkspace({}, "desktop", document.body);
    await importFixtureDocument(wrapper);
    const title = wrapper.get('[data-test="exam-workspace-title"]').element as HTMLButtonElement;
    title.focus();
    await clickTitle();
    const drawer = wrapper.get('[data-test="exam-workspace-drawer-details"]').element;
    expect(document.activeElement).toBe(title);

    layout.value = "tablet";
    await flushPromises();
    expect(document.activeElement).toBe(drawer);

    pressEscape(drawer);
    await flushPromises();
    expect(document.activeElement).toBe(title);
    wrapper.unmount();
  });

  it("reports the layout through data-layout and follows layout changes", async () => {
    const { layout, wrapper } = await mountWithLayout("desktop");
    const frame = wrapper.get('[data-test="exam-workspace-frame"]');
    expect(frame.attributes("data-layout")).toBe("desktop");
    expect(wrapper.find('[data-test="exam-workspace-phone-strip"]').exists()).toBe(false);

    layout.value = "phone";
    await flushPromises();
    expect(frame.attributes("data-layout")).toBe("phone");
    expect(wrapper.find('[data-test="exam-workspace-phone-strip"]').exists()).toBe(true);

    layout.value = "tablet";
    await flushPromises();
    expect(frame.attributes("data-layout")).toBe("tablet");
    expect(wrapper.find('[data-test="exam-workspace-phone-strip"]').exists()).toBe(false);
  });

  it.todo(
    "fills the available height without a hard-coded header offset — height is scoped CSS now (`.ws { flex: 1 }`), not a class or attribute jsdom can observe",
  );

  it.todo(
    "paints the phone question sheet with an opaque surface — the list layer's background is scoped CSS (`.list--overlay`), not a utility class",
  );

  it("closes the phone list layer when the layout leaves phone", async () => {
    const { layout, wrapper } = await mountWithLayout("phone");

    await wrapper.get('[data-test="exam-workspace-phone-list"]').trigger("click");
    expect(isListLayerOpen(wrapper)).toBe(true);

    layout.value = "tablet";
    await flushPromises();
    layout.value = "phone";
    await flushPromises();

    expect(isListLayerOpen(wrapper)).toBe(false);
  });
});
