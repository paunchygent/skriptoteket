/**
 * Exam workspace guest sign-in departure under the editing lock.
 *
 * Expected behavior (TASK-SKRIPT-41-02-02 repair R9, finding F4):
 *   A sign-in exit departs through the history's `depart(leave)`, which holds
 *   the document owner's replacing lock while it stores, so no edit typed
 *   while the departure write runs is stored past it and
 *   lost. Typing during a paused departure write is refused like any edit
 *   during an undo read: the visible copy and the stored draft stay at the
 *   departure snapshot, nothing is pending, and departure resolves true. A
 *   departure that meets another replacing read resolves false and stores
 *   nothing new; a departure whose store fails resolves false.
 *
 * Transport is the production guest store on a pausable in-memory draft
 * storage; the editing session and the sign-in prompt state are the
 * production composables.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { defineComponent, h } from "vue";
import { describe, expect, it } from "vitest";

import * as publicApi from "../../../api/publicExamWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { guestDocumentResponse, newGuestDraft } from "./examWorkspaceGuestDraft";
import type {
  ExamWorkspaceGuestDraftStoragePort,
  StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { createExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import type { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import { createGuestExamWorkspaceStore as createStore } from "./examWorkspaceGuestStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { useExamWorkspaceGuestSignIn } from "./useExamWorkspaceGuestSignIn";

type Guest = ReturnType<typeof createGuestExamWorkspaceStore>;

function ids() {
  let counter = 0;
  return {
    now: () => "2026-10-18T10:00:00.000Z",
    uuid: () => {
      counter += 1;
      return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
    },
  };
}

function createGuest(port: ExamWorkspaceGuestDraftStoragePort): Guest {
  return createStore({ api: publicApi, ids: ids(), onLimit: () => undefined, storage: port });
}

function mountWorkspace(guest: Guest) {
  let editing!: ReturnType<typeof useExamWorkspaceEditing>;
  let signIn!: ReturnType<typeof useExamWorkspaceGuestSignIn>;
  const component = defineComponent({
    setup() {
      editing = useExamWorkspaceEditing(guest.store);
      signIn = useExamWorkspaceGuestSignIn({
        history: editing.history,
        store: guest.store,
        workspaceDocument: editing.workspaceDocument,
      });
      return () => h("div");
    },
  });
  const wrapper = mount(component, { global: { plugins: [createPinia()] } });
  if (!editing || !signIn) {
    throw new Error("expected the departure probe to mount");
  }
  return { editing, signIn, wrapper };
}

describe("guest sign-in departure under the editing lock", () => {
  it("refuses typing during a paused departure write and stores the departure snapshot", async () => {
    const backing = createInMemoryExamWorkspaceGuestDraftStorage();
    const original = newGuestDraft(buildParentDocument(), ids(), []);
    expect(await backing.replaceIf(null, { assets: {}, draft: original })).toBe(true);
    let releaseWrite!: () => void;
    let enteredResolve!: () => void;
    const writeGate = new Promise<void>((resolve) => {
      releaseWrite = resolve;
    });
    const writeEntered = new Promise<void>((resolve) => {
      enteredResolve = resolve;
    });
    const port: ExamWorkspaceGuestDraftStoragePort = {
      clearIf: (cursor) => backing.clearIf(cursor),
      load: () => backing.load(),
      async replaceIf(expectedCursor, next) {
        enteredResolve();
        await writeGate;
        return backing.replaceIf(expectedCursor, next);
      },
    };
    const guest = createGuest(createExamWorkspaceGuestDraftStorage({ port }));
    const { editing, signIn, wrapper } = mountWorkspace(guest);
    try {
      const token = await editing.noteRouteRequest();
      if (token === null) {
        throw new Error("expected the route request to settle");
      }
      expect(await editing.openDocument(original.lineage_id, token)).toBe("installed");
      await flushPromises();
      editing.setTitle("snapshot A");

      const departure = signIn.depart(async () => true);
      await writeEntered;
      editing.setTitle("newer visible B");
      expect(editing.workspaceDocument.value?.title).toBe("snapshot A");
      releaseWrite();
      await expect(departure).resolves.toBe(true);

      const stored: StoredGuestDraft | null = await backing.load();
      if (stored === null) {
        throw new Error("expected the departure write to store a draft");
      }
      expect(guestDocumentResponse(stored.draft).document.title).toBe("snapshot A");
      expect(editing.history.pending.value).toBe(false);
    } finally {
      releaseWrite();
      wrapper.unmount();
    }
  });

  it("resolves false and stores nothing new while an undo holds the copy", async () => {
    const backing = createInMemoryExamWorkspaceGuestDraftStorage();
    const original = newGuestDraft(buildParentDocument(), ids(), []);
    expect(await backing.replaceIf(null, { assets: {}, draft: original })).toBe(true);
    const guest = createGuest(createExamWorkspaceGuestDraftStorage({ port: backing }));
    const { editing, signIn, wrapper } = mountWorkspace(guest);
    try {
      const token = await editing.noteRouteRequest();
      if (token === null) {
        throw new Error("expected the route request to settle");
      }
      expect(await editing.openDocument(original.lineage_id, token)).toBe("installed");
      await flushPromises();
      editing.setTitle("one");
      await editing.history.flush();
      const before: StoredGuestDraft | null = await backing.load();
      if (before === null) {
        throw new Error("expected the flushed edit to store a draft");
      }

      let releaseMove!: () => void;
      let enteredMoveResolve!: () => void;
      const moveGate = new Promise<void>((resolve) => {
        releaseMove = resolve;
      });
      const moveEntered = new Promise<void>((resolve) => {
        enteredMoveResolve = resolve;
      });
      const moveStep = guest.store.shared.moveExamWorkspaceHistoryPosition.bind(
        guest.store.shared,
      );
      guest.store.shared.moveExamWorkspaceHistoryPosition = async (lineageId, params) => {
        enteredMoveResolve();
        await moveGate;
        return moveStep(lineageId, params);
      };
      try {
        const moving = editing.history.undo();
        await moveEntered;
        await expect(signIn.depart(async () => true)).resolves.toBe(false);
        const during: StoredGuestDraft | null = await backing.load();
        expect(during?.draft.steps).toHaveLength(before.draft.steps.length);
        releaseMove();
        await moving;
      } finally {
        releaseMove();
      }
    } finally {
      wrapper.unmount();
    }
  });

  it("resolves false when the departure store rejects", async () => {
    const backing = createInMemoryExamWorkspaceGuestDraftStorage();
    const original = newGuestDraft(buildParentDocument(), ids(), []);
    expect(await backing.replaceIf(null, { assets: {}, draft: original })).toBe(true);
    const port: ExamWorkspaceGuestDraftStoragePort = {
      clearIf: (cursor) => backing.clearIf(cursor),
      load: () => backing.load(),
      async replaceIf() {
        throw new Error("The browser storage is unavailable.");
      },
    };
    const guest = createGuest(port);
    const { editing, signIn, wrapper } = mountWorkspace(guest);
    try {
      const token = await editing.noteRouteRequest();
      if (token === null) {
        throw new Error("expected the route request to settle");
      }
      expect(await editing.openDocument(original.lineage_id, token)).toBe("installed");
      await flushPromises();
      editing.setTitle("unsaved A");

      await expect(signIn.depart(async () => true)).resolves.toBe(false);
    } finally {
      wrapper.unmount();
    }
  });

  it("resolves false when the departure store reports a lost write", async () => {
    const backing = createInMemoryExamWorkspaceGuestDraftStorage();
    const original = newGuestDraft(buildParentDocument(), ids(), []);
    expect(await backing.replaceIf(null, { assets: {}, draft: original })).toBe(true);
    const port: ExamWorkspaceGuestDraftStoragePort = {
      clearIf: (cursor) => backing.clearIf(cursor),
      load: () => backing.load(),
      async replaceIf() {
        return false;
      },
    };
    const guest = createGuest(port);
    const { editing, signIn, wrapper } = mountWorkspace(guest);
    try {
      const token = await editing.noteRouteRequest();
      if (token === null) {
        throw new Error("expected the route request to settle");
      }
      expect(await editing.openDocument(original.lineage_id, token)).toBe("installed");
      await flushPromises();
      editing.setTitle("unsaved A");

      await expect(signIn.depart(async () => true)).resolves.toBe(false);
      const stored: StoredGuestDraft | null = await backing.load();
      expect(stored?.draft.cursor).toBe(original.cursor);
    } finally {
      wrapper.unmount();
    }
  });
});
