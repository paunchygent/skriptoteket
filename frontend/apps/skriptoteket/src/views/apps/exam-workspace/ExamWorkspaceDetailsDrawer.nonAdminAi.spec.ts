/**
 * The details drawer's "Föreslå innehåll" button runs for every signed-in
 * user.
 *
 * Expected behavior:
 *   With role "user" or "contributor" no admin-only note shows, the button
 *   is enabled once the course content is loaded and the exam is saved, and
 *   clicking emits the suggestion request.
 */

import { flushPromises, mount } from "@vue/test-utils";
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

/** Distinctive fragment of the removed admin-only note; the full note must not render. */
const REMOVED_ADMIN_NOTE = "bara tillgängliga för administratörer";

const apiMocks = vi.hoisted(() => ({
  getExamCourseCatalog: vi.fn(),
  getExamCourseContent: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

type Role = "user" | "contributor";

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
      plugins: [pinia, examWorkspaceProvidersPlugin()],
    },
  });
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
  apiMocks.getExamCourseCatalog.mockReset().mockResolvedValue(CATALOG);
  apiMocks.getExamCourseContent.mockReset().mockResolvedValue(CONTENT);
});

describe("ExamWorkspaceDetailsDrawer non-admin AI", () => {
  it.each(["user", "contributor"] as const)(
    "leaves the content button working without the admin-only note for role %s",
    async (role) => {
      signIn(pinia, role);
      const wrapper = mountDrawer(pinia);
      await flushPromises();

      expect(wrapper.text()).not.toContain(REMOVED_ADMIN_NOTE);
      const button = wrapper.get('[data-test="exam-workspace-content-suggest"]');
      expect(button.attributes("disabled")).toBeUndefined();
      expect(button.attributes("title")).not.toBe(REMOVED_ADMIN_NOTE);
      await button.trigger("click");
      expect(wrapper.emitted("suggestContent")).toHaveLength(1);
      wrapper.unmount();
    },
  );
});
