/**
 * Exam workspace question list, Markera mode state.
 *
 * Domain purpose:
 *   The Markera mode lets a teacher tick standalone questions and group them
 *   into a new part (G2, G11). This composable holds the mode flag, the set
 *   of ticked question ids and the rules that decide which ticks count: only
 *   standalone questions (an item without a parent) are ever grouped, in
 *   document order (G10). A group the workspace accepts turns the ticks into
 *   a part's children, which ends the mode; a refused group keeps the ticks
 *   for a retry.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceQuestionList`, which renders the checkboxes and
 *     the group bar and passes the group command to the workspace.
 */

import { computed, ref, watch, type ComputedRef, type Ref } from "vue";

import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";

export type ExamWorkspaceQuestionMarkingOptions = {
  /** The list's entries in document order. */
  entries: () => ExamWorkspaceListEntry[];
  /** The workspace is busy: ticking waits like the list's other actions. */
  disabled: () => boolean;
  /** The group command, given the ticked standalone question ids in document order. */
  onGroup: (itemIds: string[]) => void;
};

export type ExamWorkspaceQuestionMarking = {
  /** The Markera mode: the list shows a checkbox per standalone question and a group bar. */
  marking: Ref<boolean>;
  /** The ticked question ids, which only ever hold standalone questions (G11). */
  marked: Ref<Set<string>>;
  /** The ticks in document order, as the group command takes them (G10). */
  markedIds: ComputedRef<string[]>;
  toggleMarking(): void;
  toggleMark(id: string): void;
  groupMarked(): void;
};

export function useExamWorkspaceQuestionMarking(
  options: ExamWorkspaceQuestionMarkingOptions,
): ExamWorkspaceQuestionMarking {
  const marking = ref(false);
  const marked = ref<Set<string>>(new Set());

  const markedIds = computed(() =>
    options
      .entries()
      .filter((entry) => entry.kind === "item" && entry.parentId === null && marked.value.has(entry.id))
      .map((entry) => entry.id),
  );

  function startMarking(): void {
    marked.value = new Set();
    marking.value = true;
  }

  function cancelMarking(): void {
    marked.value = new Set();
    marking.value = false;
  }

  function toggleMarking(): void {
    if (marking.value) {
      cancelMarking();
    } else {
      startMarking();
    }
  }

  function toggleMark(id: string): void {
    if (options.disabled()) {
      return;
    }
    const next = new Set(marked.value);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    marked.value = next;
  }

  function groupMarked(): void {
    if (markedIds.value.length === 0) {
      return;
    }
    options.onGroup(markedIds.value);
  }

  // A successful group turns the ticked questions into a part's children, so no
  // tick is a standalone question any more and the mode leaves with them; a
  // refused group changes nothing and keeps the ticks for a retry.
  watch(markedIds, (ids) => {
    if (marking.value && marked.value.size > 0 && ids.length === 0) {
      cancelMarking();
    }
  });

  return { marking, marked, markedIds, toggleMarking, toggleMark, groupMarked };
}
