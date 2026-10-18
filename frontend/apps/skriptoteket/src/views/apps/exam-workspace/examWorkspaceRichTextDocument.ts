/**
 * Exam workspace rich-text document mapping.
 *
 * Domain purpose:
 *   The two-way mapping between a stored native body (paragraphs of text,
 *   gap and picture segments) and the TipTap document an exam text editor
 *   holds. The stored body is the only persisted form; this module is the
 *   whole translation, so nothing else reads TipTap node names.
 *
 *   Into the editor: a paragraph with a heading level becomes a heading, a
 *   `"\n"` inside a text segment becomes a hard break carrying that segment's
 *   marks, and an empty body opens as the one empty paragraph the schema
 *   needs. Out of the editor: adjacent text with equal marks merges into one
 *   segment, a hard break joins its text as `"\n"`, marks follow the stored
 *   order, and a document without any text, gap or picture is the empty body
 *   (TASK-SKRIPT-40-04-06 D3, D4). Otherwise every paragraph is kept, an
 *   emptied one as a paragraph without segments.
 *
 * Relationships:
 *   - Reads node names from `examWorkspaceRichTextSchema`.
 *   - Used by `ExamWorkspaceRichTextEditor`.
 */

import type { JSONContent } from "@tiptap/core";

import type { NativeExamBodyParagraph, NativeExamBodySegment } from "../../../api/examWorkspace";
import { BODY_MARKS, type BodyMark } from "./examWorkspaceBodyMarks";
import { EXAM_GAP_NODE, EXAM_PICTURE_NODE } from "./examWorkspaceRichTextSchema";

type TextSegment = Extract<NativeExamBodySegment, { kind: "text" }>;

function editorMarks(marks: readonly BodyMark[]): JSONContent["marks"] {
  return BODY_MARKS.filter((mark) => marks.includes(mark)).map((type) => ({ type }));
}

function withMarks(node: JSONContent, marks: readonly BodyMark[]): JSONContent {
  return marks.length > 0 ? { ...node, marks: editorMarks(marks) } : node;
}

function editorInline(segments: readonly NativeExamBodySegment[]): JSONContent[] {
  const nodes: JSONContent[] = [];
  for (const segment of segments) {
    if (segment.kind === "gap") {
      nodes.push({ type: EXAM_GAP_NODE, attrs: { gapId: segment.gap_id } });
      continue;
    }
    if (segment.kind === "asset") {
      nodes.push({ type: EXAM_PICTURE_NODE, attrs: { assetId: segment.asset_id } });
      continue;
    }
    segment.text.split("\n").forEach((line, lineIndex) => {
      if (lineIndex > 0) {
        nodes.push(withMarks({ type: "hardBreak" }, segment.marks));
      }
      // ProseMirror has no empty text node; an empty line carries nothing to render.
      if (line.length > 0) {
        nodes.push(withMarks({ type: "text", text: line }, segment.marks));
      }
    });
  }
  return nodes;
}

function editorBlock(paragraph: NativeExamBodyParagraph): JSONContent {
  const content = editorInline(paragraph.segments);
  const node: JSONContent =
    paragraph.heading_level === null
      ? { type: "paragraph" }
      : { type: "heading", attrs: { level: paragraph.heading_level } };
  return content.length > 0 ? { ...node, content } : node;
}

/** The stored body as the TipTap document an editor opens. */
export function editorContentFrom(body: readonly NativeExamBodyParagraph[]): JSONContent {
  return {
    type: "doc",
    content: body.length > 0 ? body.map(editorBlock) : [{ type: "paragraph" }],
  };
}

function bodyMarks(node: JSONContent): BodyMark[] {
  const names = new Set((node.marks ?? []).map((mark) => mark.type));
  return BODY_MARKS.filter((mark) => names.has(mark));
}

function sameMarks(left: readonly BodyMark[], right: readonly BodyMark[]): boolean {
  return left.length === right.length && left.every((mark, index) => mark === right[index]);
}

function bodySegments(content: readonly JSONContent[] | undefined): NativeExamBodySegment[] {
  const segments: NativeExamBodySegment[] = [];
  const appendText = (text: string, marks: BodyMark[]): void => {
    const last = segments.at(-1);
    if (last?.kind === "text" && sameMarks(last.marks, marks)) {
      segments[segments.length - 1] = { ...last, text: last.text + text } satisfies TextSegment;
      return;
    }
    segments.push({ kind: "text", text, marks });
  };
  for (const node of content ?? []) {
    if (node.type === EXAM_GAP_NODE) {
      segments.push({ kind: "gap", gap_id: String(node.attrs?.gapId) });
    } else if (node.type === EXAM_PICTURE_NODE) {
      segments.push({ kind: "asset", asset_id: String(node.attrs?.assetId) });
    } else if (node.type === "hardBreak") {
      appendText("\n", bodyMarks(node));
    } else if (node.type === "text" && node.text) {
      appendText(node.text, bodyMarks(node));
    }
  }
  return segments;
}

function headingLevel(node: JSONContent): NativeExamBodyParagraph["heading_level"] {
  if (node.type !== "heading") {
    return null;
  }
  const level = Number(node.attrs?.level);
  return level === 1 || level === 2 || level === 3 ? level : null;
}

/** The editor's TipTap document as the stored body; a document with no content is the empty body. */
export function bodyFromEditor(content: JSONContent): NativeExamBodyParagraph[] {
  const body = (content.content ?? [])
    .filter((node) => node.type === "paragraph" || node.type === "heading")
    .map((node) => ({ heading_level: headingLevel(node), segments: bodySegments(node.content) }));
  return body.some((paragraph) => paragraph.segments.length > 0) ? body : [];
}

/** Gap ids in body order. */
export function placedGapIds(body: readonly NativeExamBodyParagraph[]): string[] {
  return body.flatMap((paragraph) =>
    paragraph.segments.flatMap((segment) => (segment.kind === "gap" ? [segment.gap_id] : [])),
  );
}

/** Picture ids in body order. */
export function placedAssetIds(body: readonly NativeExamBodyParagraph[]): string[] {
  return body.flatMap((paragraph) =>
    paragraph.segments.flatMap((segment) => (segment.kind === "asset" ? [segment.asset_id] : [])),
  );
}

/** A body that prints nothing: no gap, no picture and no visible character. */
export function isEmptyBody(body: readonly NativeExamBodyParagraph[]): boolean {
  return body.every((paragraph) =>
    paragraph.segments.every((segment) => segment.kind === "text" && segment.text.trim() === ""),
  );
}
