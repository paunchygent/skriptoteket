/**
 * Exam workspace replacing reads.
 *
 * Domain purpose:
 *   Coordinate the reads that replace the open copy (undo, redo and the
 *   server commands): lock editing while the read runs, hold the AI
 *   suggestion arrivals and gap keying replies that land meanwhile, and run
 *   them again on the installed document so a delivered result is never
 *   overwritten.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceDocument`, which passes its open copy, its
 *     selection, its replacing flag, and its arrivals and keying bindings.
 *   - Replays run through `arrivals` and `keying`: replies whose question or
 *     gap the new document no longer holds do not apply, as everywhere else.
 *   - A conflict reload inside a replacing read replays only arrivals; the
 *     replacing read's own completion replays both arrivals and keying.
 */

import type { Ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import type { useExamWorkspaceGapKeying } from "./useExamWorkspaceGapKeying";
import type { useExamWorkspaceSaveArrivals } from "./useExamWorkspaceSaveArrivals";

export type ExamWorkspaceDocumentReplacingBinding = {
  workspaceDocument: Ref<NativeExamDocument | null>;
  selectedItemId: Ref<string | null>;
  /** Editing lock the document owner reads; set while a replacing read runs. */
  replacing: Ref<boolean>;
  arrivals: ReturnType<typeof useExamWorkspaceSaveArrivals>;
  keying: ReturnType<typeof useExamWorkspaceGapKeying>;
};

export function useExamWorkspaceDocumentReplacing(binding: ExamWorkspaceDocumentReplacingBinding) {
  const { workspaceDocument, selectedItemId, replacing, arrivals, keying } = binding;
  /** The arrival marks a replacing read was started at; null while none runs. */
  let held: { arrivals: number; keying: number } | null = null;

  function keepSelection(document: NativeExamDocument): void {
    if (!document.items.some((item) => item.item_id === selectedItemId.value)) {
      selectedItemId.value = document.items[0]?.item_id ?? null;
    }
  }

  /**
   * Run an undo, redo or server command that replaces the copy. Editing is
   * locked meanwhile, and AI suggestions and spelling replies that arrive
   * during its read run again on the document it installs, so a delivered
   * result is never overwritten. Replies whose question or gap the document
   * no longer holds do not apply, as everywhere else.
   */
  async function replaceCopy<T>(run: () => Promise<T>): Promise<T> {
    replacing.value = true;
    const marks = { arrivals: arrivals.payloadMark(), keying: keying.payloadMark() };
    const openedArrivals = arrivals.beginHold();
    const openedKeying = keying.beginHold();
    held = marks;
    try {
      return await run();
    } finally {
      held = null;
      arrivals.endHold(openedArrivals);
      keying.endHold(openedKeying);
      replacing.value = false;
    }
  }

  function replayHeld(): void {
    if (held) {
      arrivals.replayAfterResponse(held.arrivals);
      keying.replayAfterResponse(held.keying);
    }
  }

  /** A conflict reload inside a replacing read: its suggestions run again on the reloaded exam. */
  function replayArrivalsAfterReload(): void {
    if (held) {
      arrivals.replayAfterResponse(held.arrivals);
    }
  }

  /** Put an undo step's document in front of the teacher; not an edit. */
  function installDocument(document: NativeExamDocument): void {
    workspaceDocument.value = document;
    keepSelection(document);
    replayHeld();
  }

  return {
    installDocument,
    replaceCopy,
    replayArrivalsAfterReload,
    replayHeld,
  };
}
