/**
 * Guest exam workspace host.
 *
 * Expected behavior:
 *   The public exam-converter URL renders the browser-only notice and the
 *   shared exam workspace on a guest store (teacher null, guest startBlank
 *   present) without calling the server. A stored draft opens through the
 *   view's `?document=` address, even when the URL names another id, while
 *   no draft leaves the address untouched. A signed-in visitor is sent to
 *   the signed-in workspace and sees no guest workspace. A guest limit
 *   surfaces the sign-in prompt with a login link back to /apps/exam-workspace.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { useAuthStore } from "../../stores/auth";
import ExamWorkspaceGuestHost from "./ExamWorkspaceGuestHost.vue";
import {
  GUEST_BROWSER_ONLY_NOTICE,
  GUEST_LIMIT_SIGN_IN,
} from "./exam-workspace/examWorkspaceGuestCopy";
import type { StoredGuestDraft } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import { newGuestDraft } from "./exam-workspace/examWorkspaceGuestDraft";
import type { ExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { buildParentDocument } from "./exam-workspace/examWorkspaceParentDocument.specSupport";

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
  stored: null as StoredGuestDraft | null,
}));

vi.mock("./exam-workspace/examWorkspaceGuestDraftStorage", () => ({
  createExamWorkspaceGuestDraftStorage: () => ({
    async clear() {
      storageMocks.stored = null;
    },
    async load() {
      return storageMocks.stored;
    },
    async save(next: StoredGuestDraft) {
      storageMocks.stored = next;
    },
  }),
}));

const apiMocks = vi.hoisted(() => ({
  createBlank: vi.fn(),
}));

vi.mock("../../api/publicExamWorkspace", () => ({
  createPublicExamWorkspaceBlank: apiMocks.createBlank,
}));

vi.mock("./ExamWorkspaceView.vue", () => ({
  default: {
    name: "ExamWorkspaceViewStub",
    props: { store: { type: Object, required: true } },
    template: "<div data-test='exam-workspace-view-stub' />",
  },
}));

const GUEST_IDS = {
  now: () => "2026-10-18T10:00:00.000Z",
  uuid: () => "10000000-0000-4000-8000-000000000001",
};

function seedDraft(): StoredGuestDraft {
  const draft = newGuestDraft(buildParentDocument(), GUEST_IDS);
  storageMocks.stored = { assets: {}, draft };
  return storageMocks.stored;
}

function guestStoreOf(wrapper: ReturnType<typeof mount>): ExamWorkspaceStore {
  const stub = wrapper.findComponent({ name: "ExamWorkspaceViewStub" });
  const props = stub.props() as { store: ExamWorkspaceStore };
  return props.store;
}

describe("ExamWorkspaceGuestHost", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    storageMocks.stored = null;
    routeMocks.query = {};
    routeMocks.replace.mockReset();
    apiMocks.createBlank.mockReset();
  });

  it("renders the browser-only notice and the shared workspace on the guest store", async () => {
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    expect(wrapper.find("[data-test='exam-workspace-guest-browser-notice']").text()).toBe(
      GUEST_BROWSER_ONLY_NOTICE,
    );
    const store = guestStoreOf(wrapper);
    expect(store.teacher).toBeNull();
    expect(typeof store.guest?.startBlank).toBe("function");
    expect(routeMocks.replace).not.toHaveBeenCalled();
    expect(apiMocks.createBlank).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("opens the stored draft through the view's document address", async () => {
    const lineageId = seedDraft().draft.lineage_id;
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    expect(routeMocks.replace).toHaveBeenCalledWith({
      query: { document: lineageId },
    });

    wrapper.unmount();
  });

  it("replaces a foreign document id in the address with the stored draft", async () => {
    const lineageId = seedDraft().draft.lineage_id;
    routeMocks.query = { document: "other-lineage" };
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    expect(routeMocks.replace).toHaveBeenCalledWith({
      query: { document: lineageId },
    });

    wrapper.unmount();
  });

  it("leaves the address untouched without a draft", async () => {
    routeMocks.query = { document: "named-lineage" };
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    expect(routeMocks.replace).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("sends a signed-in visitor to the signed-in workspace without the guest workspace", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const authStore = useAuthStore();
    authStore.user = {
      auth_provider: "huleedu",
      email: "teacher@example.com",
      id: "user-1",
      role: "user",
    };
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [pinia] },
    });
    await flushPromises();

    expect(routeMocks.replace).toHaveBeenCalledWith({ name: "exam-workspace" });
    expect(wrapper.find("[data-test='exam-workspace-view-stub']").exists()).toBe(false);

    wrapper.unmount();
  });

  it("sends the visitor away when sign-in arrives after bootstrap", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const authStore = useAuthStore();
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [pinia] },
    });
    await flushPromises();
    expect(wrapper.find("[data-test='exam-workspace-view-stub']").exists()).toBe(true);

    authStore.user = {
      auth_provider: "huleedu",
      email: "teacher@example.com",
      id: "user-1",
      role: "user",
    };
    await flushPromises();

    expect(routeMocks.replace).toHaveBeenCalledWith({ name: "exam-workspace" });

    wrapper.unmount();
  });

  it("shows the sign-in prompt with a workspace login return when a guest limit is hit", async () => {
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();
    expect(wrapper.find("[data-test='exam-workspace-sign-in-prompt']").exists()).toBe(false);

    const limit = new ApiError({
      code: "TOO_MANY_REQUESTS",
      details: { bucket: "guest_edit", reason: "caller_limit" },
      message: "Gränsen för gäster är nådd. Logga in för att fortsätta.",
      status: 429,
    });
    apiMocks.createBlank.mockRejectedValueOnce(limit);
    await guestStoreOf(wrapper)
      .guest?.startBlank()
      .catch((caught: unknown) => caught);
    await flushPromises();

    const prompt = wrapper.find("[data-test='exam-workspace-sign-in-prompt']");
    expect(prompt.exists()).toBe(true);
    expect(prompt.text()).toContain(GUEST_LIMIT_SIGN_IN);
    const login = prompt.find("[data-test='exam-workspace-sign-in-prompt-login']");
    expect(login.attributes("href") ?? "").toContain(
      `next=${encodeURIComponent("/apps/exam-workspace")}`,
    );

    wrapper.unmount();
  });
});
