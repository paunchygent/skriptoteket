/**
 * Exam workspace column sizes browser storage.
 *
 * Domain purpose:
 *   Remember the user's column widths and list-collapsed state per browser,
 *   shared by the guest and signed-in workspaces. Storage is a convenience:
 *   every read and write is guarded, so the workspace renders at its CSS
 *   defaults when the key is missing, the JSON is invalid, the schema rejects
 *   the value, or storage throws. A stored width is never rewritten for a
 *   smaller window; CSS clips it there and it returns when the window grows.
 *
 * Relationships:
 *   - Read once on setup and written on every change by
 *     `useExamWorkspaceColumnSizes`; no other reader.
 *   - Validated with zod like `api/tutorialClips.ts`; guarded like
 *     `components/help/tutorial/useTutorialSeenSections.ts`.
 */

import { z } from "zod";

export const EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY = "skriptoteket.exam-workspace.columns";

const examWorkspaceColumnSizesSchema = z.strictObject({
  list: z.number().positive().optional(),
  drawer: z.number().positive().optional(),
  preview: z.number().positive().optional(),
  listCollapsed: z.boolean().optional(),
});

export type ExamWorkspaceColumnSizes = z.infer<typeof examWorkspaceColumnSizesSchema>;

/** The remembered widths, or {} when nothing usable is stored. */
export function readExamWorkspaceColumnSizes(): ExamWorkspaceColumnSizes {
  try {
    const raw = localStorage.getItem(EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed: unknown = JSON.parse(raw);
    const result = examWorkspaceColumnSizesSchema.safeParse(parsed);
    return result.success ? result.data : {};
  } catch {
    return {};
  }
}

/** Persist the widths; an empty value removes the key instead. */
export function writeExamWorkspaceColumnSizes(value: ExamWorkspaceColumnSizes): void {
  try {
    if (Object.keys(value).length === 0) {
      localStorage.removeItem(EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY);
      return;
    }
    localStorage.setItem(EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY, JSON.stringify(value));
  } catch {
    // Storage can be full or blocked; the in-memory sizes still hold this visit.
  }
}
