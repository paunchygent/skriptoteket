/**
 * Signed-out guest host: a draft the app cannot read shows the
 * download-or-remove notice (U14, repairs F1).
 *
 * Expected behavior:
 *   A stored draft whose documents are not all current renders the shared
 *   file notice with the older-format sentence and glyph-only download and
 *   remove actions instead of the editor. Download saves one zip with
 *   draft.json and every stored picture unchanged and keeps the record;
 *   remove deletes the record and its pictures, clears the document address
 *   and shows the normal empty guest start. A current draft still opens in
 *   the editor with no notice.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { unzipSync } from "fflate";

import { useToastStore } from "../../stores/toast";
import { triggerBrowserDownload } from "../../utils/browserDownload";
import ExamWorkspaceGuestHost from "./ExamWorkspaceGuestHost.vue";
import type { StoredGuestDraft } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import {
  EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY,
} from "./exam-workspace/examWorkspaceFileNoticeCopy";
import { newGuestDraft, type ExamWorkspaceGuestDraft } from "./exam-workspace/examWorkspaceGuestDraft";
import { GUEST_BROWSER_ONLY_NOTICE } from "./exam-workspace/examWorkspaceGuestCopy";
import { pictureExam } from "./exam-workspace/examWorkspaceGuestStore.specSupport";

const CURRENT_TOKEN = '"native_exam_document_v11"';
const OLD_TOKEN = '"native_exam_document_v10"';

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

vi.mock("./exam-workspace/examWorkspaceGuestDraftStorage", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./exam-workspace/examWorkspaceGuestDraftStorage")>()) as object,
  createExamWorkspaceGuestDraftStorage: () => ({
    async load() {
      return storageMocks.stored;
    },
    async replaceIf(expectedCursor: string | null, next: StoredGuestDraft) {
      if ((storageMocks.stored?.draft.cursor ?? null) !== expectedCursor) {
        return false;
      }
      storageMocks.stored = next;
      return true;
    },
    async clearIf(expectedCursor: string) {
      if (storageMocks.stored?.draft.cursor !== expectedCursor) {
        return false;
      }
      storageMocks.stored = null;
      return true;
    },
  }),
}));

vi.mock("../../utils/browserDownload", () => ({
  triggerBrowserDownload: vi.fn(),
}));

vi.mock("./ExamWorkspaceView.vue", () => ({
  default: {
    name: "ExamWorkspaceViewStub",
    props: { store: { type: Object, required: true } },
    template: "<div data-test='exam-workspace-view-stub' />",
  },
}));

const redirectMocks = vi.hoisted(() => ({
  redirectToSharedAuthCeremony: vi.fn(),
}));

vi.mock("../../composables/auth/sharedAuthRedirect", () => ({
  redirectToSharedAuthCeremony: redirectMocks.redirectToSharedAuthCeremony,
}));

const GUEST_IDS = {
  now: () => "2026-10-18T10:00:00.000Z",
  uuid: () => "10000000-0000-4000-8000-000000000001",
};

/** A stored draft with picture bytes, downgraded to the older format. */
function seatUnreadableDraft(): StoredGuestDraft {
  const draft = newGuestDraft(pictureExam("Bildprov"), GUEST_IDS, []);
  const downgraded: ExamWorkspaceGuestDraft = JSON.parse(
    JSON.stringify(draft).replaceAll(CURRENT_TOKEN, OLD_TOKEN),
  );
  storageMocks.stored = { assets: { asset_001: new Blob(["a"]) }, draft: downgraded };
  return storageMocks.stored;
}

function seatCurrentDraft(): StoredGuestDraft {
  const draft = newGuestDraft(pictureExam("Bildprov"), GUEST_IDS, []);
  storageMocks.stored = { assets: { asset_001: new Blob(["a"]) }, draft };
  return storageMocks.stored;
}

async function blobBytes(blob: Blob): Promise<Uint8Array> {
  return await new Promise<Uint8Array>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (reader.result instanceof ArrayBuffer) {
        resolve(new Uint8Array(reader.result));
        return;
      }
      reject(new Error("The FileReader did not return bytes."));
    };
    reader.onerror = () => reject(reader.error ?? new Error("Could not read the blob bytes."));
    reader.readAsArrayBuffer(blob);
  });
}

async function equipStoredPictureBytes(): Promise<void> {
  const stored = storageMocks.stored;
  if (stored === null) {
    throw new Error("expected a stored draft to equip");
  }
  for (const blob of Object.values(stored.assets)) {
    Object.defineProperty(blob, "arrayBuffer", {
      configurable: true,
      value: async (): Promise<ArrayBuffer> => {
        const bytes = await blobBytes(blob);
        const copy = new Uint8Array(bytes.length);
        copy.set(bytes);
        return copy.buffer;
      },
    });
  }
}

