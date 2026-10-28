/**
 * Exam workspace Öppna drawer: the open exam's import notes reach the teacher.
 *
 * Expected behavior (TASK-SKRIPT-39-10-03, D2):
 *   The backend names every page it skipped for lacking readable text in the
 *   import result. The drawer shows those notes through its existing notes
 *   list (`data-test="exam-workspace-notes"`) on the current exam's row, in
 *   the order the import produced them, and shows no notes list on another
 *   exam's row or when the open exam has no notes.
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
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";

const unreadableApiMocks = vi.hoisted(() => ({
  downloadSavedExamFile: vi.fn(),
  listUnreadableExamWorkspaceDocuments: vi.fn(),
  removeSavedExamFile: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceUnreadableFiles", () => unreadableApiMocks);

const listUnreadableMock = vi.mocked(listUnreadableExamWorkspaceDocuments);

/** Backend copy for one skipped page. */
const ONE_SKIPPED_PAGE = "Sida 2 importerades inte eftersom texten inte gick att läsa in.";
/** Backend copy for several skipped pages. */
const SEVERAL_SKIPPED_PAGES = "Sidorna 2, 4 och 5 importerades inte eftersom texten inte gick att läsa in.";
/** A note the import already produces today, listed before the skipped-pages note. */
const ANSWER_KEY_NOTE = "Facit: 1. B";

const DOCUMENTS = [
  buildSavedExamSummary({ lineage_id: "lineage-a", title: "Prov A" }),
  buildSavedExamSummary({ lineage_id: "lineage-b", title: "Prov B" }),
];

function mountDrawer(options: { currentLineageId: string | null; notes: string[] }) {
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
      conversionMessage: null,
      conversionElapsed: null,
      conversionProgress: null,
      currentExports: [],
      currentLineageId: options.currentLineageId,
      documents: DOCUMENTS,
      importBlocked: false,
      isBusy: false,
      isConverting: false,
      isImporting: false,
      isDirty: false,
      isOpenBlockedByOtherOperation: false,
      notes: options.notes,
      ordering: "newest",
      saveDetail: null,
      saveState: "saved",
      sourceFileError: null,
    },
    global: {
      plugins: [createPinia(), examWorkspaceProvidersPlugin(), provideUnreadable],
    },
  });
}

/** The note texts the notes list on the current exam's row renders, in order. */
function renderedNotes(wrapper: ReturnType<typeof mountDrawer>): string[] {
  const list = wrapper.get('[data-test="exam-workspace-open-lineage-a"]').find(
    '[data-test="exam-workspace-notes"]',
  );
  return list.findAll("li").map((item) => item.text());
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  listUnreadableMock.mockResolvedValue({ documents: [] });
});

describe("ExamWorkspaceOpenDrawer import notes", () => {
  it("lists one skipped page on the open exam's row", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", notes: [ONE_SKIPPED_PAGE] });
    await flushPromises();

    const list = wrapper.get('[data-test="exam-workspace-open-lineage-a"] [data-test="exam-workspace-notes"]');
    expect(list.findAll("li").map((item) => item.text())).toEqual([ONE_SKIPPED_PAGE]);
  });

  it("lists several skipped pages after the earlier import notes, in order", async () => {
    const wrapper = mountDrawer({
      currentLineageId: "lineage-a",
      notes: [ANSWER_KEY_NOTE, SEVERAL_SKIPPED_PAGES],
    });
    await flushPromises();

    expect(renderedNotes(wrapper)).toEqual([ANSWER_KEY_NOTE, SEVERAL_SKIPPED_PAGES]);
  });

  it("shows no notes list on another exam's row", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", notes: [ONE_SKIPPED_PAGE] });
    await flushPromises();

    expect(
      wrapper
        .get('[data-test="exam-workspace-open-lineage-b"]')
        .find('[data-test="exam-workspace-notes"]')
        .exists(),
    ).toBe(false);
    expect(wrapper.text()).toContain(ONE_SKIPPED_PAGE);
  });

  it("shows no notes list when the open exam has no notes", async () => {
    const wrapper = mountDrawer({ currentLineageId: "lineage-a", notes: [] });
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-notes"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-open-lineage-a"]').text()).toContain("Öppet");
  });
});
