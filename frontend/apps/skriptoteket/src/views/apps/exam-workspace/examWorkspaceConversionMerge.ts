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
 *   otherwise the teacher's version stays. The title, the instructions and
 *   the parents follow the converted-unit rule; items the teacher added
 *   belong to no unit and keep their place.
 *
 * Relationships:
 *   - Client twin of `merge_conversion` in
 *     `application/curated_apps/handlers/exam_workspace_conversion_merge.py`,
 *     which applies the same rule on the server against the saved head.
 *   - Pure function consumed by `useExamWorkspaceConversion` and
 *     `useExamWorkspaceDocument`.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type {
  ExamWorkspaceConversionUnit,
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";

type MergeArgs = {
  base: NativeExamDocument;
  /** The units of `base`, with the state each had in it. */
  baseUnits: ExamWorkspaceConversionUnit[];
  local: NativeExamDocument;
  head: NativeExamDocument;
  headUnits: ExamWorkspaceConversionUnit[];
};

type Entry = { fromHead: boolean; item: NativeExamItem; unit: string | null };

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
function sameValue(a: unknown, b: unknown): boolean {
  return JSON.stringify(sortKeys(a)) === JSON.stringify(sortKeys(b));
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

function insertionIndex(
  entries: Entry[],
  headUnits: ExamWorkspaceConversionUnit[],
  at: number,
) {
  for (let index = at - 1; index >= 0; index -= 1) {
    const unitId = headUnits[index]!.unit_id;
    const last = entries.map((entry) => entry.unit).lastIndexOf(unitId);
    if (last >= 0) {
      return last + 1;
    }
  }
  return 0;
}

export function mergeConversionRevision({
  base,
  baseUnits,
  head,
  headUnits,
  local,
}: MergeArgs): { document: NativeExamDocument; teacherEditsKept: boolean } {
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

  const entries: Entry[] = [];
  const placed = new Set<string>();
  for (const item of local.items) {
    const unit = unitByItemId.get(item.item_id) ?? null;
    const headItems = unit === null ? undefined : replaced.get(unit);
    if (unit === null || headItems === undefined) {
      entries.push({ fromHead: false, item, unit });
    } else if (!placed.has(unit)) {
      placed.add(unit);
      entries.push(
        ...headItems.map((headItem) => ({
          fromHead: true,
          item: headItem,
          unit,
        })),
      );
    }
  }
  for (const { at, items, unit } of inserted) {
    const index = insertionIndex(entries, headUnits, at);
    entries.splice(
      index,
      0,
      ...items.map((item) => ({ fromHead: true, item, unit })),
    );
  }

  const headIds = new Set(
    entries.filter((entry) => entry.fromHead).map((e) => e.item.item_id),
  );
  const renames = new Map<string, string>();
  for (const entry of entries) {
    if (!entry.fromHead && headIds.has(entry.item.item_id)) {
      const fresh = nextItemId(entries.map((other) => other.item.item_id));
      renames.set(entry.item.item_id, fresh);
      entry.item = { ...entry.item, item_id: fresh };
    }
  }
  const items = entries.map((entry, index) => ({
    ...entry.item,
    sequence: index + 1,
  }));

  const title = pick(base.title, local.title, head.title).value;
  const instructions = pick(
    base.instructions,
    local.instructions,
    head.instructions,
  ).value;
  const parentsPick = pick(base.parents, local.parents, head.parents);
  const present = new Set(items.map((item) => item.item_id));
  const parents = parentsPick.value
    .map((parent): NativeExamParent => {
      const itemIds = parentsPick.fromHead
        ? parent.item_ids
        : parent.item_ids.map((itemId) => renames.get(itemId) ?? itemId);
      return {
        ...parent,
        item_ids: itemIds.filter((itemId) => present.has(itemId)),
      };
    })
    .filter((parent) => parent.item_ids.length > 0);

  const document: NativeExamDocument = {
    ...local,
    document_id: head.document_id,
    instructions,
    items,
    parents,
    revision: head.revision,
    title,
  };
  return { document, teacherEditsKept: !sameValue(document, head) };
}