describe("ExamWorkspaceGuestHost unreadable drafts", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    storageMocks.stored = null;
    routeMocks.query = {};
    routeMocks.replace.mockReset();
    vi.mocked(triggerBrowserDownload).mockClear();
  });

  it("shows the older-format notice with glyph download and remove instead of the editor", async () => {
    const seated = seatUnreadableDraft();
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY,
    );
    const buttons = wrapper.findAll("button");
    expect(buttons.map((button) => button.attributes("data-test"))).toEqual([
      "exam-workspace-file-notice-download",
      "exam-workspace-file-notice-remove",
    ]);
    for (const button of buttons) {
      expect(button.text().trim()).toBe("");
    }
    const download = wrapper.get('[data-test="exam-workspace-file-notice-download"]');
    expect(download.attributes("title")).toBe(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME);
    expect(download.attributes("aria-label")).toBe(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME);
    const remove = wrapper.get('[data-test="exam-workspace-file-notice-remove"]');
    expect(remove.attributes("title")).toBe(EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME);
    expect(remove.attributes("aria-label")).toBe(EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME);
    expect(wrapper.find("[data-test='exam-workspace-view-stub']").exists()).toBe(false);
    expect(routeMocks.replace).not.toHaveBeenCalled();
    expect(seated.draft.lineage_id).toBeDefined();
    expect(storageMocks.stored).not.toBeNull();
    expect(vi.mocked(triggerBrowserDownload)).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("download saves one zip with draft.json and every stored picture unchanged", async () => {
    seatUnreadableDraft();
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();
    await equipStoredPictureBytes();

    await wrapper.get('[data-test="exam-workspace-file-notice-download"]').trigger("click");
    // The click handler awaits FileReader macrotasks; wait for the download.
    await vi.waitFor(() => {
      expect(vi.mocked(triggerBrowserDownload)).toHaveBeenCalledTimes(1);
    });

    const [blob, filename] = vi.mocked(triggerBrowserDownload).mock.calls[0];
    expect(filename).toBe("Bildprov.zip");
    expect(blob.type).toBe("application/zip");
    const unzipped = unzipSync(await blobBytes(blob));
    expect(Object.keys(unzipped).sort()).toEqual(["assets/asset_001", "draft.json"]);
    const draftJson = unzipped["draft.json"];
    const picture = unzipped["assets/asset_001"];
    if (draftJson === undefined || picture === undefined) {
      throw new Error("expected draft.json and the picture entry in the zip");
    }
    expect(JSON.parse(new TextDecoder().decode(draftJson))).toEqual(
      storageMocks.stored?.draft,
    );
    expect(new TextDecoder().decode(picture)).toBe("a");
    expect(storageMocks.stored).not.toBeNull();
    expect(useToastStore().toasts).toEqual([]);

    wrapper.unmount();
  });

  it("remove deletes the record and its pictures and shows the empty guest start", async () => {
    const seated = seatUnreadableDraft();
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
    await flushPromises();

    expect(storageMocks.stored).toBeNull();
    expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(false);
    expect(wrapper.find("[data-test='exam-workspace-view-stub']").exists()).toBe(true);
    expect(routeMocks.replace).toHaveBeenLastCalledWith({ query: { document: undefined } });
    expect(seated.draft.lineage_id).toBeDefined();

    wrapper.unmount();
  });

  it("still opens a current draft in the editor with no notice", async () => {
    seatCurrentDraft();
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(false);
    expect(wrapper.find("[data-test='exam-workspace-view-stub']").exists()).toBe(true);

    wrapper.unmount();
  });

  it("shows the notice for a draft with one older document among current ones", async () => {
    const draft = newGuestDraft(pictureExam("Bildprov"), GUEST_IDS, []);
    const mixed: ExamWorkspaceGuestDraft = JSON.parse(
      JSON.stringify(draft).replace(CURRENT_TOKEN, OLD_TOKEN),
    );
    expect(mixed.baseline.document.schema_version).not.toBe(
      mixed.saved_document.schema_version,
    );
    storageMocks.stored = { assets: {}, draft: mixed };
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY,
    );
    expect(wrapper.find("[data-test='exam-workspace-view-stub']").exists()).toBe(false);

    wrapper.unmount();
  });

  it("hides the browser-only banner while the unreadable notice is shown", async () => {
    seatUnreadableDraft();
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(true);
    expect(
      wrapper.find("[data-test='exam-workspace-guest-browser-notice']").exists(),
    ).toBe(false);

    wrapper.unmount();
  });

  it("shows the browser-only banner again after remove with the empty guest start", async () => {
    seatUnreadableDraft();
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-file-notice"]').exists()).toBe(false);
    expect(wrapper.find("[data-test='exam-workspace-guest-browser-notice']").text()).toBe(
      GUEST_BROWSER_ONLY_NOTICE,
    );
    expect(wrapper.find("[data-test='exam-workspace-view-stub']").exists()).toBe(true);

    wrapper.unmount();
  });

  it("still shows the browser-only banner with a readable draft", async () => {
    seatCurrentDraft();
    const wrapper = mount(ExamWorkspaceGuestHost, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    expect(wrapper.find("[data-test='exam-workspace-guest-browser-notice']").text()).toBe(
      GUEST_BROWSER_ONLY_NOTICE,
    );
    expect(wrapper.find("[data-test='exam-workspace-view-stub']").exists()).toBe(true);

    wrapper.unmount();
  });
});
