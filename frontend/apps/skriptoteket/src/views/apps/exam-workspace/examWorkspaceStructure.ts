/**
 * Exam workspace structure transitions.
 *
 * Domain purpose:
 *   The exam's top-level units are standalone questions and whole
 *   instructions with their deluppgifter (parents). A part has its own stored
 *   place: the number of questions before it in document order, and a part
 *   with no questions is an instruction block that keeps that place. A new
 *   question lands after the selected unit, never inside a parent, and a
 *   deleted standalone question leaves contiguous sequences 1..n behind.
 *   Names the content a Byt frågetyp dropped in the teacher's words
 *   (TASK-SKRIPT-39-06-05).
 *
 *   The client twin of the server's one ordering owner (`native_exam_outline`,
 *   R1): `examWorkspaceMembers` reads the units as a flat member list, and
 *   `withMembers` is the one grouping rule that turns members back into units
 *   with item sequences and part places -- the client twins of
 *   `outline_members` and `outline_from_members`. A conversion merge hands a
 *   member list to `withMembers` instead of computing a part place itself, so
 *   no consumer reconstructs the ordering rule.
 *
 * Relationships:
 *   - Pure functions used by `useExamWorkspaceStructure`; parent and
 *     change-type commands themselves run on the server.
 *   - `examWorkspaceConversionMerge` consumes `examWorkspaceMembers` and
 *     `withMembers`.
 */

