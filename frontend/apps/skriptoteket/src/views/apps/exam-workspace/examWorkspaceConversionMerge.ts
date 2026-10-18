/**
 * Exam workspace conversion merge.
 *
 * Domain purpose:
 *   The background DOCX conversion saves newer server revisions while the
 *   teacher keeps editing a local, possibly unsaved copy. This module merges
 *   such a revision into the local copy, one conversion unit (one outline
 *   question, or one review item no question owns) at a time. A unit that was
 *   still converting in the base is a placeholder and belongs to conversion:
 *   the head's items always replace it, in place, or after the nearest
 *   preceding unit when the local copy lacks it, whatever the local copy
 *   holds. A converted unit is replaced by the head's items only while the
 *   teacher has not touched it since the base the local copy started from;
 *   otherwise the teacher's version stays. The title, the header, the instructions and
 *   the parents follow the converted-unit rule. The merge computes no part
 *   place: it builds a flat member list in document order (each converted
 *   item keeps the part of the item it replaces) and hands it to the
 *   structure owner `withMembers`, whose grouping rule assigns item sequences
 *   and part places (R1). Items the teacher added belong to no unit and keep
 *   their place; when the head is a later save from another tab, its edits of
 *   such items follow the same rule and the items it added are kept after the
 *   head item they follow.
 *
 * Relationships:
 *   - Client twin of `merge_conversion` in
 *     `application/curated_apps/handlers/exam_workspace_conversion_merge.py`,
 *     which applies the same rule on the server against the saved head.
 *   - `examWorkspaceMembers` reads the local copy as members and `withMembers`
 *     groups the merged members back into units. The merge never reconstructs
 *     the ordering rule itself.
 *   - Pure function consumed by `useExamWorkspaceConversion` and
 *     `useExamWorkspaceDocument`; `sameDocument` is the one rule that tells
 *     `useExamWorkspaceDocument` whether the copy is dirty, and `sameValue`
 *     tells `useExamWorkspaceSaveArrivals` whether an arrival changed an item.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type {
  ExamWorkspaceConversionUnit,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import type { ExamWorkspaceMember } from "./examWorkspaceStructure";
import { examWorkspaceMembers, withMembers } from "./examWorkspaceStructure";

type MergeArgs = {
  base: NativeExamDocument;
  /** The units of `base`, with the state each had in it. */
  baseUnits: ExamWorkspaceConversionUnit[];
  local: NativeExamDocument;
  head: NativeExamDocument;
  headUnits: ExamWorkspaceConversionUnit[];
};

type Entry =
  | {
      kind: "item";
      fromHead: boolean;
      item: NativeExamItem;
      unit: string | null;
      parentId: string | null;
    }
  | { kind: "block"; parentId: string };

type ItemEntry = Extract<Entry, { kind: "item" }>;

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(sortKeys);
  }
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value).filter(([, entry]) => entry != null);
    entries.sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
    return Object.fromEntries(
      entries.map(([key, entry]) => [key, sortKeys(entry)]),
    );
  }
  return value;
}

/** Key-order and null/absent insensitive deep equality. */
export function sameValue(a: unknown, b: unknown): boolean {
  return JSON.stringify(sortKeys(a)) === JSON.stringify(sortKeys(b));
}

/**
 * Whether two documents hold the same value. An item both documents share
 * by reference is equal without being serialised, so typing in one question
 * compares only that question.
 */
export function sameDocument(
  a: NativeExamDocument | null,
  b: NativeExamDocument | null,
): boolean {
  if (a === b) {
    return true;
  }
  if (a === null || b === null || a.items.length !== b.items.length) {
    return false;
  }
  const { items: aItems, ...aRest } = a;
  const { items: bItems, ...bRest } = b;
  return (
    sameValue(aRest, bRest) &&
    aItems.every((item, index) => item === bItems[index] || sameValue(item, bItems[index]))
  );
}

/** Item content without ids and positions, so renumbering never reads as an edit. */
function sameItems(a: NativeExamItem[], b: NativeExamItem[]): boolean {
  const content = (items: NativeExamItem[]) =>
    items.map(({ item_id: _id, sequence: _sequence, ...rest }) => rest);
  return sameValue(content(a), content(b));
}

