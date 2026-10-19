/**
 * Exam workspace gap-answer keying.
 *
 * Domain purpose:
 *   Key a teacher's accepted gap answers synchronously, then fill the gap's
 *   automatic misspellings from the deterministic producer (TASK-SKRIPT-39-09-06
 *   T3). An edit requests newly added values and any still-pending values it keeps, plus every accepted
 *   answer the question now holds, and the document's text.
 *
 *   The reply merges into the gap as it stands at that moment: existing
 *   automatic values stay, and a duplicate, a gold answer and a spelling the
 *   teacher suppressed are all dropped. A reply that lost its place changes
 *   nothing and stays silent: another exam is open, the copy was reloaded,
 *   reopened or its question reconverted, the question or gap is gone, a
 *   keyed value was removed, or a newer keying edit of the same gap
 *   superseded it.
 *
 *   A reply merged while a save is in flight is re-applied when that save's
 *   response or conflict reload installs a document the payload was read
 *   without; likewise for an undo, redo or server command, whose document
 *   must still hold the gap's keyed values for the reply to apply. A reply the payload already held is never replayed, so a
 *   teacher-removed spelling never returns from an earlier reply. A failed
 *   request that still stands reports Swedish copy.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceDocument`, which owns the copy and its one
 *     item patch path.
 *   - Applies `withGapValues`, `withAutomaticValues` and
 *     `withoutAutomaticValue` from `examWorkspaceItemEdits`.
 *   - Reads the document's text through `examWorkspaceDocumentText`.
 *   - Delegates transport to the shared store half.
 */

import type { Ref, ShallowRef } from "vue";

