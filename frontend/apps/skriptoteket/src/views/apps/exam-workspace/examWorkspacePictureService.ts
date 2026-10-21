/**
 * Exam workspace picture service.
 *
 * Domain purpose:
 *   The one way a picture file enters an exam text: the toolbar's Lägg till
 *   bild / Byt bild, a dropped file and a pasted file all hand their files to
 *   `add` with the rich surface they target. The service checks each file,
 *   records the new picture for the open exam, and places it on the target;
 *   a refused file leaves the text unchanged and shows the refused inline
 *   notice, never a toast. `busy` is true while a file is being read.
 *
 * Relationships:
 *   - Provided once by `ExamWorkspaceEditorPane` for the open exam; read by
 *     the four editors that show the picture control and by
 *     `ExamWorkspaceRichTextEditor` for drop and paste.
 *   - A subtree without a provider gets null: the picture control hides and
 *     drop and paste of files do nothing.
 */

import { inject, provide } from "vue";
import type { InjectionKey, Ref } from "vue";

import type { RichTextTarget } from "./examWorkspaceRichTextTarget";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

export type ExamWorkspacePictureService = {
  /** True while a chosen, dropped or pasted file is being read. */
  busy: Ref<boolean>;
  /** The refused-file notice, or null. */
  notice: Ref<ExamWorkspaceNotice | null>;
  /** Check `files` in order and place each on `target`; the first refusal stops and shows the notice. */
  add(target: RichTextTarget, files: readonly File[]): Promise<void>;
  dismissNotice(): void;
};

const PICTURE_SERVICE_KEY: InjectionKey<ExamWorkspacePictureService> = Symbol(
  "exam-workspace-picture-service",
);

export function provideExamWorkspacePictures(service: ExamWorkspacePictureService): void {
  provide(PICTURE_SERVICE_KEY, service);
}

/** The open exam's picture service, or null where no editor pane provides one. */
export function useExamWorkspacePictures(): ExamWorkspacePictureService | null {
  return inject(PICTURE_SERVICE_KEY, null);
}
