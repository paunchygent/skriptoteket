/**
 * Exam workspace refused-edit merge.
 *
 * Domain purpose:
 *   A refused edit survives the takeover (TASK-SKRIPT-40-04-14, USER decision
 *   2026-10-19 "Ta över keeps the edit"): after the tab gets the edit lease
 *   back, the kept edit is merged onto the newest server document and stored
 *   through the normal save path, so nothing is lost. The merge takes
 *   explicit ownership: `mergeRefusedEdit(desired, owned, newest)` returns
 *   the document to install. For a piece in `owned` the desired value wins,
 *   including absence (a deletion); everything else stays the newest
 *   version. A question in `owned` wins whole, even when the other tab
 *   changed it later; untouched questions and fields stay newest.
 *
 *   Item content merges separately from derived positions: the selected
 *   ordered items go through the structure owner (`withMembers`, which
 *   renumbers items 1..n through `withUnits`), so positions never come from a
 *   snapshot. Parents are reconciled per part against the merged outline
 *   through the same structure owner, the local order wins only when the
 *   order piece is owned, and header question tags are filtered to
 *   surviving items. Asset declarations are the union of both tabs' declarations
 *   run through the asset owner (`withReferencedAssetsOnly`), so restored
 *   content keeps its pictures and unreferenced declarations drop.
 *   Complementary deletions that would leave no question keep the whole
 *   desired document (L9).
 *
 * Relationships:
 *   - Pure function consumed by `useExamWorkspaceEditing` and the sync
 *     gate's recovery commit; comparisons use `sameValue` from
 *     `examWorkspaceConversionMerge`, piece keys from
 *     `examWorkspaceEditPieces`.
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
import {
  EDIT_PIECE_HEADER,
  EDIT_PIECE_INSTRUCTIONS,
  EDIT_PIECE_OUTLINE,
  EDIT_PIECE_QUESTION_ORDER,
  EDIT_PIECE_TITLE,
  membershipPiece,
  parentIdIn,
  parentPiece,
  questionPiece,
} from "./examWorkspaceEditPieces";
import {
  withMembers,
  withReferencedAssetsOnly,
  type ExamWorkspaceMember,
} from "./examWorkspaceStructure";

function byId(items: NativeExamItem[]): Map<string, NativeExamItem> {
  return new Map(items.map((item) => [item.item_id, item]));
}

function parentsById(parents: NativeExamParent[]): Map<string, NativeExamParent> {
  return new Map(parents.map((parent) => [parent.parent_id, parent]));
}

function orderOf(document: NativeExamDocument): string[] {
  return document.items.map((item) => item.item_id);
}

/**
 * Merge owned pieces of the desired copy onto the newest server document.
 * `owned` holds piece keys from `examWorkspaceEditPieces`; an empty set
 * returns the newest copy. Always returns a document to install.
 */