/** The next free `item_NNN` id: one above the highest numbered id in use. */
export function nextItemId(itemIds: string[]): string {
  const used = new Set(itemIds);
  let highest = 0;
  for (const itemId of itemIds) {
    const match = /^item_(\d+)$/.exec(itemId);
    if (match) {
      highest = Math.max(highest, Number(match[1]));
    }
  }
  let candidate = highest + 1;
  while (used.has(`item_${String(candidate).padStart(3, "0")}`)) {
    candidate += 1;
  }
  return `item_${String(candidate).padStart(3, "0")}`;
}

/** The server's value when the teacher left the base untouched, otherwise the teacher's. */
function pick<T>(base: T, local: T, head: T): { fromHead: boolean; value: T } {
  if (sameValue(base, head)) {
    return { fromHead: false, value: local };
  }
  if (sameValue(local, base)) {
    return { fromHead: true, value: head };
  }
  return { fromHead: false, value: local };
}

function itemEntries(entries: Entry[]): ItemEntry[] {
  return entries.filter((entry): entry is ItemEntry => entry.kind === "item");
}

/** The position after the last item entry of `unitId`, or the start when it has none. */
function insertionIndex(
  entries: Entry[],
  headUnits: ExamWorkspaceConversionUnit[],
  at: number,
): number {
  for (let index = at - 1; index >= 0; index -= 1) {
    const unitId = headUnits[index]!.unit_id;
    for (let position = entries.length - 1; position >= 0; position -= 1) {
      const entry = entries[position]!;
      if (entry.kind === "item" && entry.unit === unitId) {
        return position + 1;
      }
    }
  }
  return 0;
}

/**
 * The part an inserted item joins: the part shared by the entries around the
 * insert position, and only when both are item entries carrying that same part.
 */
function neighbourParentId(entries: Entry[], index: number): string | null {
  const before = entries[index - 1];
  const after = entries[index];
  if (
    before !== undefined &&
    after !== undefined &&
    before.kind === "item" &&
    after.kind === "item" &&
    before.parentId !== null &&
    before.parentId === after.parentId
  ) {
    return before.parentId;
  }
  return null;
}

/**
 * The members the delivered parents define: every item entry takes the head
 * part that owns it (by item id), else none, and the head's childless parts are
 * blocks again, each after the nearest earlier head item member.
 */
function membersFromHead(entries: Entry[], head: NativeExamDocument): ExamWorkspaceMember[] {
  const parentIdByItem = new Map<string, string>();
  for (const parent of head.parents) {
    for (const itemId of parent.item_ids) {
      parentIdByItem.set(itemId, parent.parent_id);
    }
  }
  const members: ExamWorkspaceMember[] = itemEntries(entries).map((entry) => {
    entry.parentId = parentIdByItem.get(entry.item.item_id) ?? null;
    return { kind: "item", item: entry.item, parentId: entry.parentId };
  });
  const headMembers = examWorkspaceMembers(head);
  headMembers.forEach((member, position) => {
    if (member.kind !== "block") {
      return;
    }
    let earlierItemId: string | null = null;
    for (let at = position - 1; at >= 0; at -= 1) {
      const earlier = headMembers[at]!;
      if (earlier.kind === "item") {
        earlierItemId = earlier.item.item_id;
        break;
      }
    }
    const after =
      earlierItemId === null
        ? -1
        : members.findIndex(
            (entry) => entry.kind === "item" && entry.item.item_id === earlierItemId,
          );
    members.splice(after + 1, 0, { kind: "block", parentId: member.parentId });
  });
  return members;
}

