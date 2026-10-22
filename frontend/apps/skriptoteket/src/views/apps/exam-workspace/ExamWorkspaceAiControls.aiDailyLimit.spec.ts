/**
 * Exam workspace AI controls under the daily AI limit.
 *
 * Expected behavior:
 *   Once the page-session limit is marked, every AI control is disabled and
 *   shows that limit's inline note next to it: the header suggest-all
 *   button, the export-blocker key buttons, the details-drawer content
 *   button, the Word import in the Öppna drawer, and the per-question retry.
 *   The user's own share names the user note; the pool and the ceiling name
 *   the app note. Without the limit, today's behavior is unchanged. No toast
 *   belongs to this path.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { DOMWrapper, VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Plugin } from "vue";

import type {
  ExamCourse,
  ExamCourseCatalogResponse,
  ExamCourseContent,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import { buildDocument } from "../ExamWorkspaceSlice.specSupport";
import AiDailyLimitNote from "./AiDailyLimitNote.vue";
import ExamWorkspaceDetailsDrawer from "./ExamWorkspaceDetailsDrawer.vue";
import ExamWorkspaceExportBlockers from "./ExamWorkspaceExportBlockers.vue";
import ExamWorkspaceHeader from "./ExamWorkspaceHeader.vue";
import ExamWorkspaceImportBox from "./ExamWorkspaceImportBox.vue";
import ExamWorkspaceOpenDrawer from "./ExamWorkspaceOpenDrawer.vue";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import {
  EXAM_WORKSPACE_UNREADABLE_FILES_KEY,
  useExamWorkspaceUnreadableFiles,
} from "./useExamWorkspaceUnreadableFiles";
import type { AiDailyLimit } from "./aiDailyLimit";
import {
  aiLimitNote,
  markAiDailyLimit,
  resetAiDailyLimitForTests,
} from "./aiDailyLimit";

const apiMocks = vi.hoisted(() => ({
  getExamCourseCatalog: vi.fn(),
  getExamCourseContent: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

const unreadableApiMocks = vi.hoisted(() => ({
  downloadSavedExamFile: vi.fn(),
  listUnreadableExamWorkspaceDocuments: vi.fn(),
  removeSavedExamFile: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceUnreadableFiles", () => unreadableApiMocks);

type Role = "admin";

const COURSE: ExamCourse = {
  code: "ENGENG05",
  key: "eng5",
  name: "Engelska 5",
  reform: "GY11",
  school_form: "gymnasiet",
  subject_code: "ENG",
  subject_name: "Engelska",
};

const CATALOG: ExamCourseCatalogResponse = {
  courses: [COURSE],
  generated_at: "2026-10-18T00:00:00Z",
  registered_course_keys: [],
};

const CONTENT: ExamCourseContent = {
  course_key: "eng5",
  items: [{ id: "c1", text: "Centralt innehåll" }],
};

const LIMIT_CASES: Array<{ limit: AiDailyLimit; note: string }> = [
  { limit: "user_share", note: aiLimitNote("user_share") },
  { limit: "pool", note: aiLimitNote("pool") },
  { limit: "usd_ceiling", note: aiLimitNote("usd_ceiling") },
];

function signIn(pinia: Pinia, role: Role): void {
  setActivePinia(pinia);
  useAuthStore().user = { id: "u1", email: "u@example.test", role, auth_provider: "local" };
}

function findLimitNotes(wrapper: VueWrapper, note: string): DOMWrapper<Element>[] {
  return wrapper
    .findAll("p, small, span")
    .filter((node) => node.text().trim() === note);
}

function keyBlocker(itemId: string, label: string): ExamWorkspaceBlockerEntry {
  return {
    fix: "suggest_key",
    focus: null,
    itemId,
    label,
    problem: "facit saknas",
    reason: "missing_answer_key",
  };
}

function courseDocument(): NativeExamDocument {
  return { ...buildDocument(), header: { tags: [], course: { key: "eng5", name: "Engelska 5" } } };
}

function reviewItem(): NativeExamItem {
  return buildFreeTextItem(1, {
    retry_source: {
      chunks: [],
      context_chunks: [],
      key_chunks: [],
      label_kind: "gap_fill",
      owned_context_anchors: [],
    },
    review: {
      confidence: null,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_required",
    },
    import_record: {
      original_wording: { question_text: "Förklara begreppet.", answer_key_text: null },
      steps: [],
    },
  });
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
  resetAiDailyLimitForTests();
  apiMocks.getExamCourseCatalog.mockReset().mockResolvedValue(CATALOG);
  apiMocks.getExamCourseContent.mockReset().mockResolvedValue(CONTENT);
  unreadableApiMocks.downloadSavedExamFile.mockReset();
  unreadableApiMocks.removeSavedExamFile.mockReset();
  unreadableApiMocks.listUnreadableExamWorkspaceDocuments
    .mockReset()
    .mockResolvedValue({ documents: [] });
});

describe("AiDailyLimitNote", () => {
  it.each(LIMIT_CASES)("renders the $limit note", ({ limit, note }) => {
    resetAiDailyLimitForTests();
    markAiDailyLimit(limit);
    const wrapper = mount(AiDailyLimitNote);
    expect(wrapper.get('[data-test="ai-daily-limit-note"]').text()).toBe(note);
    wrapper.unmount();
  });
});

describe("exam workspace AI controls under the daily limit", () => {
  it.each(LIMIT_CASES)("disables the header suggest-all button and shows the $limit note", async ({ limit, note }) => {
    signIn(pinia, "admin");
    markAiDailyLimit(limit);
    const wrapper = mount(ExamWorkspaceHeader, {
      props: {
        title: "Prov 1",
        saveState: "saved",
        saveText: "Sparat",
        saveTitle: null,
        courseLabel: null,
        total: 0,
        detailsOpen: false,
        openDrawerOpen: false,
        canRename: true,
        canSaveAs: true,
        suggestBusy: false,
        suggestDisabled: false,
        isPhone: false,
        previewOpen: false,
        newExamBusy: false,
      },
      global: { plugins: [pinia, examWorkspaceProvidersPlugin()] },
    });

    const button = wrapper.get('[data-test="exam-workspace-suggest-all"]');
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.attributes("title")).toBe(note);
    const notes = findLimitNotes(wrapper, note);
    expect(notes).toHaveLength(1);
    expect(notes[0]!.text()).toBe(note);
    await button.trigger("click");
    expect(wrapper.emitted("suggestAll")).toBeUndefined();
    wrapper.unmount();
  });

  it.each(LIMIT_CASES)("disables the export-blocker key buttons and shows the $limit note once", async ({ limit, note }) => {
    signIn(pinia, "admin");
    markAiDailyLimit(limit);
    const wrapper = mount(ExamWorkspaceExportBlockers, {
      props: {
        blockers: [keyBlocker("item_001", "1"), keyBlocker("item_002", "2")],
        fixDisabled: false,
        suggestBusy: false,
        testId: "exam-workspace-blockers",
      },
      global: { plugins: [pinia, examWorkspaceProvidersPlugin()] },
    });

    expect(findLimitNotes(wrapper, note)).toHaveLength(1);
    const all = wrapper.get('[data-test="exam-workspace-blocker-suggest-all"]');
    expect(all.attributes("disabled")).toBeDefined();
    expect(all.attributes("title")).toBe(note);
    await all.trigger("click");
    expect(wrapper.emitted("suggestAll")).toBeUndefined();
    const fix = wrapper.get('[data-test="exam-workspace-blocker-fix-item_001"]');
    expect(fix.attributes("disabled")).toBeDefined();
    await fix.trigger("click");
    expect(wrapper.emitted("fix")).toBeUndefined();
    wrapper.unmount();
  });

  it.each(LIMIT_CASES)("disables the details-drawer content button and shows the $limit note", async ({ limit, note }) => {
    signIn(pinia, "admin");
    markAiDailyLimit(limit);
    const wrapper = mount(ExamWorkspaceDetailsDrawer, {
      props: {
        document: courseDocument(),
        summary: buildSavedExamSummary({ course_key: "eng5" }),
        renameFile: async () => null,
        renameFailure: null,
        disabled: false,
        dirty: false,
        contentBusy: false,
        contentMessage: null,
        questionLabel: () => null,
      },
      global: { plugins: [pinia, examWorkspaceProvidersPlugin()] },
    });
    await flushPromises();

    expect(findLimitNotes(wrapper, note)).toHaveLength(1);
    const button = wrapper.get('[data-test="exam-workspace-content-suggest"]');
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.attributes("title")).toBe(note);
    await button.trigger("click");
    expect(wrapper.emitted("suggestContent")).toBeUndefined();
    wrapper.unmount();
  });

  it.each(LIMIT_CASES)("hides the Word format and shows the $limit note in the Öppna drawer", async ({ limit, note }) => {
    signIn(pinia, "admin");
    markAiDailyLimit(limit);
    setActivePinia(pinia);
    const unreadable = useExamWorkspaceUnreadableFiles();
    const provideUnreadable: Plugin = {
      install(app) {
        app.provide(EXAM_WORKSPACE_UNREADABLE_FILES_KEY, unreadable);
      },
    };
    const wrapper = mount(ExamWorkspaceOpenDrawer, {
      props: {
        conversionError: null,
        conversionMessage: null,
        conversionElapsed: null,
        conversionProgress: null,
        currentExports: [],
        currentLineageId: null,
        documents: [],
        importBlocked: false,
        isBusy: false,
        isOpenBlockedByOtherOperation: false,
        isConverting: false,
        isDirty: false,
        notes: [],
        ordering: "newest",
        saveDetail: null,
        saveState: "saved",
        sourceFileError: null,
      },
      global: { plugins: [pinia, examWorkspaceProvidersPlugin(), provideUnreadable] },
    });
    await flushPromises();

    const formats = wrapper
      .findAll(".drop__format")
      .map((node) => node.text().trim());
    expect(formats).not.toContain("Word (.docx)");
    const notes = findLimitNotes(wrapper, note);
    expect(notes).toHaveLength(1);
    expect(
      wrapper.get('[data-test="exam-workspace-source-file-input"]').attributes("accept"),
    ).toBe(".dxe,.zip");
    wrapper.unmount();
  });

  it.each(LIMIT_CASES)("disables the per-question retry and shows the $limit note", async ({ limit, note }) => {
    signIn(pinia, "admin");
    markAiDailyLimit(limit);
    const wrapper = mount(ExamWorkspaceImportBox, {
      props: { item: reviewItem(), origin: "docx_import", open: true, disabled: false },
      global: { plugins: [pinia, examWorkspaceProvidersPlugin()] },
    });

    expect(wrapper.get('[data-test="exam-workspace-retry-kind"]').attributes("disabled"))
      .toBeDefined();
    expect(findLimitNotes(wrapper, note)).toHaveLength(1);
    const button = wrapper.get('[data-test="exam-workspace-retry"]');
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.attributes("title")).toBe(note);
    await button.trigger("click");
    expect(wrapper.emitted("retry")).toBeUndefined();
    wrapper.unmount();
  });
});
