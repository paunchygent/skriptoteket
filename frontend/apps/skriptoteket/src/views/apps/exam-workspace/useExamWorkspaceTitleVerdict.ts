/**
 * Exam workspace title verdict.
 *
 * Domain purpose:
 *   Remember which exam title the server's export gate judged to have no
 *   letter or digit, so the workspace shows the title blocker before any
 *   click without a title rule of its own. Every server response that carries
 *   the gate's blockers for a document (open, Spara, autosave, a refused
 *   export) replaces the verdict; a title the teacher has changed since is
 *   unjudged and shows no blocker until the next response judges it.
 *
 * Relationships:
 *   - Fed by `useExamWorkspaceDocument` and `useExamWorkspaceHistory` from
 *     their responses and by `useExamWorkspaceExports` from a refusal.
 *   - Read by `examWorkspaceBlockers` through `ExamWorkspaceView`.
 */

import { computed, ref } from "vue";
import type { Ref } from "vue";

import type { ExamWorkspaceExportBlocker, NativeExamDocument } from "../../../api/examWorkspace";

export type ExamWorkspaceTitleVerdict = (title: string, blockers: readonly ExamWorkspaceExportBlocker[]) => void;

export function useExamWorkspaceTitleVerdict(workspaceDocument: Ref<NativeExamDocument | null>) {
  /** The title the server last judged without text; null when its last verdict accepted the title. */
  const judgedTitle = ref<string | null>(null);

  const noteExportBlockers: ExamWorkspaceTitleVerdict = (title, blockers) => {
    judgedTitle.value = blockers.some((blocker) => blocker.reason === "title_without_text") ? title : null;
  };

  const titleWithoutText = computed(
    () => judgedTitle.value !== null && judgedTitle.value === workspaceDocument.value?.title,
  );

  return { noteExportBlockers, titleWithoutText };
}
