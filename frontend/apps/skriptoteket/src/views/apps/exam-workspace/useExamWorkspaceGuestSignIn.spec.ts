/**
 * Exam workspace guest sign-in prompt state.
 *
 * Expected behavior:
 *   Guest mode is the store without the teacher half. A component that
 *   injects the sign-in key sets the one prompt slot, and dismissing clears
 *   it. Settling for departure with no open document resolves true without
 *   settling; with an open document it runs the history's departure settle
 *   and resolves its result.
 */

import { mount } from "@vue/test-utils";
import { defineComponent, h, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import { serverExamWorkspaceStore, type ExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceSignIn } from "./examWorkspaceSignIn";
import { useExamWorkspaceGuestSignIn } from "./useExamWorkspaceGuestSignIn";

function setupGuestStore(): ExamWorkspaceStore {
  const storage = createInMemoryExamWorkspaceGuestDraftStorage();
  const api = {
    addPublicExamWorkspaceChild: vi.fn(),
    changePublicExamWorkspaceItemType: vi.fn(),
    createEmptyPublicExamWorkspacePart: vi.fn(),
    createPublicExamWorkspaceBlank: vi.fn(),
    createPublicExamWorkspaceParent: vi.fn(),
    deletePublicExamWorkspaceChild: vi.fn(),
    deletePublicExamWorkspaceParent: vi.fn(),
    downloadPublicExamWorkspaceExport: vi.fn(),
    getPublicExamCourseCatalog: vi.fn(),
    getPublicExamWorkspaceExportChecklist: vi.fn(),
    groupPublicExamWorkspaceItems: vi.fn(),
    movePublicExamWorkspaceItem: vi.fn(),
    reorderPublicExamWorkspaceChildren: vi.fn(),
    requestPublicExamWorkspaceAnswerMisspellings: vi.fn(),
  };
  let counter = 0;
  const guest = createGuestExamWorkspaceStore({
    api,
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
  return guest.store;
}

type SignInApi = ReturnType<typeof useExamWorkspaceGuestSignIn>;

function mountSignIn(options: {
  store: ExamWorkspaceStore;
  document: NativeExamDocument | null;
  settleForDeparture: () => Promise<boolean>;
}): { api: SignInApi; requestThroughKey: (message: string) => void } {
  let api: SignInApi | null = null;
  let requestThroughKey: ((message: string) => void) | null = null;
  // eslint-disable-next-line vue/one-component-per-file
  const child = defineComponent({
    setup() {
      requestThroughKey = useExamWorkspaceSignIn();
      return () => h("div");
    },
  });
  // eslint-disable-next-line vue/one-component-per-file
  const probe = defineComponent({
    setup() {
      api = useExamWorkspaceGuestSignIn({
        history: { settleForDeparture: options.settleForDeparture },
        store: options.store,
        workspaceDocument: ref(options.document),
      });
      return () => h(child);
    },
  });
  const wrapper = mount(probe);
  if (!api || !requestThroughKey) {
    throw new Error("expected the sign-in probe to mount");
  }
  const mounted: { api: SignInApi; requestThroughKey: (message: string) => void } = {
    api,
    requestThroughKey,
  };
  wrapper.unmount();
  return mounted;
}

describe("useExamWorkspaceGuestSignIn", () => {
  it("reports guest mode only for the store without the teacher half", () => {
    const guest = mountSignIn({
      document: null,
      settleForDeparture: async () => true,
      store: setupGuestStore(),
    });
    expect(guest.api.isGuest.value).toBe(true);

    const teacher = mountSignIn({
      document: null,
      settleForDeparture: async () => true,
      store: serverExamWorkspaceStore,
    });
    expect(teacher.api.isGuest.value).toBe(false);
  });

  it("sets the prompt through the injected key and clears it on dismiss", () => {
    const { api, requestThroughKey } = mountSignIn({
      document: null,
      settleForDeparture: async () => true,
      store: setupGuestStore(),
    });

    expect(api.signInPrompt.value).toBeNull();
    requestThroughKey("Logga in för att använda AI.");
    expect(api.signInPrompt.value).toBe("Logga in för att använda AI.");
    api.dismissSignInPrompt();
    expect(api.signInPrompt.value).toBeNull();
  });

  it("settles departure without settling when no document is open", async () => {
    const settleForDeparture = vi.fn(async () => true);
    const { api } = mountSignIn({ document: null, settleForDeparture, store: setupGuestStore() });

    await expect(api.settleForDeparture()).resolves.toBe(true);
    expect(settleForDeparture).not.toHaveBeenCalled();
  });

  it("runs the history's departure settle with an open document and resolves its result", async () => {
    const settleForDeparture = vi.fn(async () => false);
    const { api } = mountSignIn({
      document: buildParentDocument(),
      settleForDeparture,
      store: setupGuestStore(),
    });

    await expect(api.settleForDeparture()).resolves.toBe(false);
    expect(settleForDeparture).toHaveBeenCalledTimes(1);
  });
});
