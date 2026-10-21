/**
 * Exam workspace new-exam intake (TASK-SKRIPT-40-04-21).
 *
 * Domain purpose:
 *   Whether the open browser draft holds anything worth keeping, so creating
 *   over it never silently discards a guest's work. The creation itself runs
 *   through the gate-owned replacement coordinator (Nytt prov is a third
 *   replacement intent, modelled on Spara som): the source settles behind
 *   the shared barrier first, and the guest's browser slot is replaced only
 *   while it still holds exactly the draft this check read.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceNewExam`, which owns the open gate, the guest
 *     confirm and the failure handling around this intake.
 */

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";

/** The failure copy when the new exam could not be created. */
export const NEW_EXAM_FAILURE_COPY = "Det gick inte att skapa ett nytt prov. Försök igen.";

/** The one item's content the draft check reads; every other item field keeps its stored value. */
function blankItemIsEmpty(item: NativeExamItem): boolean {
  return (
    item.body.length === 0 &&
    item.choices.length === 0 &&
    item.gaps.length === 0 &&
    item.kept_gaps.length === 0 &&
    item.match_left.length === 0 &&
    item.match_right.length === 0 &&
    item.criteria.length === 0 &&
    (item.facit_text === null || item.facit_text === undefined)
  );
}

/**
 * True when the open draft holds anything worth keeping. False only when
 * every one of these holds; when in doubt this says "has content", because a
 * wrong "empty" would discard a guest's work.
 */
export function examWorkspaceDraftHasContent(document: NativeExamDocument): boolean {
  if (document.title.trim() !== "") return true;
  if (document.header.course !== null && document.header.course !== undefined) return true;
  if (document.header.tags.length !== 0) return true;
  if (document.instructions.length !== 0) return true;
  if (document.parents.length !== 0) return true;
  if (document.assets.length !== 0) return true;
  const [only, ...rest] = document.items;
  if (only === undefined || rest.length !== 0) return true;
  return !blankItemIsEmpty(only);
}
