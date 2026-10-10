/**
 * Exam workspace two-mode layout slice.
 *
 * Domain purpose:
 *   Lock the Filer/Redigera composition: an imported exam opens in
 *   Redigera, save state stays in the toolbar in both modes, Filer lists the
 *   questions that stop an export and jumps to them with their details open,
 *   desktop and tablet show the question list beside the editor, and the
 *   phone makes the editor the screen behind a "Fråga N av M" picker. The
 *   phone details drawer is a full-screen modal dialog and the tablet
 *   overlay drawer closes on Escape; leaving the phone layout closes the
 *   question sheet.
 *
 * Relationships:
 *   - Mounts `ExamWorkspaceView` through the shared slice harness with a
 *     provided layout, so no media queries are involved.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceEnrichment: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  startExamWorkspaceEnrichment: vi.fn(),
}));

vi.mock("../../api/examWorkspace", () => apiMocks);

async function mountImported(layout: ExamWorkspaceLayout) {
  const { wrapper } = await mountExamWorkspace({}, layout);
  await importFixtureDocument(wrapper);
  return wrapper;
}

function pressEscape(target: EventTarget = document): void {
  target.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
}

function isShown(wrapper: Awaited<ReturnType<typeof mountImported>>, testId: string): boolean {
  const element = wrapper.get(`[data-test="${testId}"]`).element as HTMLElement;
  return element.style.display !== "none";
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
  apiMocks.getExamWorkspaceEnrichment.mockResolvedValue({
    document_revision: 1,
    lineage_id: "lineage-1",
    proposals: [],
    state: "not_requested",
  });
  apiMocks.importExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 1 }));
});

describe("ExamWorkspaceView two-mode layout", () => {
  it("starts in Filer with Redigera unavailable until an exam is open", async () => {
    const { wrapper } = await mountExamWorkspace();

    expect(isShown(wrapper, "exam-workspace-rail")).toBe(true);
    expect(isShown(wrapper, "exam-workspace-workspace")).toBe(false);
    expect(
      wrapper.get('[data-test="exam-workspace-mode-redigera"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("opens an imported exam in Redigera and keeps save state in both modes", async () => {
    const wrapper = await mountImported("desktop");

    expect(isShown(wrapper, "exam-workspace-workspace")).toBe(true);
    expect(isShown(wrapper, "exam-workspace-rail")).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-item-editor"]').exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");

    expect(isShown(wrapper, "exam-workspace-rail")).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-save"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-summary-version"]').text()).toBe(
      "Version 1",
    );
  });

  it("lists questions that stop an export in Filer and jumps to one with details open", async () => {
    const wrapper = await mountImported("desktop");
    await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");

    const readiness = wrapper.get('[data-test="exam-workspace-readiness"]');
    expect(readiness.text()).toContain("2 frågor behöver åtgärdas");
    expect(readiness.text()).toContain("Frågan behöver granskas.");

    await wrapper.get('[data-test="exam-workspace-readiness-item-item_004"]').trigger("click");

    expect(isShown(wrapper, "exam-workspace-workspace")).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-item-editor"]').text()).toContain("Fråga 4");
    expect(wrapper.get('[data-test="exam-workspace-item-drawer"]').text()).toContain(
      "Frågan behöver granskas.",
    );
  });

  it("steps between questions from the editor header", async () => {
    const wrapper = await mountImported("desktop");

    await wrapper.get('[data-test="exam-workspace-item-next"]').trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-item-editor"]').text()).toContain("Fråga 2");

    await wrapper.get('[data-test="exam-workspace-item-previous"]').trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-item-editor"]').text()).toContain("Fråga 1");
    expect(
      wrapper.get('[data-test="exam-workspace-item-previous"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("keeps the question list beside the editor on tablet", async () => {
    const wrapper = await mountImported("tablet");

    expect(wrapper.get('[data-test="exam-workspace-frame"]').attributes("data-layout")).toBe(
      "tablet",
    );
    expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-phone-question-bar"]').exists()).toBe(false);
  });

  it("makes the editor the phone screen behind a question picker sheet", async () => {
    const wrapper = await mountImported("phone");

    expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-item-previous"]').exists()).toBe(false);
    const picker = wrapper.get('[data-test="exam-workspace-question-picker"]');
    expect(picker.text()).toContain("Fråga 1 av 8");

    await wrapper.get('[data-test="exam-workspace-phone-next"]').trigger("click");
    expect(picker.text()).toContain("Fråga 2 av 8");

    await picker.trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-sheet"]').exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-item-row-item_005"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-sheet"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-question-picker"]').text()).toContain(
      "Fråga 5 av 8",
    );
  });

  it("shows the phone details drawer as a full-screen modal dialog that Escape closes", async () => {
    const wrapper = await mountImported("phone");

    await wrapper.get('[data-test="exam-workspace-item-details-toggle"]').trigger("click");

    const frame = wrapper.get('[data-test="exam-workspace-item-drawer-frame"]');
    expect(frame.attributes("role")).toBe("dialog");
    expect(frame.attributes("aria-modal")).toBe("true");
    const titleId = frame.attributes("aria-labelledby");
    expect(titleId).toBeTruthy();
    expect(wrapper.get(`[id="${titleId}"]`).text()).toContain("Detaljer – fråga 1");
    expect(frame.classes()).toContain("fixed");

    pressEscape();
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-item-drawer"]').exists()).toBe(false);
  });

  it("closes the tablet overlay drawer on Escape from inside it, not from the editor", async () => {
    const wrapper = await mountImported("tablet");

    await wrapper.get('[data-test="exam-workspace-item-details-toggle"]').trigger("click");
    const frame = wrapper.get('[data-test="exam-workspace-item-drawer-frame"]');
    expect(frame.attributes("role")).toBeUndefined();

    pressEscape(wrapper.get('[data-test="exam-workspace-item-title-input"]').element);
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-item-drawer"]').exists()).toBe(true);

    pressEscape(wrapper.get('[data-test="exam-workspace-item-drawer-close"]').element);
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-item-drawer"]').exists()).toBe(false);
  });

  it("returns focus to the Detaljer toggle when Escape closes the tablet overlay", async () => {
    const { wrapper } = await mountExamWorkspace({}, "tablet", document.body);
    await importFixtureDocument(wrapper);
    const toggle = wrapper.get('[data-test="exam-workspace-item-details-toggle"]')
      .element as HTMLButtonElement;

    // A click that does not focus its button (Safari) leaves focus on the page.
    (document.activeElement as HTMLElement | null)?.blur();
    await wrapper.get('[data-test="exam-workspace-item-details-toggle"]').trigger("click");
    const frame = wrapper.get('[data-test="exam-workspace-item-drawer-frame"]').element;
    expect(document.activeElement).toBe(frame);

    pressEscape(frame);
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-item-drawer"]').exists()).toBe(false);
    expect(document.activeElement).toBe(toggle);
    wrapper.unmount();
  });

  it("applies the overlay focus contract when a desktop drawer is resized to tablet", async () => {
    const { layout, wrapper } = await mountExamWorkspace({}, "desktop", document.body);
    await importFixtureDocument(wrapper);
    const toggle = wrapper.get('[data-test="exam-workspace-item-details-toggle"]')
      .element as HTMLButtonElement;
    toggle.focus();
    await wrapper.get('[data-test="exam-workspace-item-details-toggle"]').trigger("click");
    const frame = wrapper.get('[data-test="exam-workspace-item-drawer-frame"]').element;
    expect(document.activeElement).toBe(toggle);

    layout.value = "tablet";
    await flushPromises();
    expect(document.activeElement).toBe(frame);

    pressEscape(frame);
    await flushPromises();
    expect(document.activeElement).toBe(toggle);
    wrapper.unmount();
  });

  it("fills the available height without a hard-coded header offset", async () => {
    const wrapper = await mountImported("desktop");
    const frame = wrapper.get('[data-test="exam-workspace-frame"]');

    expect(frame.classes()).toContain("flex-1");
    expect(frame.classes().join(" ")).not.toContain("72px");
  });

  it("paints the phone question sheet with an opaque surface", async () => {
    const wrapper = await mountImported("phone");
    await wrapper.get('[data-test="exam-workspace-question-picker"]').trigger("click");

    const classes = wrapper.get('[data-test="exam-workspace-sheet"] section').classes();
    expect(classes).toContain("bg-modal");
    expect(classes).not.toContain("bg-panel");
  });

  it("closes the question sheet when the layout leaves phone", async () => {
    const { layout, wrapper } = await mountExamWorkspace({}, "phone");
    await importFixtureDocument(wrapper);

    await wrapper.get('[data-test="exam-workspace-question-picker"]').trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-sheet"]').exists()).toBe(true);

    layout.value = "tablet";
    await flushPromises();
    layout.value = "phone";
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-sheet"]').exists()).toBe(false);
  });
});
