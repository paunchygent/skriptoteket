/**
 * Exam workspace AI suggestion arrivals and their reconciliation with saves.
 *
 * Domain purpose:
 *   Write each arriving AI answer-key suggestion onto its question once, and
 *   keep that single effect when a save's outcome replaces the open copy
 *   (TASK-SKRIPT-39-04-07). Each arrival gets a sequence number. A save
 *   records the number its payload has reached: the payload holds every
 *   arrival up to that mark and none after it. When a server document
 *   replaces the copy, the arrivals it was built without run once more, in
 *   order, against that document. That is a save response's arrivals after
 *   its mark, or every arrival since the teacher's save for a conflict
 *   reload. A failed save leaves the copy, so nothing runs again. Whether an
 *   arrival runs again depends on when it arrived, never on the values the
 *   replacing document holds. Every write, first delivery and replay alike,
 *   checks at that moment that the exam opening the arrival was requested
 *   for is still open, so a job of another exam never writes into this one.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceDocument`, which owns the save lifecycle.
 *   - Applies `withArrivingSuggestion` from `examWorkspaceItemEdits`.
 *   - Compares items with `sameValue` from `examWorkspaceConversionMerge`, so
 *     an arrival that changes nothing leaves the copy as it was. Dirty state
 *     is the document owner's: it derives it from the copy.
 */

import type { Ref } from "vue";

import type {
  ExamWorkspaceAnswerKeySuggestionItem,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { sameValue } from "./examWorkspaceConversionMerge";
import { withArrivingSuggestion } from "./examWorkspaceSuggestionEdits";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";

type NumberedArrival = {
  entry: ExamWorkspaceAnswerKeySuggestionItem;
  opening: ExamWorkspaceOpening;
  sequence: number;
};

type SaveArrivalsBinding = {
  convertingItemIds: Readonly<Ref<ReadonlySet<string>>>;
  isOpen: (opening: ExamWorkspaceOpening) => boolean;
  workspaceDocument: Ref<NativeExamDocument | null>;
};

export function useExamWorkspaceSaveArrivals(binding: SaveArrivalsBinding) {
  let delivered = 0;
  // Arrivals written since the teacher's save began; null while no save runs.
  let duringSave: NumberedArrival[] | null = null;

  /**
   * Write suggestions onto their questions in one update when the opening
   * they were requested for is still open; returns the written entries.
   */
  function writeArrivals(
    opening: ExamWorkspaceOpening,
    suggestions: ExamWorkspaceAnswerKeySuggestionItem[],
  ): ExamWorkspaceAnswerKeySuggestionItem[] {
    const current = binding.workspaceDocument.value;
    if (!current || !binding.isOpen(opening) || suggestions.length === 0) {
      return [];
    }
    const byItemId = new Map(suggestions.map((entry) => [entry.item_id, entry.suggestion]));
    const written: ExamWorkspaceAnswerKeySuggestionItem[] = [];
    let changed = false;
    const items = current.items.map((item) => {
      const suggestion = byItemId.get(item.item_id);
      if (!suggestion || binding.convertingItemIds.value.has(item.item_id)) {
        return item;
      }
      written.push({ item_id: item.item_id, suggestion });
      const next = withArrivingSuggestion(item, suggestion);
      if (sameValue(next, item)) {
        return item;
      }
      changed = true;
      return next;
    });
    if (changed) {
      binding.workspaceDocument.value = { ...current, items };
    }
    return written;
  }

  /** Write every arriving suggestion of `opening` onto its question, numbering each arrival. */
  function applyArrivingSuggestions(
    opening: ExamWorkspaceOpening,
    suggestions: ExamWorkspaceAnswerKeySuggestionItem[],
  ): void {
    for (const entry of writeArrivals(opening, suggestions)) {
      delivered += 1;
      duringSave?.push({ entry, opening, sequence: delivered });
    }
  }

  /**
   * Start listing arrivals for the teacher's save. Returns whether this call
   * opened the list; the recursive save after a conversion merge joins the
   * list its outer save opened.
   */
  function beginSave(): boolean {
    if (duringSave !== null) {
      return false;
    }
    duringSave = [];
    return true;
  }

  /** The highest arrival number a payload read now contains. */
  function payloadMark(): number {
    return delivered;
  }

  function replay(arrivals: NumberedArrival[]): void {
    for (const { entry, opening } of arrivals) {
      writeArrivals(opening, [entry]);
    }
  }

  /** After a save response: replay the arrivals its payload was read without. */
  function replayAfterResponse(mark: number): void {
    replay((duringSave ?? []).filter((arrival) => arrival.sequence > mark));
  }

  /** After a conflict reload: replay every arrival since the teacher's save began. */
  function replayAfterReload(): void {
    replay(duringSave ?? []);
  }

  function endSave(opened: boolean): void {
    if (opened) {
      duringSave = null;
    }
  }

  return {
    applyArrivingSuggestions,
    beginSave,
    endSave,
    payloadMark,
    replayAfterReload,
    replayAfterResponse,
  };
}