import type {
  ExamWorkspaceMisspellingsRequest,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { examWorkspaceDocumentText } from "./examWorkspaceDocumentText";
import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import {
  itemAcceptedAnswers,
  withAutomaticValues,
  withGapValues,
  withoutAutomaticValue,
} from "./examWorkspaceGapEdits";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";

const AUTOMATIC_VALUES_FAILURE_COPY =
  "Det gick inte att skapa automatiska stavningar. Svaren finns kvar.";

export type ExamWorkspaceGapKeyingBinding = {
  /** The draft copy; keyed values and merged spellings are written into it. */
  workspaceDocument: Ref<NativeExamDocument | null>;
  /** The opening the request is sent for; a newer opening drops its reply. */
  openExam: Readonly<ShallowRef<ExamWorkspaceOpening | null>>;
  /** The document owner's one item patch path; false when it refused the edit. */
  patchItem: (itemId: string, patch: (item: NativeExamItem) => NativeExamItem) => boolean;
  /** The shared store half the misspelling request runs through. */
  shared: ExamWorkspaceSharedStore;
};

/** One keying request, identified so a reply that lost its place can be refused. */
type KeyedRequest = {
  acceptedValues: string[];
  copyGeneration: number;
  epoch: number;
  gapId: string;
  itemGeneration: number;
  itemId: string;
  opening: ExamWorkspaceOpening;
};

/** One merged keying reply, numbered in arrival order for the save lifecycle. */
type KeyedReply = KeyedRequest & {
  automaticValues: string[];
  sequence: number;
};

export function useExamWorkspaceGapKeying(binding: ExamWorkspaceGapKeyingBinding) {
  const toast = useToast();
  const epochs = new Map<string, number>();
  const pendingValues = new Map<string, string[]>();
  const itemGenerations = new Map<string, number>();
  let copyGeneration = 0;
  let delivered = 0;
  // Replies merged since the teacher's save began; null while no save runs.
  let duringSave: KeyedReply[] | null = null;

  function gapKey(itemId: string, gapId: string): string {
    return `${itemId}\u0000${gapId}`;
  }

  /** Whether the request still stands for the copy in front of the teacher. */
  function requestIsLive(request: KeyedRequest): boolean {
    const current = binding.workspaceDocument.value;
    if (current === null || binding.openExam.value !== request.opening) {
      return false;
    }
    if (
      request.copyGeneration !== copyGeneration ||
      request.itemGeneration !== (itemGenerations.get(request.itemId) ?? 0)
    ) {
      return false;
    }
    if (epochs.get(gapKey(request.itemId, request.gapId)) !== request.epoch) {
      return false;
    }
    const item = current.items.find((candidate) => candidate.item_id === request.itemId);
    const gap = item?.gaps.find((candidate) => candidate.gap_id === request.gapId);
    return (
      gap !== undefined &&
      request.acceptedValues.every((value) => gap.accepted_values.includes(value))
    );
  }

  /** Write one live reply's spellings into the current gap. */
  function writeReply(reply: KeyedReply): void {
    const current = binding.workspaceDocument.value;
    if (current === null || !requestIsLive(reply)) {
      return;
    }
    let changed = false;
    const items = current.items.map((item) => {
      if (item.item_id !== reply.itemId) {
        return item;
      }
      const next = withAutomaticValues(item, reply.gapId, reply.automaticValues);
      changed = changed || next !== item;
      return next;
    });
    if (changed) {
      binding.workspaceDocument.value = { ...current, items };
    }
  }

  /** Merge one arriving reply, and hold it for a save that read its payload earlier. */
  function mergeReply(request: KeyedRequest, automaticValues: string[]): void {
    if (!requestIsLive(request)) {
      return;
    }
    delivered += 1;
    const reply: KeyedReply = { ...request, automaticValues, sequence: delivered };
    writeReply(reply);
    duringSave?.push(reply);
  }

  async function requestAutomaticValues(
    request: KeyedRequest,
    body: ExamWorkspaceMisspellingsRequest,
  ): Promise<void> {
    try {
      const response = await binding.shared.requestExamWorkspaceAnswerMisspellings(body);
      mergeReply(request, response.automatic_values);
    } catch {
      if (requestIsLive(request)) {
        toast.failure(AUTOMATIC_VALUES_FAILURE_COPY);
      }
    } finally {
      if (
        epochs.get(gapKey(request.itemId, request.gapId)) === request.epoch &&
        request.copyGeneration === copyGeneration &&
        request.itemGeneration === (itemGenerations.get(request.itemId) ?? 0)
      ) {
        pendingValues.delete(gapKey(request.itemId, request.gapId));
      }
    }
  }

  /**
   * Key the gap's accepted values at once, and let the producer fill in the
   * spellings of new values and retained values whose first request is pending.
   */
  function updateItemGapValues(itemId: string, gapId: string, acceptedValues: string[]): void {
    const current = binding.workspaceDocument.value;
    const opening = binding.openExam.value;
    const item = current?.items.find((candidate) => candidate.item_id === itemId) ?? null;
    const gap = item?.gaps.find((candidate) => candidate.gap_id === gapId) ?? null;
    if (current === null || opening === null || item === null || gap === null) {
      binding.patchItem(itemId, (target) => withGapValues(target, gapId, acceptedValues));
      return;
    }
    const added = acceptedValues.filter((value) => !gap.accepted_values.includes(value));
    const keyed = withGapValues(item, gapId, acceptedValues);
    if (!binding.patchItem(itemId, () => keyed) || keyed === item) {
      return;
    }
    const key = gapKey(itemId, gapId);
    // Supersede the old reply, but do not lose values whose first generation is pending.
    const requested = [...new Set([
      ...(pendingValues.get(key) ?? []).filter((value) => acceptedValues.includes(value)),
      ...added,
    ])];
    const epoch = (epochs.get(key) ?? 0) + 1;
    epochs.set(key, epoch);
    if (requested.length === 0) {
      pendingValues.delete(key);
      return;
    }
    pendingValues.set(key, requested);
    void requestAutomaticValues(
      {
        acceptedValues: requested,
        copyGeneration,
        epoch,
        gapId,
        itemGeneration: itemGenerations.get(itemId) ?? 0,
        itemId,
        opening,
      },
      {
        accepted_values: requested,
        other_gold_answers: itemAcceptedAnswers(keyed),
        document_text: examWorkspaceDocumentText(current),
      },
    );
  }

  /** Remove one automatic value and suppress it for good. */
  function removeItemAutomaticValue(itemId: string, gapId: string, value: string): void {
    binding.patchItem(itemId, (item) => withoutAutomaticValue(item, gapId, value));
  }

  /** Start listing replies for a save or a replacing read; false when one is already open. */
  function beginHold(): boolean {
    if (duringSave !== null) {
      return false;
    }
    duringSave = [];
    return true;
  }

  /** The highest reply number a payload read now contains. */
  function payloadMark(): number {
    return delivered;
  }

  /** After a save response or a replacing read: re-apply the replies it was read without. */
  function replayAfterResponse(mark: number): void {
    for (const reply of (duringSave ?? []).filter((entry) => entry.sequence > mark)) {
      writeReply(reply);
    }
  }

  function endHold(opened: boolean): void {
    if (opened) {
      duringSave = null;
    }
  }

  /** A reload, reopen or Spara som replaced the copy: every in-flight reply is stale. */
  function invalidateCopy(): void {
    copyGeneration += 1;
    pendingValues.clear();
  }

  /** A retry replaced just this question: only its in-flight replies are stale. */
  function invalidateItem(itemId: string): void {
    itemGenerations.set(itemId, (itemGenerations.get(itemId) ?? 0) + 1);
    for (const key of pendingValues.keys()) {
      if (key.startsWith(`${itemId}\u0000`)) {
        pendingValues.delete(key);
      }
    }
  }

  return {
    beginHold,
    endHold,
    invalidateCopy,
    invalidateItem,
    payloadMark,
    removeItemAutomaticValue,
    replayAfterResponse,
    updateItemGapValues,
  };
}
