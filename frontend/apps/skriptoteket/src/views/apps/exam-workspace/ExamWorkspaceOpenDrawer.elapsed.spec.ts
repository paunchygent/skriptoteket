/**
 * Exam workspace Öppna drawer: the import's phase line carries the elapsed
 * time of the phase (TASK-SKRIPT-39-04-23). The status block is a polite live
 * region, so a clock ticking inside it must stay out of the announcement; the
 * busy glyph stays for every phase.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Plugin } from "vue";

import { listUnreadableExamWorkspaceDocuments } from "../../../api/examWorkspaceUnreadableFiles";
import ExamWorkspaceOpenDrawer from "./ExamWorkspaceOpenDrawer.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import {
  EXAM_WORKSPACE_UNREADABLE_FILES_KEY,
  useExamWorkspaceUnreadableFiles,
} from "./useExamWorkspaceUnreadableFiles";

const unreadableApiMocks = vi.hoisted(() => ({
  downloadSavedExamFile: vi.fn(),
  listUnreadableExamWorkspaceDocuments: vi.fn(),
  removeSavedExamFile: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceUnreadableFiles", () => unreadableApiMocks);

const STATUS = '[data-test="exam-workspace-conversion-status"]';
const ELAPSED = '[data-test="exam-workspace-conversion-elapsed"]';
const MESSAGE = '[data-test="exam-workspace-conversion-message"]';

type DrawerOverrides = {
  conversionElapsed: string | null;
  conversionMessage: string | null;
  conversionProgress?: { received: number; total: number } | null;
  isConverting?: boolean;
  isImporting?: boolean;
};

function mountDrawer(overrides: DrawerOverrides) {
  setActivePinia(createPinia());
  const unreadable = useExamWorkspaceUnreadableFiles();
  const provideUnreadable: Plugin = {
    install(app) {
      app.provide(EXAM_WORKSPACE_UNREADABLE_FILES_KEY, unreadable);
    },
  };
  return mount(ExamWorkspaceOpenDrawer, {
    props: {
      conversionError: null,
      conversionProgress: null,
      currentExports: [],
      currentLineageId: null,
      documents: [],
      importBlocked: false,
      isBusy: true,
      isOpenBlockedByOtherOperation: false,
      isConverting: true,
      isImporting: false,
      isDirty: false,
      notes: [],
      ordering: "newest",
      saveDetail: null,
      saveState: "saved",
      sourceFileError: null,
      ...overrides,
    },
    global: { plugins: [createPinia(), examWorkspaceProvidersPlugin(), provideUnreadable] },
  });
}

describe("ExamWorkspaceOpenDrawer elapsed time", () => {
  beforeEach(() => {
    vi.mocked(listUnreadableExamWorkspaceDocuments).mockResolvedValue({ documents: [] });
  });

  it("shows the phase line, the busy glyph and the clock hidden from the live announcement", async () => {
    const wrapper = mountDrawer({ conversionElapsed: "1:52", conversionMessage: "Hittar frågorna" });
    await flushPromises();

    const status = wrapper.get(STATUS);
    expect(status.attributes("role")).toBe("status");
    expect(status.attributes("aria-live")).toBe("polite");
    expect(status.find(".xw-spin").exists()).toBe(true);
    expect(status.text()).toContain("Hittar frågorna");
    const elapsed = wrapper.get(ELAPSED);
    expect(elapsed.text()).toBe("1:52");
    expect(elapsed.attributes("aria-hidden")).toBe("true");
    expect(elapsed.classes()).toContain("prog__elapsed");
  });

  it("renders an empty clock slot while no phase is known", async () => {
    const wrapper = mountDrawer({ conversionElapsed: null, conversionMessage: "Konverterar provet …" });
    await flushPromises();

    expect(wrapper.get(ELAPSED).text()).toBe("");
    expect(wrapper.get(STATUS).find(".xw-spin").exists()).toBe(true);
  });
});

describe("ExamWorkspaceOpenDrawer upload wait", () => {
  beforeEach(() => {
    vi.mocked(listUnreadableExamWorkspaceDocuments).mockResolvedValue({ documents: [] });
  });

  it("shows the status block, the spinning glyph and no drop zone or retry hint while the file uploads", async () => {
    const wrapper = mountDrawer({
      conversionElapsed: null,
      conversionMessage: "Laddar upp filen",
      isConverting: false,
      isImporting: true,
    });
    await flushPromises();

    const status = wrapper.get(STATUS);
    expect(status.text()).toContain("Laddar upp filen");
    expect(status.find(".xw-spin").exists()).toBe(true);
    expect(status.text()).not.toContain("Välj provfilen igen");
    expect(wrapper.find('[data-test="exam-workspace-drop-zone"]').exists()).toBe(false);
  });
});

/**
 * The status row's geometry (clock position, row height at the supported
 * drawer widths) cannot be measured in jsdom: it is checked in the Mac
 * staging walk. These checks hold what jsdom can: the full text in the
 * tooltip and the clock slot present, as one element, through every phase.
 */
describe("ExamWorkspaceOpenDrawer status row slots", () => {
  beforeEach(() => {
    vi.mocked(listUnreadableExamWorkspaceDocuments).mockResolvedValue({ documents: [] });
  });

  it("keeps the clock slot and carries the full message as its tooltip through the phases", async () => {
    const wrapper = mountDrawer({ conversionElapsed: null, conversionMessage: "Läser filen" });
    await flushPromises();
    const slot = wrapper.get(ELAPSED).element;
    expect(wrapper.get(MESSAGE).attributes("title")).toBe("Läser filen");
    expect(wrapper.get(ELAPSED).text()).toBe("");

    await wrapper.setProps({ conversionElapsed: "0:07", conversionMessage: "Sorterar frågorna efter typ" });
    expect(wrapper.get(MESSAGE).attributes("title")).toBe("Sorterar frågorna efter typ");
    expect(wrapper.get(MESSAGE).text()).toBe("Sorterar frågorna efter typ");
    expect(wrapper.get(ELAPSED).element).toBe(slot);
    expect(wrapper.get(ELAPSED).text()).toBe("0:07");

    await wrapper.setProps({
      conversionElapsed: "12:03",
      conversionMessage: "AI-svar mottagna för 12 av 120 frågor.",
      conversionProgress: { received: 12, total: 120 },
    });
    expect(wrapper.get(MESSAGE).attributes("title")).toBe("AI-svar mottagna för 12 av 120 frågor.");
    expect(wrapper.get(ELAPSED).element).toBe(slot);
    expect(wrapper.get(ELAPSED).text()).toBe("12:03");
    expect(wrapper.get(ELAPSED).attributes("aria-hidden")).toBe("true");
  });
});
