/**
 * The details drawer's "Föreslå innehåll" button is admin-only until the AI
 * spend cap ships (TASK-SKRIPT-REP-0044 L3).
 *
 * Expected behavior:
 *   With role "user" or "contributor" the button is disabled, its title and the
 *   inline note carry the admin-only text, and clicking emits nothing. With role
 *   "admin" or "superuser" the note is gone and the button works once the course
 *   content is loaded and the exam is saved.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { DOMWrapper, VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamCourseCatalogResponse,
  ExamCourseContent,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { AI_ADMIN_ONLY_NOTE } from "../../../composables/useAiAccess";
import { useAuthStore } from "../../../stores/auth";
import { buildDocument } from "../ExamWorkspaceSlice.specSupport";
import ExamWorkspaceDetailsDrawer from "./ExamWorkspaceDetailsDrawer.vue";
import { EXAM_WORKSPACE_STORE_KEY, serverExamWorkspaceStore } from "./examWorkspaceStore";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamCourseCatalog: vi.fn(),
  getExamCourseContent: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

type Role = "user" | "contributor" | "admin" | "superuser";

function findNotes(wrapper: VueWrapper): DOMWrapper<Element>[] {
  return wrapper
    .findAll("p, small, span")
    .filter((node) => node.text().trim() === AI_ADMIN_ONLY_NOTE);
}

const COURSE = {
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
} as ExamCourseCatalogResponse;

const CONTENT = {
  course_key: "eng5",
  items: [{ id: "c1", text: "Centralt innehåll" }],
} as unknown as ExamCourseContent;

function courseDocument(): NativeExamDocument {
  return { ...buildDocument(), header: { tags: [], course: { key: "eng5", name: "Engelska 5" } } };
}

function signIn(pinia: Pinia, role: Role): void {
  setActivePinia(pinia);
  useAuthStore().user = { id: "u1", email: "u@example.test", role, auth_provider: "local" };
}

function mountDrawer(pinia: Pinia) {
  return mount(ExamWorkspaceDetailsDrawer, {
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
    global: {
      plugins: [pinia],
      provide: { [EXAM_WORKSPACE_STORE_KEY as symbol]: serverExamWorkspaceStore },
    },
  });
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
  apiMocks.getExamCourseCatalog.mockReset().mockResolvedValue(CATALOG);
  apiMocks.getExamCourseContent.mockReset().mockResolvedValue(CONTENT);
});

describe("ExamWorkspaceDetailsDrawer AI gate", () => {
  it.each(["user", "contributor"] as const)(
    "disables the content button, shows the note and emits nothing for role %s",
    async (role) => {
      signIn(pinia, role);
      const wrapper = mountDrawer(pinia);
      await flushPromises();

      const notes = findNotes(wrapper);
      expect(notes).toHaveLength(1);
      const note = notes[0]!;
      expect(note.text()).toBe(AI_ADMIN_ONLY_NOTE);

      const button = wrapper.get('[data-test="exam-workspace-content-suggest"]');
      expect(button.attributes("disabled")).toBeDefined();
      expect(button.attributes("title")).toBe(AI_ADMIN_ONLY_NOTE);
      expect(button.attributes("aria-describedby")).toBe(note.attributes("id"));
      await button.trigger("click");
      expect(wrapper.emitted("suggestContent")).toBeUndefined();
      wrapper.unmount();
    },
  );

  it.each(["admin", "superuser"] as const)(
    "leaves the content button working without the note for role %s",
    async (role) => {
      signIn(pinia, role);
      const wrapper = mountDrawer(pinia);
      await flushPromises();

      expect(findNotes(wrapper)).toHaveLength(0);
      const button = wrapper.get('[data-test="exam-workspace-content-suggest"]');
      expect(button.attributes("disabled")).toBeUndefined();
      await button.trigger("click");
      expect(wrapper.emitted("suggestContent")).toHaveLength(1);
      wrapper.unmount();
    },
  );
});