import type {
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { examWorkspaceTypeLabel } from "./examWorkspaceRows";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";

export type ExamWorkspaceUnit =
  | { kind: "item"; itemId: string }
  | { kind: "parent"; parentId: string; itemIds: string[] };

/**
 * One token of a flat member list in document order: an item with the part it
 * belongs to (`null` when standalone), or a block for a childless part.
 */
export type ExamWorkspaceMember =
  | { kind: "item"; item: NativeExamItem; parentId: string | null }
  | { kind: "block"; parentId: string };

/**
 * The top-level units in document order: a part sits at its stored place (the
 * questions before it), a part with no questions is an instruction block, and
 * the standalone questions fill the places no part claims.
 */
export function examWorkspaceUnits(document: NativeExamDocument): ExamWorkspaceUnit[] {
  const parentsByPlace = new Map<number, NativeExamDocument["parents"]>();
  for (const parent of document.parents) {
    const at = parentsByPlace.get(parent.place);
    if (at === undefined) {
      parentsByPlace.set(parent.place, [parent]);
    } else {
      at.push(parent);
    }
  }
  const inPart = new Set(document.parents.flatMap((parent) => [...parent.item_ids]));
  const units: ExamWorkspaceUnit[] = [];
  const emitParts = (place: number) => {
    for (const parent of parentsByPlace.get(place) ?? []) {
      units.push({ kind: "parent", parentId: parent.parent_id, itemIds: [...parent.item_ids] });
    }
  };
  document.items.forEach((item, place) => {
    emitParts(place);
    if (!inPart.has(item.item_id)) {
      units.push({ kind: "item", itemId: item.item_id });
    }
  });
  emitParts(document.items.length);
  return units;
}

/**
 * The one writer: items in unit order, renumbered 1..n, and the parts reordered
 * to unit order with their stored place (the items before them). Content tags
 * and assets are left untouched here.
 */
export function withUnits(
  document: NativeExamDocument,
  units: ExamWorkspaceUnit[],
  pool: NativeExamItem[] = document.items,
): NativeExamDocument {
  const itemById = new Map(pool.map((item) => [item.item_id, item]));
  const items: NativeExamItem[] = [];
  const parents: NativeExamDocument["parents"] = [];
  for (const unit of units) {
    if (unit.kind === "item") {
      const item = itemById.get(unit.itemId);
      if (item !== undefined) {
        items.push(item);
      }
      continue;
    }
    const parent = document.parents.find((entry) => entry.parent_id === unit.parentId);
    if (parent === undefined) {
      continue;
    }
    const itemIds = unit.itemIds.filter((itemId) => itemById.has(itemId));
    parents.push({ ...parent, item_ids: itemIds, place: items.length });
    for (const itemId of itemIds) {
      items.push(itemById.get(itemId)!);
    }
  }
  return {
    ...document,
    items: items.map((item, index) =>
      item.sequence === index + 1 ? item : { ...item, sequence: index + 1 },
    ),
    parents,
  };
}

/**
 * The document's member list in document order: one item token per item with
 * the part it belongs to (`null` when standalone), and one block token per
 * childless part. The client twin of `outline_members`.
 */
export function examWorkspaceMembers(document: NativeExamDocument): ExamWorkspaceMember[] {
  const itemById = new Map(document.items.map((item) => [item.item_id, item]));
  const members: ExamWorkspaceMember[] = [];
  for (const unit of examWorkspaceUnits(document)) {
    if (unit.kind === "item") {
      const item = itemById.get(unit.itemId);
      if (item !== undefined) {
        members.push({ kind: "item", item, parentId: null });
      }
      continue;
    }
    if (unit.itemIds.length === 0) {
      members.push({ kind: "block", parentId: unit.parentId });
      continue;
    }
    for (const itemId of unit.itemIds) {
      const item = itemById.get(itemId);
      if (item !== undefined) {
        members.push({ kind: "item", item, parentId: unit.parentId });
      }
    }
  }
  return members;
}

/** The next free `parent_NNN` id: one above the highest numbered id in use. */
export function nextParentId(parentIds: string[]): string {
  const used = new Set(parentIds);
  let highest = 0;
  for (const parentId of parentIds) {
    const match = /^parent_(\d+)$/.exec(parentId);
    if (match) {
      highest = Math.max(highest, Number(match[1]));
    }
  }
  let candidate = highest + 1;
  while (used.has(`parent_${String(candidate).padStart(3, "0")}`)) {
    candidate += 1;
  }
  return `parent_${String(candidate).padStart(3, "0")}`;
}

/**
 * The one grouping rule for a member list: consecutive item members of one part
 * become one part entry, a block member becomes a childless part in place, and a
 * part whose members reappear after an interruption is split into runs; each
 * later run is a copy of the part with a fresh parent id and the same
 * instruction, so no child loses its part. The client twin of
 * `outline_from_members`.
 */
export function withMembers(
  document: NativeExamDocument,
  members: ExamWorkspaceMember[],
  parents: NativeExamParent[],
): NativeExamDocument {
  const parentById = new Map(parents.map((parent) => [parent.parent_id, parent]));
  const usedParentIds = parents.map((parent) => parent.parent_id);
  const runCopies: NativeExamParent[] = [];
  const started = new Set<string>();
  const units: ExamWorkspaceUnit[] = [];
  let previous: ExamWorkspaceMember | null = null;
  for (const member of members) {
    if (member.kind === "block") {
      units.push({ kind: "parent", parentId: member.parentId, itemIds: [] });
      previous = member;
      continue;
    }
    if (member.parentId === null) {
      units.push({ kind: "item", itemId: member.item.item_id });
      previous = member;
      continue;
    }
    const continues =
      previous !== null && previous.kind === "item" && previous.parentId === member.parentId;
    let parentId = member.parentId;
    if (!continues) {
      if (started.has(member.parentId)) {
        parentId = nextParentId(usedParentIds);
        usedParentIds.push(parentId);
        const source = parentById.get(member.parentId);
        if (source !== undefined) {
          const copy = { ...source, parent_id: parentId };
          runCopies.push(copy);
          parentById.set(parentId, copy);
        }
      }
      started.add(member.parentId);
      units.push({ kind: "parent", parentId, itemIds: [] });
    }
    const running = units[units.length - 1]!;
    if (running.kind === "parent") {
      running.itemIds.push(member.item.item_id);
    }
    previous = member;
  }
  return withUnits(
    { ...document, parents: [...parents, ...runCopies] },
    units,
    members.flatMap((member) => (member.kind === "item" ? [member.item] : [])),
  );
}

/** The index of the unit holding the selection (an item, a child or a parent), or -1. */
export function examWorkspaceUnitIndex(
  units: ExamWorkspaceUnit[],
  selection: { itemId?: string | null; parentId?: string | null },
): number {
  return units.findIndex((unit) =>
    unit.kind === "item"
      ? unit.itemId === selection.itemId
      : unit.parentId === selection.parentId ||
        (selection.itemId != null && unit.itemIds.includes(selection.itemId)),
  );
}

/** Insert a standalone question after unit `afterUnit` (-1 puts it first). */
export function withItemAfterUnit(
  document: NativeExamDocument,
  item: NativeExamItem,
  afterUnit: number,
): NativeExamDocument {
  const units = examWorkspaceUnits(document);
  const next = [...units];
  next.splice(Math.min(afterUnit, units.length - 1) + 1, 0, { kind: "item", itemId: item.item_id });
  return withUnits(document, next, [...document.items, item]);
}

function bodyAssetIds(body: NativeExamBodyParagraph[]): string[] {
  return body.flatMap((paragraph) =>
    paragraph.segments.flatMap((segment) => (segment.kind === "asset" ? [segment.asset_id] : [])),
  );
}

/** Pictures an item's body or its stored retry source references (mirrors the server's `_rebuild`). */
function itemAssetIds(item: NativeExamItem): string[] {
  const source = item.retry_source;
  const records = source ? [...source.chunks, ...source.key_chunks, ...source.context_chunks] : [];
  return [...bodyAssetIds(item.body), ...records.flatMap((record) => record.images.map((image) => image.asset_id))];
}

/** Whether removing the question would leave the exam without one. */
export function examWorkspaceIsOnlyQuestion(document: NativeExamDocument, itemId: string): boolean {
  return document.items.every((item) => item.item_id === itemId);
}

/**
 * How many times each picture is still cited (an item's body or retry
 * source, the exam instruction, a part instruction): the one walk
 * `withReferencedAssetsOnly` prunes by, shared with the new-pictures
 * registry so a placed picture is declared by the same rule, and with the
 * picture intake so a replacement credits the picture it removes.
 */
export function examWorkspaceAssetReferenceCounts(document: NativeExamDocument): Map<string, number> {
  const counts = new Map<string, number>();
  for (const assetId of [
    ...document.items.flatMap(itemAssetIds),
    ...bodyAssetIds(document.instructions),
    ...document.parents.flatMap((parent) => bodyAssetIds(parent.instruction)),
  ]) {
    counts.set(assetId, (counts.get(assetId) ?? 0) + 1);
  }
  return counts;
}

export function examWorkspaceReferencedAssetIds(document: NativeExamDocument): Set<string> {
  return new Set(examWorkspaceAssetReferenceCounts(document).keys());
}

/**
 * Keep only the pictures something still references (an item's body or retry
 * source, the exam instruction, a part instruction), as the server's rebuild
 * does; a picture an edit removed takes its asset record with it.
 */
export function withReferencedAssetsOnly(document: NativeExamDocument): NativeExamDocument {
  const referenced = examWorkspaceReferencedAssetIds(document);
  const assets = document.assets.filter((asset) => referenced.has(asset.asset_id));
  return assets.length === document.assets.length ? document : { ...document, assets };
}

/**
 * Remove a standalone question; a child leaves through its parent's server command.
 * Content tags stop citing it and only still-referenced pictures stay, as on the server.
 */
export function withoutStandaloneItem(document: NativeExamDocument, itemId: string): NativeExamDocument {
  if (document.parents.some((parent) => parent.item_ids.includes(itemId))) {
    return document;
  }
  const units = examWorkspaceUnits(document).filter(
    (unit) => unit.kind !== "item" || unit.itemId !== itemId,
  );
  const stripped = withUnits(document, units);
  const surviving = new Set(stripped.items.map((item) => item.item_id));
  return withReferencedAssetsOnly({
    ...stripped,
    header: {
      ...stripped.header,
      tags: stripped.header.tags.map((tag) => ({
        ...tag,
        question_ids: tag.question_ids.filter((id) => surviving.has(id)),
      })),
    },
  });
}

/** The item to select after `itemId` leaves: the next one, else the previous one. */
export function examWorkspaceNeighbourId(document: NativeExamDocument, itemId: string): string | null {
  const index = document.items.findIndex((item) => item.item_id === itemId);
  return document.items[index + 1]?.item_id ?? document.items[index - 1]?.item_id ?? null;
}

/** "a", "a och b", "a, b och c". */
export function swedishList(parts: string[]): string {
  if (parts.length < 2) {
    return parts.join("");
  }
  return `${parts.slice(0, -1).join(", ")} och ${parts[parts.length - 1]}`;
}

const DROPPED_CONTENT_COPY: Record<string, string> = {
  accepted_values: "luckornas godkända svar",
  ai_suggestion: "AI:s facitförslag",
  choices: "svarsalternativen",
  correct_choice_ids: "facit",
  correct_option_id: "rullistornas rätta svar",
  criteria: "bedömningskriterierna",
  gaps: "luckorna",
  match_left: "raderna",
  match_pairs: "kryssen",
  match_right: "kategorierna",
  options: "rullistornas alternativ",
  tick_points: "poäng per kryss",
};

/** The inline notice after Byt frågetyp: the new type, and what the change removed. */
export function examWorkspaceChangeTypeNotice(
  kind: NativeExamItem["kind"],
  droppedContent: string[],
): string {
  const dropped = droppedContent.map((name) => DROPPED_CONTENT_COPY[name] ?? name);
  const head = `Bytte till ${examWorkspaceTypeLabel(kind)}.`;
  return dropped.length ? `${head} Borttaget: ${swedishList(dropped)}.` : head;
}

/** The menu entries for a new question, in the prototype's order. */
export const EXAM_WORKSPACE_NEW_ITEM_KINDS: { kind: TeacherItemKind; label: string }[] = [
  { kind: "free_text", label: "Fritext" },
  { kind: "short_answer", label: "Kort svar" },
  { kind: "single_choice", label: "Flerval: ett val" },
  { kind: "multiple_response", label: "Flerval: flera val" },
  { kind: "gap_fill", label: "Lucktext" },
  { kind: "inline_choice", label: "Lucktext med rullista" },
  { kind: "matching", label: "Kategorisera" },
  { kind: "ordering", label: "Ordna" },
];
