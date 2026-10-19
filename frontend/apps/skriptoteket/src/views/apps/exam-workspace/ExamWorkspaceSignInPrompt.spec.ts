/**
 * Exam workspace guest sign-in prompt.
 *
 * Expected behavior:
 *   The prompt shows the given message and a "Logga in" link into the shared
 *   auth ceremony that returns to the signed-in exam workspace. Following the
 *   link settles the pending edit into browser storage through `depart` first:
 *   a settled departure navigates to the login href, while a failed settle
 *   stays on the page and shows the inline failure copy under the message.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { ref } from "vue";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { createTestRouter, mountWithContext } from "../../../test/utils";
import ExamWorkspaceView from "../ExamWorkspaceView.vue";
import { GUEST_LIMIT_SIGN_IN } from "./examWorkspaceGuestCopy";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import ExamWorkspaceSignInPrompt from "./ExamWorkspaceSignInPrompt.vue";
import {
  EXAM_WORKSPACE_LAYOUT_KEY,
  type ExamWorkspaceLayout,
} from "./useExamWorkspaceLayout";

const DEPARTURE_FAILURE_COPY =
  "Det gick inte att spara dina senaste ändringar i webbläsaren. Försök igen.";

const apiMocks = vi.hoisted(() => ({
  addExamWorkspaceChild: vi.fn(),
  changeExamWorkspaceItemType: vi.fn(),
  copyExamWorkspaceDocument: vi.fn(),
  createEmptyExamWorkspacePart: vi.fn(),
  createExamWorkspaceParent: vi.fn(),
  deleteExamWorkspaceChild: vi.fn(),
  deleteExamWorkspaceParent: vi.fn(),
  downloadExamWorkspaceExport: vi.fn(),
  examWorkspaceAssetUrl: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamCourseCatalog: vi.fn(),
  getExamCourseContent: vi.fn(),
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceContentSuggestions: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  groupExamWorkspaceItems: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  moveExamWorkspaceItem: vi.fn(),
  reorderExamWorkspaceChildren: vi.fn(),
  requestExamWorkspaceAnswerKeySuggestions: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
  requestExamWorkspaceContentSuggestions: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  saveExamWorkspaceExport: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  updateExamListOrdering: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../api/examWorkspace")>()),
  ...apiMocks,
}));

vi.mock("../../../api/examWorkspaceStructureCommands", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  addExamWorkspaceChild: apiMocks.addExamWorkspaceChild,
  changeExamWorkspaceItemType: apiMocks.changeExamWorkspaceItemType,
  createEmptyPublicExamWorkspacePart: apiMocks.createEmptyExamWorkspacePart,
  createExamWorkspaceParent: apiMocks.createExamWorkspaceParent,
  deleteExamWorkspaceChild: apiMocks.deleteExamWorkspaceChild,
  deleteExamWorkspaceParent: apiMocks.deleteExamWorkspaceParent,
  groupExamWorkspaceItems: apiMocks.groupExamWorkspaceItems,
  moveExamWorkspaceItem: apiMocks.moveExamWorkspaceItem,
  reorderExamWorkspaceChildren: apiMocks.reorderExamWorkspaceChildren,
}));

vi.mock("../../../api/vault", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../api/vault")>()),
  renameVaultFile: vi.fn(),
}));

beforeAll(() => {
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:picture");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

function setupGuest() {
  const storage = createInMemoryExamWorkspaceGuestDraftStorage();
  const publicMocks = {
    addPublicExamWorkspaceChild: vi.fn(),
    changePublicExamWorkspaceItemType: vi.fn(),
    createEmptyPublicExamWorkspacePart: vi.fn(),
    createPublicExamWorkspaceBlank: vi.fn(async () => ({
      document: buildParentDocument(),
      export_blockers: [],
    })),
    createPublicExamWorkspaceParent: vi.fn(),
    deletePublicExamWorkspaceChild: vi.fn(),
    deletePublicExamWorkspaceParent: vi.fn(),
    downloadPublicExamWorkspaceExport: vi.fn(),
    getPublicExamCourseCatalog: vi.fn(async () => ({
      courses: [],
      generated_at: "2026-10-18T00:00:00Z",
      registered_course_keys: [],
    })),
    getPublicExamWorkspaceExportChecklist: vi.fn(),
    groupPublicExamWorkspaceItems: vi.fn(),
    movePublicExamWorkspaceItem: vi.fn(),
    reorderPublicExamWorkspaceChildren: vi.fn(),
    requestPublicExamWorkspaceAnswerMisspellings: vi.fn(),
  };
  let counter = 0;
  const guest = createGuestExamWorkspaceStore({
    api: publicMocks,
    ids: {
      now: () => "2026-10-18T10:00:00.000Z",
      uuid: () => {
        counter += 1;
        return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
      },
    },
    onLimit: () => undefined,
    storage,
  });
  return { guest, publicMocks, storage };
}

const redirectMocks = vi.hoisted(() => ({
  redirectToSharedAuthCeremony: vi.fn(),
}));

vi.mock("../../../composables/auth/sharedAuthRedirect", () => ({
  redirectToSharedAuthCeremony: redirectMocks.redirectToSharedAuthCeremony,
}));

function takeRedirect() {
  redirectMocks.redirectToSharedAuthCeremony.mockClear();
  return redirectMocks.redirectToSharedAuthCeremony;
}

describe("ExamWorkspaceSignInPrompt", () => {
  it("renders the message and a login link returning to the signed-in workspace", () => {
    const wrapper = mount(ExamWorkspaceSignInPrompt, {
      props: { depart: async () => true, message: GUEST_LIMIT_SIGN_IN },
    });

    expect(wrapper.text()).toContain(GUEST_LIMIT_SIGN_IN);
    const login = wrapper.find("[data-test='exam-workspace-sign-in-prompt-login']");
    expect(login.exists()).toBe(true);
    expect(login.text()).toBe("Logga in");
    const href = login.attributes("href") ?? "";
    expect(href).toContain(`next=${encodeURIComponent("/apps/exam-workspace")}`);

    wrapper.unmount();
  });

  it("settles the pending edit before navigating to the login ceremony", async () => {
    const redirect = takeRedirect();
      const depart = vi.fn(async () => true);
      const wrapper = mount(ExamWorkspaceSignInPrompt, {
        props: { depart, message: GUEST_LIMIT_SIGN_IN },
      });
      const login = wrapper.find("[data-test='exam-workspace-sign-in-prompt-login']");
      const href = login.attributes("href") ?? "";

      await login.trigger("click");
      await flushPromises();

      expect(depart).toHaveBeenCalledTimes(1);
      expect(redirect).toHaveBeenCalledTimes(1);
      expect(redirect).toHaveBeenCalledWith(href);
      expect(
        wrapper.find("[data-test='exam-workspace-sign-in-prompt-error']").exists(),
      ).toBe(false);

      wrapper.unmount();
  });

  it("stays and shows the failure copy when the pending edit cannot be settled", async () => {
    const redirect = takeRedirect();
      const depart = vi.fn(async () => false);
      const wrapper = mount(ExamWorkspaceSignInPrompt, {
        props: { depart, message: GUEST_LIMIT_SIGN_IN },
      });

      await wrapper.find("[data-test='exam-workspace-sign-in-prompt-login']").trigger("click");
      await flushPromises();

      expect(depart).toHaveBeenCalledTimes(1);
      expect(redirect).not.toHaveBeenCalled();
      expect(
        wrapper.find("[data-test='exam-workspace-sign-in-prompt-error']").text(),
      ).toBe(DEPARTURE_FAILURE_COPY);

      wrapper.unmount();
  });

  describe("safe departure with the real guest workspace", () => {
    beforeEach(() => {
      for (const mock of Object.values(apiMocks)) {
        mock.mockReset();
      }
      document.body.replaceChildren();
      window.history.replaceState({}, "", "/");
    });

    it("stores the typed edit before navigating to the login ceremony", async () => {
      const redirect = takeRedirect();
        const { guest, storage } = setupGuest();
        const layout = ref<ExamWorkspaceLayout>("desktop");
        const wrapper = mountWithContext(ExamWorkspaceView, {
          props: { store: guest.store },
          global: {
            plugins: [createPinia(), createTestRouter()],
            provide: { [EXAM_WORKSPACE_LAYOUT_KEY]: layout },
          },
        });
        await flushPromises();

        await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
        await flushPromises();
        await wrapper.get('[data-test="exam-workspace-row-item_001"]').trigger("click");
        await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("5");
        await wrapper.get('[data-test="exam-workspace-suggest-all"]').trigger("click");
        await flushPromises();

        const prompt = wrapper.find('[data-test="exam-workspace-sign-in-prompt"]');
        expect(prompt.exists()).toBe(true);
        const login = prompt.find("[data-test='exam-workspace-sign-in-prompt-login']");
        const href = login.attributes("href") ?? "";

        await login.trigger("click");
        await flushPromises();

        expect(redirect).toHaveBeenCalledTimes(1);
        expect(redirect).toHaveBeenCalledWith(href);
        const stored = await storage.load();
        if (stored === null) {
          throw new Error("Expected the guest draft to be stored before navigation.");
        }
        const snapshots = [stored.draft.baseline, ...stored.draft.steps];
        const position = snapshots.find(
          (step) => step.step_id === stored.draft.position_step_id,
        );
        if (!position) {
          throw new Error("Expected the stored draft to hold its position snapshot.");
        }
        const edited = position.document.items.find((item) => item.item_id === "item_001");
        expect(edited?.points).toBe(5);

        wrapper.unmount();
    });

    it("keeps the working copy mounted when the settle fails", async () => {
      const redirect = takeRedirect();
        const { guest } = setupGuest();
        const layout = ref<ExamWorkspaceLayout>("desktop");
        const wrapper = mountWithContext(ExamWorkspaceView, {
          props: { store: guest.store },
          global: {
            plugins: [createPinia(), createTestRouter()],
            provide: { [EXAM_WORKSPACE_LAYOUT_KEY]: layout },
          },
        });
        await flushPromises();

        await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
        await flushPromises();

        // Fail every undo-step write the departure flush attempts.
        guest.store.shared.storeExamWorkspaceUndoStep = async () => {
          throw new Error("The browser storage is unavailable.");
        };
        await wrapper.get('[data-test="exam-workspace-row-item_001"]').trigger("click");
        await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("5");
        await wrapper.get('[data-test="exam-workspace-suggest-all"]').trigger("click");
        await flushPromises();

        const prompt = wrapper.find('[data-test="exam-workspace-sign-in-prompt"]');
        expect(prompt.exists()).toBe(true);
        await prompt.find("[data-test='exam-workspace-sign-in-prompt-login']").trigger("click");
        await flushPromises();

        expect(redirect).not.toHaveBeenCalled();
        expect(
          wrapper.find("[data-test='exam-workspace-sign-in-prompt-error']").text(),
        ).toBe(DEPARTURE_FAILURE_COPY);
        expect(wrapper.find('[data-test="exam-workspace-row-item_001"]').exists()).toBe(true);

        wrapper.unmount();
    });
  });
});
