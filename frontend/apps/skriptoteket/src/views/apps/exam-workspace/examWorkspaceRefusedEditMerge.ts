/**
 * Exam workspace refused-edit merge.
 *
 * Domain purpose:
 *   A refused edit survives the takeover (TASK-SKRIPT-40-04-14, USER decision
 *   2026-10-19 "Ta över keeps the edit"): after the tab gets the edit lease
 *   back, the edit refused with `EDIT_LEASE_HELD` is merged onto the newest
 *   server document and stored through the normal save path, so nothing is
 *   lost. The kept edit wins: every piece where the edited working copy
 *   differs from the history's step document replaces the newest version,
 *   because the teacher chose to keep it; every piece the edit did not change
 *   keeps the newest version, so the other tab's changes stay.
 *
 * Relationships:
 *   - Pure function consumed by `useExamWorkspaceEditing` on lease acquire;
 *     comparisons use `sameValue` from `examWorkspaceConversionMerge`.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import { sameValue } from "./examWorkspaceConversionMerge";

/** Whether the edit left the document's content untouched; then there is nothing to keep. */
function sameContent(a: NativeExamDocument, b: NativeExamDocument): boolean {
  return sameValue({ ...a, revision: 1 }, { ...b, revision: 1 });
}

function byId(items: NativeExamItem[]): Map<string, NativeExamItem> {
  return new Map(items.map((item) => [item.item_id, item]));
}

function orderOf(document: NativeExamDocument): string[] {
  return document.items.map((item) => item.item_id);
}

/**
 * Merge a refused edit onto the newest server document. `base` is the step
 * the edit started from, `edited` the refused working copy, `newest` the
 * reloaded server document. Returns the document to install, or null when
 * the edit changed nothing.
 */
export function mergeRefusedEdit(
  base: NativeExamDocument,
  edited: NativeExamDocument,
  newest: NativeExamDocument,
): NativeExamDocument | null {
  if (sameContent(edited, base)) {
    return null;
  }
  const baseItems = byId(base.items);
  const editedItems = byId(edited.items);
  const newestItems = byId(newest.items);

  const merged = new Map<string, NativeExamItem>();
  for (const item of newest.items) {
    const baseItem = baseItems.get(item.item_id);
    const editedItem = editedItems.get(item.item_id);
    if (baseItem !== undefined && editedItem !== undefined && !sameValue(editedItem, baseItem)) {
      // Changed on both sides: the kept edit wins.
      merged.set(item.item_id, editedItem);
    } else if (baseItem !== undefined && editedItem === undefined) {
      // The edit removed the item: it stays removed.
    } else {
      merged.set(item.item_id, item);
    }
  }
  for (const item of edited.items) {
    const baseItem = baseItems.get(item.item_id);
    if (baseItem === undefined) {
      // The edit added the item.
      merged.set(item.item_id, item);
    } else if (!sameValue(item, baseItem) && !newestItems.has(item.item_id)) {
      // The edit changed the item but the other tab deleted it: add it back.
      merged.set(item.item_id, item);
    }
  }

  const editedIds = new Set(orderOf(edited));
  const mergedIds = new Set(merged.keys());
  const ordered: NativeExamItem[] = [];
  if (sameValue(orderOf(edited), orderOf(base))) {
    for (const itemId of orderOf(newest)) {
      const item = merged.get(itemId);
      if (item !== undefined) {
        ordered.push(item);
      }
    }
    for (const itemId of orderOf(edited)) {
      if (!newestItems.has(itemId) && mergedIds.has(itemId)) {
        const item = merged.get(itemId);
        if (item !== undefined) {
          ordered.push(item);
        }
      }
    }
  } else {
    for (const itemId of orderOf(edited)) {
      const item = merged.get(itemId);
      if (item !== undefined) {
        ordered.push(item);
      }
    }
    for (const itemId of orderOf(newest)) {
      if (!editedIds.has(itemId)) {
        const item = merged.get(itemId);
        if (item !== undefined) {
          ordered.push(item);
        }
      }
    }
  }

  return {
    ...newest,
    title: sameValue(edited.title, base.title) ? newest.title : edited.title,
    header: sameValue(edited.header, base.header) ? newest.header : edited.header,
    instructions: sameValue(edited.instructions, base.instructions)
      ? newest.instructions
      : edited.instructions,
    assets: sameValue(edited.assets, base.assets) ? newest.assets : edited.assets,
    parents: sameValue(edited.parents, base.parents) ? newest.parents : edited.parents,
    items: ordered,
    revision: newest.revision,
    document_id: newest.document_id,
    origin: newest.origin,
    schema_version: newest.schema_version,
  };
}
