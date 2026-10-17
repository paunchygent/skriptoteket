/**
 * Exam workspace structure transitions.
 *
 * Domain purpose:
 *   The exam's top-level units are standalone questions and whole
 *   instructions with their deluppgifter (parents). A new question lands
 *   after the selected unit, never inside a parent, and a deleted standalone
 *   question leaves contiguous sequences 1..n behind. Names the content a
 *   Byt frågetyp dropped in the teacher's words (TASK-SKRIPT-39-06-05).
 *
 * Relationships:
 *   - Pure functions used by `useExamWorkspaceStructure`; parent and
 *     change-type commands themselves run on the server.
 */

import type { NativeExamBodyParagraph, NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceTypeLabel } from "./examWorkspaceRows";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";

export type ExamWorkspaceUnit =
  | { kind: "item"; itemId: string }
  | { kind: "parent"; parentId: string; itemIds: string[] };

/** The top-level units in document order. */
export function examWorkspaceUnits(document: NativeExamDocument): ExamWorkspaceUnit[] {
  const parentOf = new Map<string, NativeExamDocument["parents"][number]>();
  for (const parent of document.parents) {
    for (const itemId of parent.item_ids) {
      parentOf.set(itemId, parent);
    }
  }
  const units: ExamWorkspaceUnit[] = [];
  for (const item of document.items) {
    const parent = parentOf.get(item.item_id);
    if (!parent) {
      units.push({ kind: "item", itemId: item.item_id });
    } else if (parent.item_ids[0] === item.item_id) {
      units.push({ kind: "parent", parentId: parent.parent_id, itemIds: [...parent.item_ids] });
    }
  }
  return units;
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

function resequenced(items: NativeExamItem[]): NativeExamItem[] {
  return items.map((item, index) => (item.sequence === index + 1 ? item : { ...item, sequence: index + 1 }));
}

/** Insert a standalone question after unit `afterUnit` (-1 puts it first). */
export function withItemAfterUnit(
  document: NativeExamDocument,
  item: NativeExamItem,
  afterUnit: number,
): NativeExamDocument {
  const units = examWorkspaceUnits(document);
  const anchor = units[Math.min(afterUnit, units.length - 1)];
  const lastId = anchor === undefined || afterUnit < 0
    ? null
    : anchor.kind === "item"
      ? anchor.itemId
      : anchor.itemIds[anchor.itemIds.length - 1];
  const at = lastId === null ? 0 : document.items.findIndex((entry) => entry.item_id === lastId) + 1;
  const items = [...document.items.slice(0, at), item, ...document.items.slice(at)];
  return { ...document, items: resequenced(items) };
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
 * Remove a standalone question; a child leaves through its parent's server command.
 * Content tags stop citing it and only still-referenced pictures stay, as on the server.
 */
export function withoutStandaloneItem(document: NativeExamDocument, itemId: string): NativeExamDocument {
  if (document.parents.some((parent) => parent.item_ids.includes(itemId))) {
    return document;
  }
  const items = resequenced(document.items.filter((item) => item.item_id !== itemId));
  const surviving = new Set(items.map((item) => item.item_id));
  const referenced = new Set<string>([
    ...items.flatMap(itemAssetIds),
    ...bodyAssetIds(document.instructions),
    ...document.parents.flatMap((parent) => bodyAssetIds(parent.instruction)),
  ]);
  return {
    ...document,
    assets: document.assets.filter((asset) => referenced.has(asset.asset_id)),
    header: {
      ...document.header,
      tags: document.header.tags.map((tag) => ({
        ...tag,
        question_ids: tag.question_ids.filter((id) => surviving.has(id)),
      })),
    },
    items,
  };
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
];
