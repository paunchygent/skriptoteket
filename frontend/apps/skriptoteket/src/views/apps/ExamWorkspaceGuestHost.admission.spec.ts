/**
 * Signed-out guest host admission: the host decides readability before it
 * mounts the editor, and removes only the draft the teacher saw (U18,
 * repairs R2 and R3).
 *
 * Expected behavior:
 *   Startup with a stored draft the app cannot read shows the shared
 *   recovery notice without ever mounting the editor, without ever writing
 *   the stored lineage into the route, and without the ordinary
 *   outdated-open failure toast. Startup with a readable stored draft
 *   publishes the lineage to the route and mounts the editor, as before.
 *   Remove with a stale cursor keeps a newer unreadable draft stored with
 *   its assets and keeps its notice; a newer readable draft opens in the
 *   editor; a matching cursor shows the empty guest start with the banner.
 *
 *   The view child below is the production address/document wiring, not a
 *   stub that does nothing: it runs the real useExamWorkspaceDocument and
 *   the real useExamWorkspaceAddress against the host's guest store, so a
 *   published unreadable lineage would still run the ordinary open-error
 *   path the repair must avoid.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

import Host from "./ExamWorkspaceGuestHost.vue";
import { useToastStore } from "../../stores/toast";
import { newGuestDraft } from "./exam-workspace/examWorkspaceGuestDraft";
import type { StoredGuestDraft } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import type { ExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY } from "./exam-workspace/examWorkspaceFileNoticeCopy";
import { GUEST_BROWSER_ONLY_NOTICE } from "./exam-workspace/examWorkspaceGuestCopy";
import {
  createIds,
  exam,
  pictureExam,
} from "./exam-workspace/examWorkspaceGuestStore.specSupport";

const CURRENT_TOKEN = "native_exam_document_v10";
const OLD_TOKEN = "native_exam_document_v9";

const slot = vi.hoisted((): { stored: StoredGuestDraft | null } => ({ stored: null }));
const routeBinding = vi.hoisted((): {
  value: { query: Record<string, string | undefined> } | null;
} => ({ value: null }));
const replacements = vi.hoisted((): Array<Record<string, string | undefined>> => []);

vi.mock("vue-router", () => ({
  useRoute: () => routeBinding.value,
  useRouter: () => ({
    replace: async (next: { query: Record<string, string | undefined> }) => {
      if (!routeBinding.value) {
        throw new Error("route missing");
      }
      replacements.push(next.query);
      routeBinding.value.query = next.query;
    },
  }),
}));

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
  return {
    default: defineComponent({
      name: "ExamWorkspaceViewStub",
      props: { store: { type: Object, required: true } },
      setup(props) {
        if (!isWorkspaceStore(props.store)) {
          throw new Error("expected the host guest store");
        }
        const document = useExamWorkspaceDocument({ store: props.store });
        useExamWorkspaceAddress({
          isDirty: document.isDirty,
          openDocument: document.openDocument,
          summary: document.summary,
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

function mountHost() {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(Host, { global: { plugins: [pinia] } });
}

describe("ExamWorkspaceGuestHost admission", () => {
  beforeEach(() => {
    slot.stored = null;
    routeBinding.value = reactive({ query: {} });
    replacements.length = 0;
  });

  it("startup with an unreadable stored draft never mounts the editor, never writes the route, and shows the notice with no outdated-open toast", async () => {
    const seated = seatUnreadableDraft();
    const wrapper = mountHost();
    try {
      expect(wrapper.find('[data-test="minimal-view"]').exists()).toBe(false);
      await flushPromises();
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(true);
      expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
        EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY,
      );
      expect(wrapper.find('[data-test="minimal-view"]').exists()).toBe(false);
      expect(useToastStore().toasts.map((toast) => toast.message)).toEqual([]);
      expect(
        replacements.some((query) => query.document === seated.draft.lineage_id),
      ).toBe(false);
      expect(routeBinding.value?.query.document).not.toBe(seated.draft.lineage_id);
    } finally {
      wrapper.unmount();
    }
  });

  it("startup with a readable stored draft mounts the editor and carries the lineage in the route", async () => {
    const seated = seatReadableDraft();
    const wrapper = mountHost();
    try {
      await flushPromises();
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="minimal-view"]').exists()).toBe(true);
      expect(routeBinding.value?.query.document).toBe(seated.draft.lineage_id);
    } finally {
      wrapper.unmount();
    }
  });

  it("remove with a stale cursor keeps a newer unreadable draft stored with its assets and its notice", async () => {
    seatUnreadableDraft();
    const wrapper = mountHost();
    try {
      await flushPromises();
      if (slot.stored === null) {
        throw new Error("expected the seated draft to be stored");
      }
      const fresh = newGuestDraft(pictureExam("Nyare"), createIds(), []);
      fresh.cursor = "20000000-0000-4000-8000-000000000002";
      const seatedNewer = JSON.parse(
        JSON.stringify({
          draft: fresh,
          assets: { asset_001: new Blob(["b"]) },
        }).replaceAll(CURRENT_TOKEN, OLD_TOKEN),
      );
      slot.stored = seatedNewer;
      const newer = slot.stored;
      if (newer === null) {
        throw new Error("expected the newer draft to be seated");
      }
      await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
      await flushPromises();
      expect(slot.stored).toBe(newer);
      expect(slot.stored?.assets["asset_001"]).toBe(newer.assets["asset_001"]);
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(true);
      expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
        EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY,
      );
      expect(wrapper.find('[data-test="minimal-view"]').exists()).toBe(false);
    } finally {
      wrapper.unmount();
    }
  });

  it("remove with a stale cursor and a newer readable draft opens that draft", async () => {
    seatUnreadableDraft();
    const wrapper = mountHost();
    try {
      await flushPromises();
      const newer = seatReadableDraft();
      newer.draft.cursor = "20000000-0000-4000-8000-000000000002";
      slot.stored = { assets: newer.assets, draft: newer.draft };
      await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
      await flushPromises();
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="minimal-view"]').exists()).toBe(true);
      expect(routeBinding.value?.query.document).toBe(newer.draft.lineage_id);
      expect(slot.stored).not.toBeNull();
    } finally {
      wrapper.unmount();
    }
  });

  it("remove with a matching cursor shows the empty guest start with the banner back", async () => {
    seatUnreadableDraft();
    const wrapper = mountHost();
    try {
      await flushPromises();
      await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
      await flushPromises();
      expect(slot.stored).toBeNull();
      expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="minimal-view"]').exists()).toBe(true);
      expect(wrapper.find("[data-test='exam-workspace-guest-browser-notice']").text()).toBe(
        GUEST_BROWSER_ONLY_NOTICE,
      );
    } finally {
      wrapper.unmount();
    }
  });
});
