/**
 * Exam workspace teacher edit paths.
 *
 * Domain purpose:
 *   Own the paths every teacher edit of the open copy takes: the one item
 *   patch path, the whole-copy edit path, the title, a restored suggestion,
 *   and the gap keying, item and field commands built on them. Each path
 *   refuses while the copy is busy or read-only, applies an immutable update
 *   and reports the edit through `noteEdit`.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceDocument`, which passes its open copy, its
 *     selection, its busy and read-only guards, the converting placeholders,
 *     the session's new pictures and its edit reports.
 *   - Item edit commands through `useExamWorkspaceItemEdits`; gap keying and
 *     its misspelling replies through `useExamWorkspaceGapKeying`; the
 *     whole-document field commands through `useExamWorkspaceDocumentFields`.
 *   - The document owner reads `keying` for its open, reload, replacing and
 *     retry lifecycles, which drop keying replies that lost their place.
 */

import type { ComputedRef, Ref, ShallowRef } from "vue";

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import type { ExamWorkspaceNewPictures } from "./examWorkspaceNewPictures";
import { withReferencedAssetsOnly } from "./examWorkspaceStructure";
import { withRestoredSuggestion } from "./examWorkspaceSuggestionEdits";
import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import { useExamWorkspaceDocumentFields } from "./useExamWorkspaceDocumentFields";
import { useExamWorkspaceGapKeying } from "./useExamWorkspaceGapKeying";
import { useExamWorkspaceItemEdits } from "./useExamWorkspaceItemEdits";

export type ExamWorkspaceDocumentEditPathsBinding = {
  workspaceDocument: Ref<NativeExamDocument | null>;
  selectedItemId: Ref<string | null>;
  openExam: Readonly<ShallowRef<ExamWorkspaceOpening | null>>;
  /** No edit may start: an operation runs or the copy is about to be replaced. */
  isBusy: ComputedRef<boolean>;
  /** True while another tab holds the edit lease: every edit entry refuses. */
  isReadOnly: () => boolean;
  /** Placeholders whose batch still converts; their items refuse edits. */
  convertingItemIds: Readonly<Ref<ReadonlySet<string>>>;
  /** Pictures added from files this session, declared into every edited copy. */
  newPictures: ExamWorkspaceNewPictures;
  /**
   * A teacher edit changed the copy; structural edits become an undo step at
   * once. `before` is the copy just before the edit.
   */
  noteEdit: (structural: boolean, before: NativeExamDocument | null) => void;
  /** A keyed spelling landed in the copy; stored like typing after the pause. */
  noteMachineWrite: (before: NativeExamDocument) => void;
  /** The shared store half the misspelling request runs through. */
  shared: ExamWorkspaceSharedStore;
};

export function useExamWorkspaceDocumentEditPaths(binding: ExamWorkspaceDocumentEditPathsBinding) {
  const {
    workspaceDocument,
    selectedItemId,
    isBusy,
    isReadOnly,
    convertingItemIds,
    newPictures,
    noteEdit,
  } = binding;

  function setTitle(title: string): void {
    const current = workspaceDocument.value;
    if (!current || isBusy.value || isReadOnly()) return;
    workspaceDocument.value = { ...current, title };
    noteEdit(false, current);
  }

  /**
   * The one path every item edit takes; a placeholder whose batch still converts is refused.
   * A picture the edit removed takes its asset record with it.
   */
  function patchItem(
    itemId: string,
    patch: (item: NativeExamItem) => NativeExamItem,
    structural = false,
  ): boolean {
    const current = workspaceDocument.value;
    if (!current || isBusy.value || isReadOnly() || convertingItemIds.value.has(itemId)) {
      return false;
    }
    let changed = false;
    const items = current.items.map((item) => {
      if (item.item_id !== itemId) {
        return item;
      }
      changed = true;
      return patch(item);
    });
    if (!changed) {
      return false;
    }
    workspaceDocument.value = withReferencedAssetsOnly(newPictures.withDeclared({ ...current, items }));
    noteEdit(structural, current);
    return true;
  }

  // Every gap keying edit and its asynchronous misspelling reply.
  const keying = useExamWorkspaceGapKeying({
    noteReply: binding.noteMachineWrite,
    openExam: binding.openExam,
    patchItem,
    workspaceDocument,
    shared: binding.shared,
  });

  // Every teacher edit command, applied through the one patch path above.
  const itemEdits = useExamWorkspaceItemEdits(patchItem);

  function restoreItemSuggestion(itemId: string): void {
    patchItem(itemId, (item) => withRestoredSuggestion(item));
  }

  /**
   * An edit of the whole copy. A structural edit (add, delete, reorder) is one
   * undo step at once; typing waits for the pause like an item's text.
   */
  function editDocument(
    edit: (document: NativeExamDocument) => NativeExamDocument,
    selectId: string | null = null,
    structural = true,
  ): boolean {
    const current = workspaceDocument.value;
    if (!current || isBusy.value || isReadOnly()) {
      return false;
    }
    workspaceDocument.value = withReferencedAssetsOnly(newPictures.withDeclared(edit(current)));
    if (selectId !== null) {
      selectedItemId.value = selectId;
    }
    noteEdit(structural, current);
    return true;
  }

  // The whole-document field commands, each one `editDocument` call.
  const fieldCommands = useExamWorkspaceDocumentFields({
    courseKey: () => workspaceDocument.value?.header.course?.key ?? null,
    editDocument,
  });

  return { editDocument, fieldCommands, itemEdits, keying, restoreItemSuggestion, setTitle };
}
