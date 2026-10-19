/**
 * Exam workspace gap open request.
 *
 * Domain purpose:
 *   Let the export-blocker jump open one gap chip's popover. A gap chip
 *   opens only through ProseMirror's own click handling, so a synthetic
 *   click never opens anything; the jump dispatches this bubbling request on
 *   the chip instead and the body editor opens that gap's popover.
 *
 * Relationships:
 *   - Dispatched by `useExamWorkspaceSaveFlow` (`gotoBlocker`) through
 *     `requestOpenGap`; handled by `ExamWorkspaceBodyEditor`, which opens
 *     the popover through `openPopover`.
 */

/** The bubbling request a gap chip carries when something asks for its popover. */
export const EXAM_WORKSPACE_OPEN_GAP_EVENT = "exam-workspace-open-gap";

/** Ask the body editor to open `chip`'s popover through its bubbling open-gap request. */
export function requestOpenGap(chip: HTMLElement): void {
  chip.dispatchEvent(new CustomEvent(EXAM_WORKSPACE_OPEN_GAP_EVENT, { bubbles: true }));
}
