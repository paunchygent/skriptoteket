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
 *   - `useExamWorkspacePictureControl` is the toolbar side the four editors
 *     share: the button's state and where a chosen file goes.
 */

import { computed, inject, provide, ref } from "vue";
import type { ComputedRef, InjectionKey, Ref } from "vue";

import type { NativeExamAsset, NativeExamDocument } from "../../../api/examWorkspace";
import { readPicture, PICTURE_LIMIT_UNAVAILABLE_COPY } from "./examWorkspacePictureIntake";
import type { RichTextTarget } from "./examWorkspaceRichTextTarget";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
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

export type ExamWorkspacePictureServiceDeps = {
  /** The open document, or null while none is open. */
  document: () => NativeExamDocument | null;
  /** The session's new-picture registry; the save carries what it declares. */
  newPictures: { declare(asset: NativeExamAsset, blob: Blob): void };
  /** False while the pane is disabled: `add` does nothing. */
  canEdit: () => boolean;
  /** The opening the intake belongs to, or null while none is open. */
  opening: () => ExamWorkspaceOpening | null;
  /** Whether `opening` is still the exam opening in front of the teacher. */
  isOpen: (opening: ExamWorkspaceOpening) => boolean;
  /** The server-owned whole-exam byte cap, loaded once per service and retried after a failure. */
  maxExamBytes: () => Promise<number>;
  /** The intake check; defaults to `readPicture`. */
  read?: typeof readPicture;
};

/**
 * The one way a picture file enters an exam text. `add` checks each file in
 * order on `target`: the first refusal sets the notice and stops, so nothing
 * is placed. A picture is declared for the open exam and placed on the
 * target, clearing the notice. A second `add` while one runs is ignored.
 * One `add` belongs to the opening it started in: after every await it
 * continues only while that opening is still open, editing is still allowed
 * and the target is still live. A stale result is retired without declaring
 * or placing anything, leaving the notice unchanged and dropping the rest of
 * the batch. A limit the loader cannot read refuses with the unavailable
 * copy and is asked for again on the next `add`.
 */
export function createExamWorkspacePictureService(
  deps: ExamWorkspacePictureServiceDeps,
): ExamWorkspacePictureService {
  const busy = ref(false);
  const notice = ref<ExamWorkspaceNotice | null>(null);
  const read = deps.read ?? readPicture;
  let limitPromise: Promise<number> | null = null;

  /** The server-owned cap, loaded once per service; a rejected load is forgotten so the next `add` asks again. */
  async function loadMaxExamBytes(): Promise<number> {
    limitPromise ??= deps.maxExamBytes();
    try {
      return await limitPromise;
    } catch (error) {
      limitPromise = null;
      throw error;
    }
  }

  /** True while `opening` still owns this intake: still open, still editable, still live. */
  function isLiveIntake(opening: ExamWorkspaceOpening, target: RichTextTarget): boolean {
    return deps.isOpen(opening) && deps.canEdit() && target.isLive();
  }

  async function add(target: RichTextTarget, files: readonly File[]): Promise<void> {
    const opening = deps.opening();
    if (opening === null || !deps.canEdit() || busy.value) {
      return;
    }
    if (deps.document() === null || !target.acceptsPictures) {
      return;
    }
    busy.value = true;
    try {
      let maxExamBytes: number;
      try {
        maxExamBytes = await loadMaxExamBytes();
      } catch {
        if (isLiveIntake(opening, target)) {
          notice.value = { kind: "refused", text: PICTURE_LIMIT_UNAVAILABLE_COPY };
        }
        return;
      }
      for (const file of files) {
        if (!isLiveIntake(opening, target)) {
          return;
        }
        // Each file's size check counts the pictures placed before it, and a
        // replacement credits the selected picture it removes.
        const document = deps.document();
        if (document === null) {
          return;
        }
        const intake = await read(
          file,
          document,
          { maxExamBytes, replacing: target.selectedPictureId.value },
        );
        if (!isLiveIntake(opening, target)) {
          return;
        }
        if (intake.kind === "refused") {
          notice.value = { kind: "refused", text: intake.copy };
          return;
        }
        deps.newPictures.declare(intake.asset, intake.blob);
        target.placePicture(intake.asset.asset_id);
        notice.value = null;
      }
    } finally {
      busy.value = false;
    }
  }

  function dismissNotice(): void {
    notice.value = null;
  }

  return { busy, notice, add, dismissNotice };
}

/** A host's own rich surface: the editor or entry a chosen file falls back to. */
export type ExamWorkspacePictureSurface = {
  readonly target?: RichTextTarget | undefined;
  focus(): void;
};

export type ExamWorkspacePictureControl = {
  /** True where an editor pane provides the service: the button shows and the surface takes drops. */
  enabled: boolean;
  /** True while a whole picture is selected, so the button offers "Byt bild". */
  selected: ComputedRef<boolean>;
  /** True while a chosen file is being read. */
  busy: ComputedRef<boolean>;
  /** Hand a chosen file to the service. */
  add(file: File): void;
};

/**
 * The picture button's side of one editor host. A chosen file goes to the
 * selected surface when it takes pictures, else to the host's own surface
 * with the caret moved to its end, so the picture lands after the text.
 */
export function useExamWorkspacePictureControl(
  active: () => RichTextTarget | null,
  own: () => ExamWorkspacePictureSurface | null,
): ExamWorkspacePictureControl {
  const pictures = useExamWorkspacePictures();

  function pictureTarget(): RichTextTarget | null {
    const selected = active();
    if (selected?.acceptsPictures) {
      return selected;
    }
    return own()?.target ?? null;
  }

  function add(file: File): void {
    if (!pictures) {
      return;
    }
    const selected = active();
    if (selected?.acceptsPictures) {
      void pictures.add(selected, [file]);
      return;
    }
    const surface = own();
    surface?.focus();
    const target = surface?.target;
    if (target) {
      void pictures.add(target, [file]);
    }
  }

  return {
    enabled: pictures !== null,
    selected: computed(() => (pictureTarget()?.selectedPictureId.value ?? null) !== null),
    busy: computed(() => pictures?.busy.value ?? false),
    add,
  };
}
