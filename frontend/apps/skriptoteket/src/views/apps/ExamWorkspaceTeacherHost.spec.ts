/**
 * Signed-in exam workspace host.
 *
 * Expected behavior:
 *   The host mounts the workspace on the signed-in server store, but only
 *   after the guest handoff settles. With a stored browser draft the handoff
 *   posts it to Mina filer and the view mounts with `?document=<returned
 *   lineage>`; without a draft the route is untouched and no import runs.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type { ExamWorkspaceDocumentResponse } from "../../api/examWorkspace";
import { useToastStore } from "../../stores/toast";
import { triggerBrowserDownload } from "../../utils/browserDownload";
import ExamWorkspaceTeacherHost from "./ExamWorkspaceTeacherHost.vue";
import type { StoredGuestDraft } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import { newGuestDraft } from "./exam-workspace/examWorkspaceGuestDraft";
import {
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_VAULT_FULL_COPY,
} from "./exam-workspace/examWorkspaceFileNoticeCopy";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { buildParentDocument } from "./exam-workspace/examWorkspaceParentDocument.specSupport";
import { buildResponse } from "./exam-workspace/useExamWorkspaceDocument.specSupport";

// The host's whole job is choosing the store, so the view is stubbed and its props read.
vi.mock("./ExamWorkspaceView.vue", () => ({
  default: { name: "ExamWorkspaceViewStub", props: ["store"], template: "<div />" },
}));

// The download writes a Blob to the browser; the mock records its arguments.
vi.mock("../../utils/browserDownload", () => ({
  triggerBrowserDownload: vi.fn(),
}));

const routeMocks = vi.hoisted((): {
  query: Record<string, string | undefined>;
  replace: ReturnType<typeof vi.fn>;
} => ({
  query: {},
  replace: vi.fn(),
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRoute: () => ({ query: routeMocks.query }),
    useRouter: () => ({ replace: routeMocks.replace }),
  };
});

const storageMocks = vi.hoisted((): {
  failLoad: boolean;
  stored: StoredGuestDraft | null;
} => ({
  failLoad: false,
  stored: null,
}));

vi.mock("./exam-workspace/examWorkspaceGuestDraftStorage", () => ({
  createExamWorkspaceGuestDraftStorage: () => ({
    async clearIf(expectedCursor: string) {
      if (storageMocks.stored?.draft.cursor !== expectedCursor) {
        return false;
      }
      storageMocks.stored = null;
      return true;
    },
    async load() {
      if (storageMocks.failLoad) {
        throw new Error("lagringen är blockerad");
      }
      return storageMocks.stored;
    },
    async replaceIf(expectedCursor: string | null, next: StoredGuestDraft) {
      if ((storageMocks.stored?.draft.cursor ?? null) !== expectedCursor) {
        return false;
      }
      storageMocks.stored = next;
      return true;
    },
  }),
}));

const hostHooks = vi.hoisted((): {
  lockMode: "memory" | "unavailable";
  startOverride: null | (() => Promise<string | null>);
} => ({
  lockMode: "memory",
  startOverride: null,
}));

vi.mock("./exam-workspace/examWorkspaceGuestHandoffLock", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./exam-workspace/examWorkspaceGuestHandoffLock")>();
  return {
    ...actual,
    createWebGuestHandoffLock: () => {
      if (hostHooks.lockMode === "unavailable") {
        return {
          run: (): Promise<never> => {
            throw new actual.GuestHandoffLockUnavailableError("Web Locks are unavailable.");
          },
        };
      }
      return actual.createInMemoryGuestHandoffLock();
    },
  };
});

vi.mock("./exam-workspace/useExamWorkspaceGuestHandoffController", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("./exam-workspace/useExamWorkspaceGuestHandoffController")>();
  return {
    ...actual,
    useExamWorkspaceGuestHandoffController: (
      ...args: Parameters<typeof actual.useExamWorkspaceGuestHandoffController>
    ) => {
      const controller = actual.useExamWorkspaceGuestHandoffController(...args);
      if (hostHooks.startOverride !== null) {
        const start = hostHooks.startOverride;
        return { ...controller, start };
      }
      return controller;
    },
  };
});

const apiMocks = vi.hoisted(() => ({
  importGuestDraft: vi.fn(),
}));

vi.mock("../../api/examWorkspace", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/examWorkspace")>()),
  importExamWorkspaceGuestDraft: apiMocks.importGuestDraft,
}));

const GUEST_IDS = {
  now: () => "2026-10-18T10:00:00.000Z",
  uuid: () => "10000000-0000-4000-8000-000000000001",
};

function seatStoredDraft(): StoredGuestDraft {
  const draft = newGuestDraft(buildParentDocument(), GUEST_IDS, []);
  storageMocks.stored = { assets: {}, draft };
  return storageMocks.stored;
}

function handoffResponse(lineageId: string): ExamWorkspaceDocumentResponse {
  const response = buildResponse();
  return { ...response, summary: { ...response.summary, lineage_id: lineageId } };
}

describe("ExamWorkspaceTeacherHost", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    storageMocks.failLoad = false;
    storageMocks.stored = null;
    routeMocks.query = {};
    routeMocks.replace.mockReset();
    apiMocks.importGuestDraft.mockReset();
    vi.mocked(triggerBrowserDownload).mockClear();
    hostHooks.lockMode = "memory";
    hostHooks.startOverride = null;
  });

  it("mounts the workspace on the signed-in server store", async () => {
    const wrapper = mount(ExamWorkspaceTeacherHost);
    await flushPromises();

    const view = wrapper.findComponent({ name: "ExamWorkspaceViewStub" });
    expect(view.exists()).toBe(true);
    expect(view.props("store")).toBe(serverExamWorkspaceStore);

    wrapper.unmount();
  });

  it("opens the handed-off exam after the handoff settles", async () => {
    seatStoredDraft();
    apiMocks.importGuestDraft.mockResolvedValue(handoffResponse("lineage-new"));
    const wrapper = mount(ExamWorkspaceTeacherHost);

    expect(wrapper.findComponent({ name: "ExamWorkspaceViewStub" }).exists()).toBe(false);

    await flushPromises();

    expect(apiMocks.importGuestDraft).toHaveBeenCalledTimes(1);
    expect(routeMocks.replace).toHaveBeenCalledWith({ query: { document: "lineage-new" } });
    const view = wrapper.findComponent({ name: "ExamWorkspaceViewStub" });
    expect(view.exists()).toBe(true);
    expect(view.props("store")).toBe(serverExamWorkspaceStore);

    wrapper.unmount();
  });

  it("mounts with the route untouched and no import without a stored draft", async () => {
    routeMocks.query = { document: "named-lineage" };
    const wrapper = mount(ExamWorkspaceTeacherHost);
    await flushPromises();

    expect(apiMocks.importGuestDraft).not.toHaveBeenCalled();
    expect(routeMocks.replace).not.toHaveBeenCalled();
    expect(wrapper.findComponent({ name: "ExamWorkspaceViewStub" }).exists()).toBe(true);

    wrapper.unmount();
  });

  it("mounts with the route untouched when the stored draft cannot be read", async () => {
    storageMocks.failLoad = true;
    routeMocks.query = { document: "named-lineage" };
    const wrapper = mount(ExamWorkspaceTeacherHost);
    await flushPromises();

    expect(apiMocks.importGuestDraft).not.toHaveBeenCalled();
    expect(routeMocks.replace).not.toHaveBeenCalled();
    expect(wrapper.findComponent({ name: "ExamWorkspaceViewStub" }).exists()).toBe(true);

    wrapper.unmount();
  });

  it("a) a permanently rejected draft renders the view with a download/remove notice", async () => {
    seatStoredDraft();
    apiMocks.importGuestDraft.mockRejectedValue(
      new ApiError({ code: "DOCUMENT_SCHEMA_OUTDATED", message: "outdated", status: 422 }),
    );
    const wrapper = mount(ExamWorkspaceTeacherHost);
    await flushPromises();

    expect(wrapper.findComponent({ name: "ExamWorkspaceViewStub" }).exists()).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY,
    );
    expect(useToastStore().toasts).toEqual([]);

    await wrapper.get('[data-test="exam-workspace-file-notice-download"]').trigger("click");
    await flushPromises();
    expect(triggerBrowserDownload).toHaveBeenCalledTimes(1);
    expect(vi.mocked(triggerBrowserDownload).mock.calls[0]?.[1]).toBe("English 1.zip");

    await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
    await flushPromises();
    expect(storageMocks.stored).toBeNull();
    expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(false);

    wrapper.unmount();
  });

  it("b) a full Mina filer shows the vault notice and retry posts again", async () => {
    seatStoredDraft();
    apiMocks.importGuestDraft
      .mockRejectedValueOnce(
        new ApiError({
          code: "VALIDATION_ERROR",
          details: { reason: "vault_full" },
          message: "full",
          status: 422,
        }),
      )
      .mockResolvedValue(handoffResponse("lineage-new"));
    const wrapper = mount(ExamWorkspaceTeacherHost);
    await flushPromises();

    expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_GUEST_VAULT_FULL_COPY,
    );
    expect(wrapper.find('[data-test="exam-workspace-file-notice-retry"]').exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-file-notice-retry"]').trigger("click");
    await flushPromises();
    expect(apiMocks.importGuestDraft).toHaveBeenCalledTimes(2);

    wrapper.unmount();
  });

  it("c) a draft without its position snapshot still renders with the permanent notice", async () => {
    const seated = seatStoredDraft();
    seated.draft.position_step_id = "missing-step";
    const wrapper = mount(ExamWorkspaceTeacherHost);
    await flushPromises();

    expect(apiMocks.importGuestDraft).not.toHaveBeenCalled();
    expect(wrapper.findComponent({ name: "ExamWorkspaceViewStub" }).exists()).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY,
    );

    wrapper.unmount();
  });

  it("d) a remount after a permanent rejection makes no second POST", async () => {
    seatStoredDraft();
    apiMocks.importGuestDraft.mockRejectedValue(
      new ApiError({ code: "DOCUMENT_SCHEMA_OUTDATED", message: "outdated", status: 422 }),
    );

    const first = mount(ExamWorkspaceTeacherHost);
    await flushPromises();
    expect(apiMocks.importGuestDraft).toHaveBeenCalledTimes(1);
    first.unmount();

    const second = mount(ExamWorkspaceTeacherHost);
    await flushPromises();
    expect(apiMocks.importGuestDraft).toHaveBeenCalledTimes(1);
    expect(second.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY,
    );
    second.unmount();
  });

  it("e) an unavailable lock still renders the view with the permanent notice", async () => {
    hostHooks.lockMode = "unavailable";
    seatStoredDraft();
    const wrapper = mount(ExamWorkspaceTeacherHost);
    await flushPromises();

    try {
      expect(apiMocks.importGuestDraft).not.toHaveBeenCalled();
      expect(wrapper.findComponent({ name: "ExamWorkspaceViewStub" }).exists()).toBe(true);
      expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
        EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY,
      );
      expect(wrapper.find('[data-test="exam-workspace-file-notice-retry"]').exists()).toBe(
        false,
      );
    } finally {
      wrapper.unmount();
    }
  });

  it("f) the view still renders when start throws unexpectedly", async () => {
    hostHooks.startOverride = async () => {
      throw new Error("the handoff crashed");
    };
    const onError = vi.fn();
    const wrapper = mount(ExamWorkspaceTeacherHost, {
      global: { config: { errorHandler: onError } },
    });
    await flushPromises();

    try {
      expect(wrapper.findComponent({ name: "ExamWorkspaceViewStub" }).exists()).toBe(true);
      expect(onError).toHaveBeenCalledTimes(1);
    } finally {
      wrapper.unmount();
    }
  });
});
