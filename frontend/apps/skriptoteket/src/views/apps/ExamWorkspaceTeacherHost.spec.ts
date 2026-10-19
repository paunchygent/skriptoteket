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
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceDocumentResponse } from "../../api/examWorkspace";
import ExamWorkspaceTeacherHost from "./ExamWorkspaceTeacherHost.vue";
import type { StoredGuestDraft } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import { newGuestDraft } from "./exam-workspace/examWorkspaceGuestDraft";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { buildParentDocument } from "./exam-workspace/examWorkspaceParentDocument.specSupport";
import { buildResponse } from "./exam-workspace/useExamWorkspaceDocument.specSupport";

// The host's whole job is choosing the store, so the view is stubbed and its props read.
vi.mock("./ExamWorkspaceView.vue", () => ({
  default: { name: "ExamWorkspaceViewStub", props: ["store"], template: "<div />" },
}));

const routeMocks = vi.hoisted(() => ({
  query: {} as Record<string, string | undefined>,
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

const storageMocks = vi.hoisted(() => ({
  failLoad: false,
  stored: null as StoredGuestDraft | null,
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
    storageMocks.failLoad = false;
    storageMocks.stored = null;
    routeMocks.query = {};
    routeMocks.replace.mockReset();
    apiMocks.importGuestDraft.mockReset();
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
});
