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

function mountDrawer(overrides: { conversionElapsed: string | null; conversionMessage: string | null }) {
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

  it("renders no clock while no phase is known", async () => {
    const wrapper = mountDrawer({ conversionElapsed: null, conversionMessage: "Konverterar provet …" });
    await flushPromises();

    expect(wrapper.find(ELAPSED).exists()).toBe(false);
    expect(wrapper.get(STATUS).find(".xw-spin").exists()).toBe(true);
  });
});
