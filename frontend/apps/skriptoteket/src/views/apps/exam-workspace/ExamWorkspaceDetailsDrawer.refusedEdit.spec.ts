/**
 * Refused Centralt innehåll ticks show the document state (TASK-SKRIPT-40-04-14 TK1).
 *
 * Defect:
 *   The Centralt innehåll checkbox binds `:checked` to the document tags and
 *   emits `set-tags` on change. When the parent refuses the change, the native
 *   checkbox has already flipped and Vue does not patch it back, because the
 *   bound value never changed. The tick looks set until the drawer remounts.
 *   Centralt innehåll ticks are exam metadata that categorise the exam; they
 *   are not grading criteria and stay apart from per-question
 *   Bedömningskriterier.
 *
 * Expected behavior:
 *   A refused tick resets the checkbox to the document state straight away
 *   (still unticked after remount with the same document), while an accepted
 *   tick stays ticked across remount. The suggestions hint reads the working
 *   document's course, not the saved summary: no course asks for a course
 *   first, a dirty document with a course waits for the save, and a stored
 *   document with a course shows no hint.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamCourse,
  ExamCourseCatalogResponse,
  ExamCourseContent,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { buildDocument } from "../ExamWorkspaceSlice.specSupport";
import ExamWorkspaceDetailsDrawer from "./ExamWorkspaceDetailsDrawer.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamCourseCatalog: vi.fn(),
  getExamCourseContent: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

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

const ENTRY_TEXT = "Reading and listening in English";
const CONTENT: ExamCourseContent = {
  course_key: "eng5",
  items: [
    { id: "c1", text: ENTRY_TEXT },
    { id: "c2", text: "Speaking and writing in English" },
  ],
};

const NO_COURSE_HINT = "Välj en kurs först.";
const DIRTY_HINT = "Vänta tills ändringarna har sparats. Förslagen görs från det sparade provet.";

function courseDocument(): NativeExamDocument {
  return { ...buildDocument(), header: { tags: [], course: { key: "eng5", name: "Engelska 5" } } };
}

function mountDrawer(options: {
  pinia: Pinia;
  document: NativeExamDocument;
  summaryCourseKey: string | null;
  dirty: boolean;
}): VueWrapper {
  return mount(ExamWorkspaceDetailsDrawer, {
    props: {
      document: options.document,
      summary: buildSavedExamSummary({ course_key: options.summaryCourseKey }),
      renameFile: async () => null,
      renameFailure: null,
      disabled: false,
      dirty: options.dirty,
      contentBusy: false,
      contentMessage: null,
      questionLabel: () => null,
    },
    global: {
      plugins: [options.pinia, examWorkspaceProvidersPlugin()],
    },
  });
}

const CONTENT_BOX = '[data-test="exam-workspace-content-c1"]';

function boxChecked(wrapper: VueWrapper): boolean {
  const box = wrapper.get(CONTENT_BOX).element;
  return box instanceof HTMLInputElement && box.checked;
}

function suggestTitle(wrapper: VueWrapper): string | undefined {
  return wrapper.get('[data-test="exam-workspace-content-suggest"]').attributes("title");
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  useAuthStore().user = { id: "u1", email: "u@example.test", role: "admin", auth_provider: "local" };
  apiMocks.getExamCourseCatalog.mockReset().mockResolvedValue(CATALOG);
  apiMocks.getExamCourseContent.mockReset().mockResolvedValue(CONTENT);
});

describe("ExamWorkspaceDetailsDrawer refused ticks", () => {
  it("resets a refused tick to the document state straight away and across remount", async () => {
    const document = courseDocument();
    const wrapper = mountDrawer({ pinia, document, summaryCourseKey: "eng5", dirty: false });
    await flushPromises();

    expect(boxChecked(wrapper)).toBe(false);
    await wrapper.get(CONTENT_BOX).setValue(true);
    await flushPromises();

    expect(wrapper.emitted("setTags")).toHaveLength(1);
    expect(boxChecked(wrapper)).toBe(false);
    wrapper.unmount();

    const reopened = mountDrawer({ pinia, document, summaryCourseKey: "eng5", dirty: false });
    await flushPromises();
    expect(boxChecked(reopened)).toBe(false);
    reopened.unmount();
  });

  it("keeps an accepted tick across remount", async () => {
    const document = courseDocument();
    const wrapper = mountDrawer({ pinia, document, summaryCourseKey: "eng5", dirty: false });
    await flushPromises();

    await wrapper.get(CONTENT_BOX).setValue(true);
    await flushPromises();
    expect(wrapper.emitted("setTags")).toHaveLength(1);

    const accepted: NativeExamDocument = {
      ...document,
      header: {
        ...document.header,
        tags: [{ id: "c1", origin: "teacher", question_ids: [], text: ENTRY_TEXT }],
      },
    };
    await wrapper.setProps({ document: accepted });
    await flushPromises();
    expect(boxChecked(wrapper)).toBe(true);
    wrapper.unmount();

    const reopened = mountDrawer({ pinia, document: accepted, summaryCourseKey: "eng5", dirty: false });
    await flushPromises();
    expect(boxChecked(reopened)).toBe(true);
    reopened.unmount();
  });
});

describe("ExamWorkspaceDetailsDrawer suggestions hint", () => {
  it("asks for a course first when the working document has none, even with a stale saved course", async () => {
    const document = { ...buildDocument(), header: { tags: [] } };
    const wrapper = mountDrawer({ pinia, document, summaryCourseKey: "eng5", dirty: false });
    await flushPromises();

    expect(suggestTitle(wrapper)).toBe(NO_COURSE_HINT);
    wrapper.unmount();
  });

  it("waits for the save when the working document has a course and is dirty", async () => {
    const wrapper = mountDrawer({
      pinia,
      document: courseDocument(),
      summaryCourseKey: null,
      dirty: true,
    });
    await flushPromises();

    expect(wrapper.text()).toContain(DIRTY_HINT);
    expect(suggestTitle(wrapper)).toBe(DIRTY_HINT);
    wrapper.unmount();
  });

  it("shows no hint when the working document has a course and is stored", async () => {
    const wrapper = mountDrawer({
      pinia,
      document: courseDocument(),
      summaryCourseKey: "eng5",
      dirty: false,
    });
    await flushPromises();

    expect(wrapper.text()).not.toContain(NO_COURSE_HINT);
    expect(wrapper.text()).not.toContain(DIRTY_HINT);
    expect(suggestTitle(wrapper)).toBeUndefined();
    wrapper.unmount();
  });
});