export function mergeRefusedEdit(
  desired: NativeExamDocument,
  owned: ReadonlySet<string>,
  newest: NativeExamDocument,
): NativeExamDocument {
  if (owned.size === 0) {
    return newest;
  }
  const desiredItems = byId(desired.items);
  const newestItems = byId(newest.items);

  const mergedContent = new Map<string, NativeExamItem>();
  for (const item of newest.items) {
    if (owned.has(questionPiece(item.item_id))) {
      // The desired copy owns this question: its value wins, including absence.
      const ownedItem = desiredItems.get(item.item_id);
      if (ownedItem !== undefined) {
        mergedContent.set(item.item_id, ownedItem);
      }
    } else {
      mergedContent.set(item.item_id, item);
    }
  }
  for (const item of desired.items) {
    if (!newestItems.has(item.item_id) && owned.has(questionPiece(item.item_id))) {
      // The desired copy added or restored the question: it comes back only owned.
      mergedContent.set(item.item_id, item);
    }
  }

  const desiredIds = new Set(orderOf(desired));
  const orderedIds: string[] = [];
  const orderedSeen = new Set<string>();
  const pushId = (itemId: string) => {
    if (mergedContent.has(itemId) && !orderedSeen.has(itemId)) {
      orderedSeen.add(itemId);
      orderedIds.push(itemId);
    }
  };
  if (owned.has(EDIT_PIECE_QUESTION_ORDER)) {
    for (const itemId of orderOf(desired)) {
      pushId(itemId);
    }
    for (const itemId of orderOf(newest)) {
      if (!desiredIds.has(itemId)) {
        pushId(itemId);
      }
    }
  } else {
    for (const itemId of orderOf(newest)) {
      pushId(itemId);
    }
    for (const itemId of orderOf(desired)) {
      if (!newestItems.has(itemId)) {
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

  const mergedTitle = owned.has(EDIT_PIECE_TITLE) ? desired.title : newest.title;
  const mergedHeader = owned.has(EDIT_PIECE_HEADER) ? desired.header : newest.header;
  const mergedInstructions = owned.has(EDIT_PIECE_INSTRUCTIONS)
    ? desired.instructions
    : newest.instructions;

  const desiredParents = parentsById(desired.parents);
  const newestParents = parentsById(newest.parents);
  const allParentIds: string[] = [];
  for (const parent of [...desired.parents, ...newest.parents]) {
    if (!allParentIds.includes(parent.parent_id)) {
      allParentIds.push(parent.parent_id);
    }
  }
  const instructionParents = new Map<string, NativeExamParent>();
  for (const parentId of allParentIds) {
    const desiredParent = desiredParents.get(parentId);
    const newestParent = newestParents.get(parentId);
    if (owned.has(parentPiece(parentId))) {
      // The desired copy owns this part: its value wins, including absence.
      if (desiredParent !== undefined) {
        instructionParents.set(parentId, desiredParent);
      }
    } else if (newestParent !== undefined) {
      instructionParents.set(parentId, newestParent);
    } else if (desiredParent !== undefined) {
      instructionParents.set(parentId, desiredParent);
    }
  }

  // Complementary deletions on both sides can leave no question at all, which
  // the server rejects. The desired copy wins whole then: the merged result is
  // the desired document carried onto the newest identity fields, with
  // positions and assets through the existing owners as for any merge.
  const keptWhole = orderedItems.length === 0;
  const activeItems = keptWhole ? [...desired.items] : orderedItems;
  const activeTitle = keptWhole ? desired.title : mergedTitle;
  const activeHeader = keptWhole ? desired.header : mergedHeader;
  const activeInstructions = keptWhole ? desired.instructions : mergedInstructions;
  const activeInstructionParents = keptWhole ? parentsById(desired.parents) : instructionParents;

  const mergedParentOf = new Map<string, string | null>();
  for (const item of activeItems) {
    const desiredOwner = desiredItems.has(item.item_id)
      ? parentIdIn(desired, item.item_id)
      : undefined;
    const newestOwner = newestItems.has(item.item_id) ? parentIdIn(newest, item.item_id) : undefined;
    let owner: string | null | undefined;
    if (owned.has(membershipPiece(item.item_id))) {
      owner = desiredOwner;
    } else {
      owner = newestOwner;
    }
    if (owner === undefined) {
      owner = desiredOwner ?? newestOwner ?? null;
    }
    if (owner !== null && !activeInstructionParents.has(owner)) {
      owner = null;
    }
    if (item.kind === "ordering") {
      // Ordering questions are standalone only; never leave one inside a part.
      owner = null;
    }
    mergedParentOf.set(item.item_id, owner ?? null);
  }

  const members: ExamWorkspaceMember[] = activeItems.map((item) => ({
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
  // The desired copy wins where it owned the block outline (order or
  // placement); otherwise the newest outline wins. Base-first map order is
  // never the outline order: the blocks below enter in the selected
  // document's order, and the stable place sort only breaks ties.
  const outlineSource = keptWhole || owned.has(EDIT_PIECE_OUTLINE) ? desired : newest;
  const outlineFallback = outlineSource === desired ? newest : desired;
  const blockIds = new Set<string>();
  for (const parent of activeInstructionParents.values()) {
    if (!assigned.has(parent.parent_id)) {
      blockIds.add(parent.parent_id);
    }
  }
  const orderedBlockIds: string[] = [];
  for (const parents of [outlineSource.parents, outlineFallback.parents]) {
    for (const parent of parents) {
      if (blockIds.has(parent.parent_id) && !orderedBlockIds.includes(parent.parent_id)) {
        orderedBlockIds.push(parent.parent_id);
      }
    }
  }
  for (const parent of activeInstructionParents.values()) {
    if (blockIds.has(parent.parent_id) && !orderedBlockIds.includes(parent.parent_id)) {
      orderedBlockIds.push(parent.parent_id);
    }
  }
  const blocks: NativeExamParent[] = [];
  for (const parentId of orderedBlockIds) {
    const parent = activeInstructionParents.get(parentId);
    if (parent !== undefined) {
      blocks.push(parent);
    }
  }
  // A part's place counts preceding questions, not members: previously
  // inserted blocks already shift the member indices. Sort stably by place so
  // equal-place blocks keep their selected order, then offset each insertion
  // by the blocks already placed before it.
  const blockOrder = new Map(blocks.map((block, index) => [block.parent_id, index]));
  blocks.sort((a, b) => {
    if (a.place !== b.place) {
      return a.place - b.place;
    }
    const aIndex = blockOrder.get(a.parent_id);
    const bIndex = blockOrder.get(b.parent_id);
    return (aIndex ?? 0) - (bIndex ?? 0);
  });
  const questionCount = members.length;
  let insertedBlocks = 0;
  for (const block of blocks) {
    const at = Math.min(Math.max(block.place, 0), questionCount) + insertedBlocks;
    members.splice(at, 0, { kind: "block", parentId: block.parent_id });
    insertedBlocks += 1;
  }

  const parentList = [...activeInstructionParents.values()];
  const structured = withMembers(
    {
      ...newest,
      assets: [],
      instructions: activeInstructions,
      items: activeItems,
      parents: parentList,
      title: activeTitle,
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
  for (const entry of desired.assets) {
    if (!union.has(entry.asset_id)) {
      unionOrder.push(entry.asset_id);
    }
    // The desired copy wins when both tabs declare the same asset.
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
    ...activeHeader,
    tags: activeHeader.tags.map((tag) => ({
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
