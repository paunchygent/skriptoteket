/**
 * Exam workspace side-panel state.
 *
 * Domain purpose:
 *   Lock the width owner's side state (TASK-SKRIPT-41-02-04): the frame's
 *   `data-side` is the open drawer, else the rendered print preview, else
 *   none, on desktop, tablet and phone, without the removed legacy state
 *   classes. Opening the preview clears the drawer, and opening a drawer
 *   clears the preview.
 *
 * Relationships:
 *   - Mounts `ExamWorkspaceView` through the shared slice harness with a
 *     provided layout, so no media queries are involved.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import type { ExamWorkspaceConversionStatus, NativeExamDocument } from "../../api/examWorkspace";
import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";
import { EXAM_WORKSPACE_LAYOUT_KEY } from "./exam-workspace/useExamWorkspaceLayout";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import {
  buildResponse,
  EXAM_WORKSPACE_PATH,
  importFixtureDocument,
  mountExamWorkspace,
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

type Mounted = Awaited<ReturnType<typeof mountImported>>;

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

describe("exam workspace width owner (data-side)", () => {
  function frameSide(wrapper: Mounted): string | undefined {
    return wrapper.get('[data-test="exam-workspace-frame"]').attributes("data-side");
  }

  function frameClasses(wrapper: Mounted): string[] {
    return wrapper.get('[data-test="exam-workspace-frame"]').classes();
  }

  function expectNoLegacyStateClasses(wrapper: Mounted): void {
    expect(frameClasses(wrapper)).not.toContain("ws--drawer");
    expect(frameClasses(wrapper)).not.toContain("ws--preview");
  }

  /** A signed-in view whose teacher half is null, so the preview can never render. */
  async function mountGuestLikeDesktop(): Promise<Mounted> {
    const slot = globalThis.document.createElement("div");
    slot.id = "app-topbar-page-slot";
    globalThis.document.body.append(slot);
    const host = globalThis.document.createElement("div");
    globalThis.document.body.append(host);
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ component: { template: "<div />" }, path: EXAM_WORKSPACE_PATH }],
    });
    await router.push({ path: EXAM_WORKSPACE_PATH });
    await router.isReady();
    const layoutRef = ref<ExamWorkspaceLayout>("desktop");
    const wrapper = mount(ExamWorkspaceView, {
      attachTo: host,
      props: { store: { ...serverExamWorkspaceStore, teacher: null } },
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), router],
        provide: { [EXAM_WORKSPACE_LAYOUT_KEY]: layoutRef },
      },
    });
    await flushPromises();
    mounted.push(wrapper);
    return wrapper;
  }

  it("reports none with no side open on desktop", async () => {
    const wrapper = await mountImported("desktop");
    await wrapper.get('[data-test="exam-workspace-open"]').trigger("click");

    expect(frameSide(wrapper)).toBe("none");
    expectNoLegacyStateClasses(wrapper);
  });

  it("reports open for the Öppna drawer on desktop", async () => {
    const wrapper = await mountImported("desktop");

    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(true);
    expect(frameSide(wrapper)).toBe("open");
    expectNoLegacyStateClasses(wrapper);
  });

  it("reports details for Provets uppgifter on desktop", async () => {
    const wrapper = await mountImported("desktop");
    await clickTitle();

    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(true);
    expect(frameSide(wrapper)).toBe("details");
    expectNoLegacyStateClasses(wrapper);
  });

  it("reports export for the Exportera drawer on desktop", async () => {
    const wrapper = await mountImported("desktop");
    await wrapper.get('[data-test="exam-workspace-open"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    const more = document.body.querySelector<HTMLElement>('[data-test="exam-workspace-export-more"]');
    expect(more).not.toBeNull();
    more?.click();
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-drawer-export"]').exists()).toBe(true);
    expect(frameSide(wrapper)).toBe("export");
    expectNoLegacyStateClasses(wrapper);
  });

  it("reports preview when a teacher opens Förhandsgranska on desktop", async () => {
    const wrapper = await mountImported("desktop");
    await wrapper.get('[data-test="exam-workspace-print-preview-toggle"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-print-preview"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(false);
    expect(frameSide(wrapper)).toBe("preview");
    expectNoLegacyStateClasses(wrapper);
  });

  it("prefers the drawer when one opens while the preview is open", async () => {
    const wrapper = await mountImported("desktop");
    await wrapper.get('[data-test="exam-workspace-print-preview-toggle"]').trigger("click");
    await flushPromises();
    expect(frameSide(wrapper)).toBe("preview");

    await clickTitle();

    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-print-preview"]').exists()).toBe(false);
    expect(frameSide(wrapper)).toBe("details");
    expectNoLegacyStateClasses(wrapper);
  });

  it("prefers the preview when it opens while a drawer is open", async () => {
    const wrapper = await mountImported("desktop");
    expect(frameSide(wrapper)).toBe("open");

    await wrapper.get('[data-test="exam-workspace-print-preview-toggle"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-print-preview"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(false);
    expect(frameSide(wrapper)).toBe("preview");
    expectNoLegacyStateClasses(wrapper);
  });

  it("keeps data-side on the drawer for a guest with no preview toggle", async () => {
    const wrapper = await mountGuestLikeDesktop();

    expect(wrapper.find('[data-test="exam-workspace-print-preview-toggle"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(true);
    expect(frameSide(wrapper)).toBe("open");
    expectNoLegacyStateClasses(wrapper);
  });

  it("follows the same semantic state on tablet without legacy classes", async () => {
    const wrapper = await mountImported("tablet");

    expect(frameSide(wrapper)).toBe("none");
    expectNoLegacyStateClasses(wrapper);

    await clickTitle();

    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(true);
    expect(frameSide(wrapper)).toBe("details");
    expectNoLegacyStateClasses(wrapper);
  });

  it("follows the same semantic state on phone without legacy classes", async () => {
    const wrapper = await mountImported("phone");

    expect(frameSide(wrapper)).toBe("none");
    expect(frameSide(wrapper)).not.toBeUndefined();
    expectNoLegacyStateClasses(wrapper);

    await clickTitle();

    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(true);
    expect(frameSide(wrapper)).toBe("details");
    expect(wrapper.find('[data-test="exam-workspace-print-preview-toggle"]').exists()).toBe(false);
    expectNoLegacyStateClasses(wrapper);
  });
});