export function mergeConversionRevision({
  base,
  baseUnits,
  head,
  headUnits,
  local,
}: MergeArgs): NativeExamDocument {
  const baseUnitById = new Map(baseUnits.map((unit) => [unit.unit_id, unit]));
  const unitByItemId = new Map(
    baseUnits.flatMap((unit) =>
      unit.item_ids.map((itemId) => [itemId, unit.unit_id] as const),
    ),
  );
  const onlyIds = (items: NativeExamItem[], ids: Set<string>) =>
    items.filter((item) => ids.has(item.item_id));

  const replaced = new Map<string, NativeExamItem[]>();
  const inserted: { at: number; items: NativeExamItem[]; unit: string }[] = [];
  headUnits.forEach((headUnit, at) => {
    const baseUnit = baseUnitById.get(headUnit.unit_id);
    const baseIds = new Set(baseUnit?.item_ids ?? []);
    const baseItems = onlyIds(base.items, baseIds);
    const headItems = onlyIds(head.items, new Set(headUnit.item_ids));
    const localItems = onlyIds(local.items, baseIds);
    const placeholder = baseUnit?.state === "converting";
    if (
      !placeholder &&
      (sameItems(baseItems, headItems) || !sameItems(localItems, baseItems))
    ) {
      return;
    }
    if (localItems.length === 0) {
      inserted.push({ at, items: headItems, unit: headUnit.unit_id });
    } else {
      replaced.set(headUnit.unit_id, headItems);
    }
  });

  const unitItemIds = new Set(headUnits.flatMap((unit) => unit.item_ids));
  const baseById = new Map(base.items.map((item) => [item.item_id, item]));
  const headById = new Map(head.items.map((item) => [item.item_id, item]));
  const entries: Entry[] = [];
  const placed = new Set<string>();
  for (const member of examWorkspaceMembers(local)) {
    if (member.kind === "block") {
      entries.push({ kind: "block", parentId: member.parentId });
      continue;
    }
    const { item, parentId } = member;
    const unit = unitByItemId.get(item.item_id) ?? null;
    const headItems = unit === null ? undefined : replaced.get(unit);
    const baseItem = baseById.get(item.item_id);
    const headItem = headById.get(item.item_id);
    if (unit === null && baseItem && headItem && !unitItemIds.has(item.item_id)) {
      const chosen = pick(baseItem, item, headItem);
      entries.push({ kind: "item", fromHead: chosen.fromHead, item: chosen.value, unit, parentId });
    } else if (unit === null || headItems === undefined) {
      entries.push({ kind: "item", fromHead: false, item, unit, parentId });
    } else if (!placed.has(unit)) {
      placed.add(unit);
      entries.push(
        ...headItems.map((entryItem) => ({
          kind: "item" as const,
          fromHead: true,
          item: entryItem,
          unit,
          parentId,
        })),
      );
    }
  }
  for (const { at, items, unit } of inserted) {
    const index = insertionIndex(entries, headUnits, at);
    const parentId = neighbourParentId(entries, index);
    entries.splice(
      index,
      0,
      ...items.map((entryItem) => ({
        kind: "item" as const,
        fromHead: true,
        item: entryItem,
        unit,
        parentId,
      })),
    );
  }

  // Items a later save added since the base belong to no unit; keep them after
  // the head item they follow.
  head.items.forEach((added, at) => {
    if (unitItemIds.has(added.item_id) || baseById.has(added.item_id)) {
      return;
    }
    const previous = head.items[at - 1]?.item_id;
    const index =
      entries.findIndex((entry) => entry.kind === "item" && entry.item.item_id === previous) + 1;
    const parentId = neighbourParentId(entries, index);
    entries.splice(index, 0, { kind: "item", fromHead: true, item: added, unit: null, parentId });
  });

  const headIds = new Set(
    itemEntries(entries)
      .filter((entry) => entry.fromHead)
      .map((entry) => entry.item.item_id),
  );
  for (const entry of itemEntries(entries)) {
    if (!entry.fromHead && headIds.has(entry.item.item_id)) {
      const fresh = nextItemId(itemEntries(entries).map((other) => other.item.item_id));
      entry.item = { ...entry.item, item_id: fresh };
    }
  }

  const title = pick(base.title, local.title, head.title).value;
  const header = pick(base.header, local.header, head.header).value;
  const instructions = pick(
    base.instructions,
    local.instructions,
    head.instructions,
  ).value;
  const parentsPick = pick(base.parents, local.parents, head.parents);
  const sourceParents = parentsPick.fromHead ? head.parents : local.parents;
  const members: ExamWorkspaceMember[] = parentsPick.fromHead
    ? membersFromHead(entries, head)
    : entries.map((entry) =>
        entry.kind === "block"
          ? { kind: "block", parentId: entry.parentId }
          : { kind: "item", item: entry.item, parentId: entry.parentId },
      );

  return withMembers(
    {
      ...local,
      document_id: head.document_id,
      header,
      instructions,
      revision: head.revision,
      title,
      items: [],
    },
    members,
    sourceParents,
  );
}
