/**
 * Exam workspace guest departure keeps the editing lock across the sign-in redirect.
 *
 * Expected behavior (TASK-SKRIPT-41-02-02 repair R10, finding F4 round 3):
 *   Following the sign-in prompt's login link departs through the history's
 *   `depart(leave)`: the pending edit is flushed, then the redirect runs as
 *   `leave` while the `replaceCopy` editing lock is still held, so an edit
 *   typed or pasted after the redirect starts is refused like any edit during
 *   an undo read. The visible copy and the stored draft stay at the departure
 *   snapshot, nothing is pending, and the lock stays held until the page comes
 *   back (`pageshow`) or the history's scope is disposed. A `leave` that
 *   returns false or throws resolves `depart` false, shows the inline failure
 *   copy, and releases the lock.
 *
 * Transport is the production guest store on in-memory draft storage; the
 * editing session, the history, the sign-in state, the prompt and the rich
 * editor are the production components. Only the redirect helper is mocked:
 * it records the call and never unloads the document.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { defineComponent, h, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";
import { Editor } from "@tiptap/core";

import * as publicApi from "../../../api/publicExamWorkspace";
import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { createExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { guestDocumentResponse, newGuestDraft } from "./examWorkspaceGuestDraft";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
import { useExamWorkspaceGuestSignIn } from "./useExamWorkspaceGuestSignIn";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import ExamWorkspaceSignInPrompt from "./ExamWorkspaceSignInPrompt.vue";
import { paste } from "./ExamWorkspaceRichTextEditor.specSupport";

const redirectMocks = vi.hoisted(() => ({
  redirectToSharedAuthCeremony: vi.fn(),
}));

vi.mock("../../../composables/auth/sharedAuthRedirect", () => ({
  redirectToSharedAuthCeremony: redirectMocks.redirectToSharedAuthCeremony,
}));

function guestIds() {
  let counter = 0;
  return {
    now: () => "2026-10-18T10:00:00.000Z",
    uuid: () => {
      counter += 1;
      return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
    },
  };
}

async function openWith(
  storage: Parameters<typeof createGuestExamWorkspaceStore>[0]["storage"],
  original: ReturnType<typeof newGuestDraft>,
) {
  const guest = createGuestExamWorkspaceStore({
    api: publicApi,
    ids: guestIds(),
    onLimit: () => undefined,
    storage,
  });
  let editing!: ReturnType<typeof useExamWorkspaceEditing>;
  let signIn!: ReturnType<typeof useExamWorkspaceGuestSignIn>;
  const host = defineComponent({
    setup() {
      editing = useExamWorkspaceEditing(guest.store, nullRouteProjection());
      signIn = useExamWorkspaceGuestSignIn({
        history: editing.history,
        store: guest.store,
        workspaceDocument: editing.workspaceDocument,
      });
      provideRichTextTargetRegistry();
      provideExamWorkspaceHistoryKeys({
        redo: () => void editing.history.redo(),
        undo: () => void editing.history.undo(),
        canUndo: editing.history.canUndo,
        canRedo: editing.history.canRedo,
      });
      return () => {
        const item = editing.workspaceDocument.value?.items[0];
        if (!item) {
          return h("div");
        }
        return h("div", [
          h(ExamWorkspaceRichTextEditor, {
            body: item.body,
            disabled: editing.isBusy.value,
            label: "Frågetext",
            testId: "departure-surface",
            onUpdate: (body: NativeExamBodyParagraph[], structural: boolean) => {
              editing.updateItemBody(item.item_id, body, structural);
            },
          }),
          h(ExamWorkspaceSignInPrompt, {
            depart: signIn.depart,
            message: "Logga in för att få AI-hjälp.",
          }),
        ]);
      };
    },
  });
  const wrapper = mount(host, { attachTo: document.body, global: { plugins: [createPinia()] } });
  expect(await editing.requestRoute(original.lineage_id)).toBe("installed");
  await flushPromises();
  return { editing, wrapper };
}

async function opened() {
  const backing = createInMemoryExamWorkspaceGuestDraftStorage();
  const original = newGuestDraft(buildParentDocument(), guestIds(), []);
  await backing.replaceIf(null, { assets: {}, draft: original });
  const { editing, wrapper } = await openWith(
    createExamWorkspaceGuestDraftStorage({ port: backing }),
    original,
  );
  return { backing, editing, wrapper };
}

function editorOf(surface: Element): Editor {
  if (
    !(surface instanceof HTMLElement) ||
    !("editor" in surface) ||
    !(surface.editor instanceof Editor)
  ) {
    throw new Error("expected the production ProseMirror editor");
  }
  return surface.editor;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

describe("guest departure across the sign-in redirect", () => {
  it("refuses an edit after redirect initiation while the navigation is slow", async () => {
    const probe = await opened();
    try {
      redirectMocks.redirectToSharedAuthCeremony.mockClear();
      probe.editing.setTitle("snapshot A");
      const before = JSON.stringify(probe.editing.workspaceDocument.value?.items[0]?.body);
      const link = probe.wrapper.findAll("a").find((candidate) => candidate.text() === "Logga in");
      if (!link) {
        throw new Error("missing sign-in action");
      }
      await link.trigger("click");
      await flushPromises();
      await flushPromises();
      expect(redirectMocks.redirectToSharedAuthCeremony).toHaveBeenCalledTimes(1);

      // The document has not unloaded yet; the teacher keeps typing and pasting.
      probe.editing.setTitle("newer visible B");
      const surface = probe.wrapper.get('[role="textbox"]').element;
      if (!(surface instanceof HTMLElement)) {
        throw new Error("missing editor");
      }
      const editor = editorOf(surface);
      editor.commands.selectAll();
      paste(surface, "<p>newer visible B while login loads</p>", "newer visible B while login loads");
      await nextTick();
      await flushPromises();

      expect(probe.editing.workspaceDocument.value?.title).toBe("snapshot A");
      expect(JSON.stringify(probe.editing.workspaceDocument.value?.items[0]?.body)).toBe(before);

      // Past the 900 ms autosave pause: nothing new may have been stored.
      await sleep(1000);
      await flushPromises();
      const stored = await probe.backing.load();
      if (!stored) {
        throw new Error("missing persisted draft");
      }
      expect(guestDocumentResponse(stored.draft).document.title).toBe("snapshot A");
      expect(JSON.stringify(guestDocumentResponse(stored.draft).document.items[0]?.body)).toBe(
        before,
      );
      expect(probe.editing.history.pending.value).toBe(false);
      expect(probe.editing.isBusy.value).toBe(true);
    } finally {
      probe.wrapper.unmount();
    }
  });

  it("releases the lock when the page comes back, so editing works again", async () => {
    const probe = await opened();
    try {
      redirectMocks.redirectToSharedAuthCeremony.mockClear();
      probe.editing.setTitle("snapshot A");
      const link = probe.wrapper.findAll("a").find((candidate) => candidate.text() === "Logga in");
      if (!link) {
        throw new Error("missing sign-in action");
      }
      await link.trigger("click");
      await flushPromises();
      await flushPromises();
      expect(redirectMocks.redirectToSharedAuthCeremony).toHaveBeenCalledTimes(1);
      expect(probe.editing.isBusy.value).toBe(true);

      window.dispatchEvent(new Event("pageshow"));
      await flushPromises();

      expect(probe.editing.isBusy.value).toBe(false);
      probe.editing.setTitle("after return");
      expect(probe.editing.workspaceDocument.value?.title).toBe("after return");
    } finally {
      probe.wrapper.unmount();
    }
  });

  it("shows the failure copy and releases the lock when leaving throws", async () => {
    const probe = await opened();
    try {
      redirectMocks.redirectToSharedAuthCeremony.mockClear();
      redirectMocks.redirectToSharedAuthCeremony.mockImplementationOnce(() => {
        throw new Error("ceremony unavailable");
      });
      probe.editing.setTitle("snapshot A");
      const link = probe.wrapper.findAll("a").find((candidate) => candidate.text() === "Logga in");
      if (!link) {
        throw new Error("missing sign-in action");
      }
      await link.trigger("click");
      await flushPromises();
      await flushPromises();

      expect(redirectMocks.redirectToSharedAuthCeremony).toHaveBeenCalledTimes(1);
      expect(
        probe.wrapper.find("[data-test='exam-workspace-sign-in-prompt-error']").exists(),
      ).toBe(true);
      expect(probe.editing.isBusy.value).toBe(false);
      probe.editing.setTitle("still here");
      expect(probe.editing.workspaceDocument.value?.title).toBe("still here");
    } finally {
      redirectMocks.redirectToSharedAuthCeremony.mockReset();
      probe.wrapper.unmount();
    }
  });

  it("does not redirect or hold the lock when the owner unmounts during the departure write", async () => {
    const backing = createInMemoryExamWorkspaceGuestDraftStorage();
    const original = newGuestDraft(buildParentDocument(), guestIds(), []);
    await backing.replaceIf(null, { assets: {}, draft: original });
    let releaseWrite!: () => void;
    let enteredResolve!: () => void;
    const writeGate = new Promise<void>((resolve) => {
      releaseWrite = resolve;
    });
    const writeEntered = new Promise<void>((resolve) => {
      enteredResolve = resolve;
    });
    const port = {
      clearIf: (cursor: string) => backing.clearIf(cursor),
      load: () => backing.load(),
      async replaceIf(
        cursor: string | null,
        next: NonNullable<Awaited<ReturnType<typeof backing.load>>>,
      ) {
        enteredResolve();
        await writeGate;
        return backing.replaceIf(cursor, next);
      },
    };
    const { editing, wrapper } = await openWith(
      createExamWorkspaceGuestDraftStorage({ port }),
      original,
    );
    const addSpy = vi.spyOn(window, "addEventListener");
    const removeSpy = vi.spyOn(window, "removeEventListener");
    try {
      redirectMocks.redirectToSharedAuthCeremony.mockClear();
      editing.setTitle("snapshot A");
      const link = wrapper.findAll("a").find((candidate) => candidate.text() === "Logga in");
      if (!link) {
        throw new Error("missing sign-in action");
      }
      await link.trigger("click");
      await writeEntered;
      // The workspace navigates away through another SPA route while the write is pending.
      wrapper.unmount();
      expect(redirectMocks.redirectToSharedAuthCeremony).not.toHaveBeenCalled();
      addSpy.mockClear();
      removeSpy.mockClear();
      releaseWrite();
      await flushPromises();
      await flushPromises();
      expect(redirectMocks.redirectToSharedAuthCeremony).not.toHaveBeenCalled();
      expect(addSpy.mock.calls.some(([name]) => name === "pageshow")).toBe(false);
      expect(editing.isBusy.value).toBe(false);
      // F2 fence: the unmount retired the generation, so the late write
      // installs nothing and the edit stays pending in memory.
      expect(editing.history.pending.value).toBe(true);
    } finally {
      releaseWrite();
      window.dispatchEvent(new Event("pageshow"));
      await flushPromises();
      addSpy.mockRestore();
      removeSpy.mockRestore();
      wrapper.unmount();
    }
  });
});
