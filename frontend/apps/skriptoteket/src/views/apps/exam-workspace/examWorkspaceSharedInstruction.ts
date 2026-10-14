/**
 * Shared instruction presentation.
 *
 * Domain purpose:
 *   A shared instruction — a document's exam-wide instructions or a parent's
 *   shared stem over consecutive child questions — is a native body paragraph:
 *   text and picture segments in order, with response gaps forbidden by the
 *   document contract. The teacher list shows it read-only, so the same
 *   wording and diagrams the student will get are visible in the editor.
 *
 * Relationships:
 *   - Reads shapes from `api/examWorkspace.ts`; a picture part carries the
 *     protected asset URL the document composable already builds, never a
 *     plain app-host URL.
 *   - Resolved into blocks by `examWorkspaceParents` and rendered by
 *     `ExamWorkspaceSharedInstruction`.
 */

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";

/**
 * Visible marker for a response gap. The document contract rejects gaps in
 * shared instructions, so this keeps an impossible gap from silently
 * disappearing instead of rendering a question-time answer atom.
 */
export const SHARED_INSTRUCTION_GAP_TEXT = "[___]";

export type ExamWorkspaceSharedPart =
  | { kind: "text"; text: string }
  | { kind: "asset"; assetId: string; url: string | null };

export type ExamWorkspaceSharedParagraph = { parts: ExamWorkspaceSharedPart[] };

/**
 * Resolve one shared paragraph's segments in order into renderer parts.
 *
 * A picture part carries the protected URL when the document's asset map has
 * one and `null` otherwise, so the renderer shows the real diagram or the
 * "Bild" placeholder without inventing a URL.
 */
export function examWorkspaceSharedParts(
  paragraph: NativeExamBodyParagraph,
  assetUrls: Record<string, string> = {},
): ExamWorkspaceSharedPart[] {
  return paragraph.segments.map((segment) => {
    if (segment.kind === "text") {
      return { kind: "text", text: segment.text };
    }
    if (segment.kind === "asset") {
      return {
        assetId: segment.asset_id,
        kind: "asset",
        url: assetUrls[segment.asset_id] ?? null,
      };
    }
    return { kind: "text", text: SHARED_INSTRUCTION_GAP_TEXT };
  });
}

/** Resolve every shared paragraph of an instruction into ordered renderer parts. */
export function examWorkspaceSharedParagraphs(
  paragraphs: NativeExamBodyParagraph[],
  assetUrls: Record<string, string> = {},
): ExamWorkspaceSharedParagraph[] {
  return paragraphs.map((paragraph) => ({
    parts: examWorkspaceSharedParts(paragraph, assetUrls),
  }));
}
