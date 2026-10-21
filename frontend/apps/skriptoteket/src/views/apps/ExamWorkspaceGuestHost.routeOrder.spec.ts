/**
 * Guest host removal route order: the old document address clears before
 * the editor mounts (repairs R4).
 *
 * Expected behavior, all under the real Vue Router (memory history):
 *   A successful removal of the stored unreadable draft clears
 *   `?document=` before admission becomes readable, so the editor never
 *   mounts while the route still holds the removed lineage and never
 *   emits the ordinary open-failure toast after a removal that succeeded.
 *   A refused clear keeps deciding through the current slot: a newer
 *   readable draft opens with no failure toast, and an empty slot shows
 *   the empty start with no toast.
 *
 *   The view child below is the production address/document wiring, not a
 *   stub that does nothing: it runs the real useExamWorkspaceDocument and
 *   the real useExamWorkspaceAddress against the host's guest store, so a
 *   prematurely admitted editor would still run the ordinary open-error
 *   path the repair must avoid.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import Host from "./ExamWorkspaceGuestHost.vue";
import { useToastStore } from "../../stores/toast";
import { newGuestDraft } from "./exam-workspace/examWorkspaceGuestDraft";
import type { StoredGuestDraft } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import type { ExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { GUEST_BROWSER_ONLY_NOTICE } from "./exam-workspace/examWorkspaceGuestCopy";
import {
  createIds,
  exam,
  pictureExam,
} from "./exam-workspace/examWorkspaceGuestStore.specSupport";

const CURRENT_TOKEN = "native_exam_document_v11";
const OLD_TOKEN = "native_exam_document_v10";

const slot = vi.hoisted((): { stored: StoredGuestDraft | null } => ({ stored: null }));

vi.mock("./exam-workspace/examWorkspaceGuestDraftStorage", async (importOriginal) => ({
  ...(await importOriginal()),
  createExamWorkspaceGuestDraftStorage: () => ({
    async load() {
      return slot.stored;
    },
    async clearIf(cursor: string) {
      if (slot.stored?.draft.cursor !== cursor) {
        return false;
      }
      slot.stored = null;
      return true;
    },
  }),
}));

vi.mock("./ExamWorkspaceView.vue", async () => {
  const { defineComponent, h } = await import("vue");
  const { useExamWorkspaceDocument } = await import(
    "./exam-workspace/useExamWorkspaceDocument"
  );
  const { useExamWorkspaceAddress } = await import(
    "./exam-workspace/useExamWorkspaceAddress"
  );
  const { createSyncFence } = await import("./exam-workspace/examWorkspaceSyncFence");
  const { createRouteProjection } = await import(
    "./exam-workspace/examWorkspaceRouteProjection"
  );
  return {
    default: defineComponent({
      name: "ExamWorkspaceViewStub",
      props: { store: { type: Object, required: true } },
      setup(props) {
        if (!isWorkspaceStore(props.store)) {
          throw new Error("expected the host guest store");
        }
        const fence = createSyncFence();
        const projection = createRouteProjection();
        const document = useExamWorkspaceDocument({
          getFence: () => fence,
          noteInstallingCursor: () => undefined,
          store: props.store,
          submitRoute: (lineageId) => document.openDocument(lineageId, fence.begin()),
        });
        useExamWorkspaceAddress({
          currentAddress: () => document.summary.value?.lineage_id ?? null,
          projection,
          submitRoute: (lineageId) => {
            void document.openDocument(lineageId, fence.begin());
          },
        });
        return () => h("main", { "data-test": "minimal-view" });
      },
    }),
  };
});

vi.mock("../../composables/auth/sharedAuthRedirect", () => ({
  redirectToSharedAuthCeremony: vi.fn(),
}));

/** Narrow the stub store prop to the workspace store without a cast. */
function isWorkspaceStore(value: unknown): value is ExamWorkspaceStore {
  return typeof value === "object" && value !== null && "shared" in value;
}

/** A stored draft downgraded to the older format the browser cannot open. */
function seatUnreadableDraft(): StoredGuestDraft {
  const draft = newGuestDraft(pictureExam("Bildprov"), createIds(), []);
  const downgraded = JSON.parse(
    JSON.stringify({ draft, assets: { asset_001: new Blob(["a"]) } }).replaceAll(
      CURRENT_TOKEN,
      OLD_TOKEN,
    ),
  );
  slot.stored = downgraded;
  if (slot.stored === null) {
    throw new Error("expected the unreadable draft to be seated");
  }
  return slot.stored;
}

function seatReadableDraft(): StoredGuestDraft {
  const draft = newGuestDraft(exam("Bildprov"), createIds(), []);
  slot.stored = { assets: {}, draft };
  if (slot.stored === null) {
    throw new Error("expected the readable draft to be seated");
  }
  return slot.stored;
}

function toastMessages(): Array<string> {
  return useToastStore().toasts.map((toast) => toast.message);
}

describe("ExamWorkspaceGuestHost removal route order", () => {
  beforeEach(() => {
    slot.stored = null;
  });

  it("matching removal clears an existing guest document address before the editor mounts, with no toast", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const seated = seatUnreadableDraft();
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/guest", component: Host }],
    });
    await router.push({ path: "/guest", query: { document: seated.draft.lineage_id } });
    await router.isReady();
    const wrapper = mount(Host, { global: { plugins: [pinia, router] } });
    try {
      await flushPromises();
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(true);
      expect(toastMessages()).toEqual([]);
      await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
      await flushPromises();
      expect(slot.stored).toBeNull();
      expect(router.currentRoute.value.query.document).toBeUndefined();
      expect(wrapper.find('[data-test="minimal-view"]').exists()).toBe(true);
      expect(toastMessages()).toEqual([]);
    } finally {
      wrapper.unmount();
    }
  });

  it("refused removal with a newer readable draft opens that draft with no failure toast", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const seated = seatUnreadableDraft();
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/guest", component: Host }],
    });
    await router.push({ path: "/guest", query: { document: seated.draft.lineage_id } });
    await router.isReady();
    const wrapper = mount(Host, { global: { plugins: [pinia, router] } });
    try {
      await flushPromises();
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(true);
      expect(toastMessages()).toEqual([]);
      const newer = seatReadableDraft();
      newer.draft.cursor = "20000000-0000-4000-8000-000000000002";
      slot.stored = { assets: newer.assets, draft: newer.draft };
      await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
      await flushPromises();
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="minimal-view"]').exists()).toBe(true);
      expect(router.currentRoute.value.query.document).toBe(newer.draft.lineage_id);
      expect(slot.stored).not.toBeNull();
      expect(toastMessages()).toEqual([]);
    } finally {
      wrapper.unmount();
    }
  });

  it("refused removal with an empty slot shows the empty start with no toast", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const seated = seatUnreadableDraft();
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/guest", component: Host }],
    });
    await router.push({ path: "/guest", query: { document: seated.draft.lineage_id } });
    await router.isReady();
    const wrapper = mount(Host, { global: { plugins: [pinia, router] } });
    try {
      await flushPromises();
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(true);
      expect(toastMessages()).toEqual([]);
      slot.stored = null;
      await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
      await flushPromises();
      expect(slot.stored).toBeNull();
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="minimal-view"]').exists()).toBe(true);
      expect(router.currentRoute.value.query.document).toBeUndefined();
      expect(wrapper.find("[data-test='exam-workspace-guest-browser-notice']").text()).toBe(
        GUEST_BROWSER_ONLY_NOTICE,
      );
      expect(toastMessages()).toEqual([]);
    } finally {
      wrapper.unmount();
    }
  });
});
