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
 *   keeps the newest version, so the other tab's changes stay. A question the
 *   edit changed but the other tab deleted comes back.
 *
 *   Item content merges separately from derived positions: the selected
 *   ordered items go through the structure owner (`withMembers`, which
 *   renumbers items 1..n through `withUnits`), so positions never come from a
 *   snapshot. Asset declarations are the union of both tabs' declarations run
 *   through the asset owner (`withReferencedAssetsOnly`), so restored content
 *   keeps its pictures and unreferenced declarations drop. Parents are
 *   reconciled per part against the merged outline through the same structure
 *   owner, and header question tags are filtered to surviving items.
 *
 * Relationships:
 *   - Pure function consumed by `useExamWorkspaceEditing` on lease acquire;
 *     comparisons use `sameValue` from `examWorkspaceConversionMerge`.
 *   - Reads shapes from `api/examWorkspace.ts`.
 *   - Ordering, places and sequences are owned by `examWorkspaceStructure`;
 *     asset references are owned by its `withReferencedAssetsOnly`.
 */

import type {
  NativeExamAsset,
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { sameValue } from "./examWorkspaceConversionMerge";
import {
  withMembers,
  withReferencedAssetsOnly,
  type ExamWorkspaceMember,
} from "./examWorkspaceStructure";

/** Whether the edit left the document's content untouched; then there is nothing to keep. */
function sameContent(a: NativeExamDocument, b: NativeExamDocument): boolean {
  return sameValue({ ...a, revision: 1 }, { ...b, revision: 1 });
}

function byId(items: NativeExamItem[]): Map<string, NativeExamItem> {
  return new Map(items.map((item) => [item.item_id, item]));
}

function parentsById(parents: NativeExamParent[]): Map<string, NativeExamParent> {
  return new Map(parents.map((parent) => [parent.parent_id, parent]));
}

function orderOf(document: NativeExamDocument): string[] {
  return document.items.map((item) => item.item_id);
}

/** Item content without the derived position, so renumbering never reads as an edit. */
function sameItemContent(a: NativeExamItem, b: NativeExamItem): boolean {
  return sameValue({ ...a, sequence: 1 }, { ...b, sequence: 1 });
}

/** A part's own content without its derived place; membership is reconciled separately. */
function sameParentInstruction(a: NativeExamParent, b: NativeExamParent): boolean {
  return sameValue(
    { instruction: a.instruction, printed_total: a.printed_total ?? null },
    { instruction: b.instruction, printed_total: b.printed_total ?? null },
  );
}

/** The part holding the item in this document, or null when it stands alone. */
function parentIdIn(document: NativeExamDocument, itemId: string): string | null {
  for (const parent of document.parents) {
    if (parent.item_ids.includes(itemId)) {
      return parent.parent_id;
    }
  }
  return null;
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

  const mergedContent = new Map<string, NativeExamItem>();
  for (const item of newest.items) {
    const baseItem = baseItems.get(item.item_id);
    const editedItem = editedItems.get(item.item_id);
    if (baseItem !== undefined && editedItem !== undefined) {
      // Changed on either side: the kept edit wins when it changed the content.
      mergedContent.set(
        item.item_id,
        sameItemContent(editedItem, baseItem) ? item : editedItem,
      );
    } else if (baseItem !== undefined && editedItem === undefined) {
      // The edit removed the item: it stays removed.
    } else {
      mergedContent.set(item.item_id, item);
    }
  }
  for (const item of edited.items) {
    const baseItem = baseItems.get(item.item_id);
    if (baseItem === undefined) {
      // The edit added the item; on an id collision the kept edit wins.
      mergedContent.set(item.item_id, item);
    } else if (!sameItemContent(item, baseItem) && !newestItems.has(item.item_id)) {
      // The edit changed the item but the other tab deleted it: add it back.
      mergedContent.set(item.item_id, item);
    }
  }

  const editedIds = new Set(orderOf(edited));
  const orderedIds: string[] = [];
  const orderedSeen = new Set<string>();
  const pushId = (itemId: string) => {
    if (mergedContent.has(itemId) && !orderedSeen.has(itemId)) {
      orderedSeen.add(itemId);
      orderedIds.push(itemId);
    }
  };
  if (sameValue(orderOf(edited), orderOf(base))) {
    for (const itemId of orderOf(newest)) {
      pushId(itemId);
    }
    for (const itemId of orderOf(edited)) {
      if (!newestItems.has(itemId)) {
        pushId(itemId);
      }
    }
  } else {
    for (const itemId of orderOf(edited)) {
      pushId(itemId);
    }
    for (const itemId of orderOf(newest)) {
      if (!editedIds.has(itemId)) {
        pushId(itemId);
      }
    }
  }
  const orderedItems: NativeExamItem[] = [];
  for (const itemId of orderedIds) {
    const item = mergedContent.get(itemId);
    if (item !== undefined) {
      orderedItems.push(item);
    }
  }

  const mergedTitle = sameValue(edited.title, base.title) ? newest.title : edited.title;
  const mergedHeader = sameValue(edited.header, base.header) ? newest.header : edited.header;
  const mergedInstructions = sameValue(edited.instructions, base.instructions)
    ? newest.instructions
    : edited.instructions;

  const baseParents = parentsById(base.parents);
  const editedParents = parentsById(edited.parents);
  const newestParents = parentsById(newest.parents);
  const allParentIds: string[] = [];
  for (const parent of [...base.parents, ...edited.parents, ...newest.parents]) {
    if (!allParentIds.includes(parent.parent_id)) {
      allParentIds.push(parent.parent_id);
    }
  }
  const instructionParents = new Map<string, NativeExamParent>();
  for (const parentId of allParentIds) {
    const baseParent = baseParents.get(parentId);
    const editedParent = editedParents.get(parentId);
    const newestParent = newestParents.get(parentId);
    if (baseParent !== undefined) {
      if (editedParent !== undefined && newestParent !== undefined) {
        instructionParents.set(
          parentId,
          sameParentInstruction(editedParent, baseParent) ? newestParent : editedParent,
        );
      } else if (editedParent !== undefined && newestParent === undefined) {
        // The other tab deleted the part: it comes back only when the edit touched it.
        const touched = !sameValue(
          { ...editedParent, place: 0 },
          { ...baseParent, place: 0 },
        );
        if (touched) {
          instructionParents.set(parentId, editedParent);
        }
      } else if (editedParent === undefined) {
        // The edit deleted the part: it stays deleted.
      }
    } else if (editedParent !== undefined) {
      instructionParents.set(parentId, editedParent);
    } else if (newestParent !== undefined) {
      instructionParents.set(parentId, newestParent);
    }
  }

  const mergedParentOf = new Map<string, string | null>();
  for (const item of orderedItems) {
    const baseOwner = baseItems.has(item.item_id) ? parentIdIn(base, item.item_id) : undefined;
    const editedOwner = editedItems.has(item.item_id)
      ? parentIdIn(edited, item.item_id)
      : undefined;
    const newestOwner = newestItems.has(item.item_id)
      ? parentIdIn(newest, item.item_id)
      : undefined;
    let owner: string | null | undefined;
    if (editedOwner !== baseOwner) {
      owner = editedOwner;
    } else {
      owner = newestOwner;
    }
    if (owner === undefined) {
      owner = editedOwner ?? newestOwner ?? null;
    }
    if (owner !== null && !instructionParents.has(owner)) {
      owner = null;
    }
    if (item.kind === "ordering") {
      // Ordering questions are standalone only; never leave one inside a part.
      owner = null;
    }
    mergedParentOf.set(item.item_id, owner ?? null);
  }

  const members: ExamWorkspaceMember[] = orderedItems.map((item) => ({
    kind: "item",
    item,
    parentId: mergedParentOf.get(item.item_id) ?? null,
  }));
  const assigned = new Set<string>();
  for (const owner of mergedParentOf.values()) {
    if (owner !== null) {
      assigned.add(owner);
    }
  }
  const blocks: NativeExamParent[] = [];
  for (const parent of instructionParents.values()) {
    if (!assigned.has(parent.parent_id)) {
      blocks.push(parent);
    }
  }
  blocks.sort((a, b) => a.place - b.place);
  for (const block of blocks) {
    const at = Math.min(Math.max(block.place, 0), members.length);
    members.splice(at, 0, { kind: "block", parentId: block.parent_id });
  }

  const parentList = [...instructionParents.values()];
  const structured = withMembers(
    {
      ...newest,
      assets: [],
      instructions: mergedInstructions,
      items: orderedItems,
      parents: parentList,
      title: mergedTitle,
    },
    members,
    parentList,
  );

  const union = new Map<string, NativeExamAsset>();
  const unionOrder: string[] = [];
  for (const entry of newest.assets) {
    if (!union.has(entry.asset_id)) {
      unionOrder.push(entry.asset_id);
    }
    union.set(entry.asset_id, entry);
  }
  for (const entry of edited.assets) {
    if (!union.has(entry.asset_id)) {
      unionOrder.push(entry.asset_id);
    }
    // The kept edit wins when both tabs declare the same asset.
    union.set(entry.asset_id, entry);
  }
  const unionAssets: NativeExamAsset[] = [];
  for (const assetId of unionOrder) {
    const entry = union.get(assetId);
    if (entry !== undefined) {
      unionAssets.push(entry);
    }
  }
  const keptAssets = withReferencedAssetsOnly({ ...structured, assets: unionAssets });

  const surviving = new Set(keptAssets.items.map((item) => item.item_id));
  const filteredHeader = {
    ...mergedHeader,
    tags: mergedHeader.tags.map((tag) => ({
      ...tag,
      question_ids: tag.question_ids.filter((questionId) => surviving.has(questionId)),
    })),
  };

  return {
    ...keptAssets,
    header: filteredHeader,
    revision: newest.revision,
    document_id: newest.document_id,
    origin: newest.origin,
    schema_version: newest.schema_version,
  };
}
