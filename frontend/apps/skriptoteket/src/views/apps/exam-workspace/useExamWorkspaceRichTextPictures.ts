/**
 * Exam workspace rich-text pictures.
 *
 * Domain purpose:
 *   With the optional `pictures` switch the surface also takes pictures: a
 *   dropped or pasted PNG or JPEG file goes to the picture service with this
 *   surface as its target, a drag shows the drop line, and the target's
 *   `placePicture` puts the new picture alone in its own paragraph at the
 *   caret or replaces the selected picture in place, in one undo step.
 *   `selectedPictureId` is the selected picture's asset id, so the
 *   toolbar offers "Byt bild". Without the switch nothing about drop, paste
 *   or the drop line changes.
 *
 * Relationships:
 *   - Wired in by `ExamWorkspaceRichTextEditor`, which owns the editor, the
 *     `asToolbarEdit` boundary and the target object: the editor's
 *     `editorProps` spreads the composable's props, its `onTransaction` calls
 *     the composable's update, and the target's `placePicture` runs the
 *     composable's placement inside one toolbar edit.
 *   - Reads the picture service with `useExamWorkspacePictures` and places
 *     with `examWorkspacePicturePlacement`; the toolbar reads
 *     `selectedPictureId` through the target.
 */

import type { Editor } from "@tiptap/core";
import { NodeSelection, TextSelection } from "@tiptap/pm/state";
import type { EditorProps, EditorView } from "@tiptap/pm/view";
import { ref } from "vue";
import type { Ref } from "vue";

import { picturePlacement } from "./examWorkspacePicturePlacement";
import { useExamWorkspacePictures } from "./examWorkspacePictureService";
import type { RichTextTarget } from "./examWorkspaceRichTextTarget";
import { EXAM_PICTURE_NODE } from "./examWorkspaceRichTextSchema";

export function useExamWorkspaceRichTextPictures(options: {
  /** While true, the surface takes dropped and pasted pictures. */
  pictures: () => boolean;
  /** The editor, once TipTap created it. */
  editor: () => Editor | undefined;
  /** This surface as the picture service sees it. */
  target: () => RichTextTarget;
}): {
  /** The selected picture's asset id, or null, so the toolbar offers "Byt bild". */
  selectedPictureId: Ref<string | null>;
  /** Drop and paste of picture files, for the editor's `editorProps`. Empty while pictures are off. */
  pictureEditorProps(): Pick<EditorProps, "handlePaste" | "handleDrop">;
  /** Refresh `selectedPictureId` from the editor's current selection. */
  updatePictureSelected(): void;
  /** Place `assetId` alone in its own paragraph at the caret, or replace the selected picture in place. */
  placePictureAsset(assetId: string): void;
} {
  const pictureService = useExamWorkspacePictures();
  const selectedPictureId: Ref<string | null> = ref(null);

  /** Picture files on a paste: PNG, JPEG, or a file whose type the intake must sniff from its bytes. */
  function pastedPictureFiles(event: ClipboardEvent): File[] {
    const files = event.clipboardData?.files;
    if (!files) {
      return [];
    }
    return Array.from(files).filter(
      (file) => file.type === "image/png" || file.type === "image/jpeg" || file.type === "",
    );
  }

  /** The files one drag carries, in order. */
  function droppedFiles(event: DragEvent): File[] {
    const files = event.dataTransfer?.files;
    return files ? Array.from(files) : [];
  }

  /** Move the caret to the point the pointer dropped on, so the picture lands there. */
  function moveCaretToDropPoint(view: EditorView, event: DragEvent): void {
    try {
      const point = view.posAtCoords({ left: event.clientX, top: event.clientY });
      if (point === null) {
        return;
      }
      // A drop between two blocks lands in the nearest text, never outside one.
      const caret = TextSelection.near(view.state.doc.resolve(point.pos));
      view.dispatch(view.state.tr.setSelection(caret));
    } catch {
      // Without layout there are no coordinates: the picture keeps the caret's place.
    }
  }

  /**
   * Drop and paste of picture files, on a surface that takes pictures only.
   * Both hand the files to the picture service with this surface as the target,
   * and the service, not the editor, decides which files it accepts.
   */
  function pictureEditorProps(): Pick<EditorProps, "handlePaste" | "handleDrop"> {
    if (!options.pictures()) {
      return {};
    }
    return {
      handlePaste: (_view, event) => {
        const files = pastedPictureFiles(event);
        if (files.length === 0) {
          // Any other paste stays a text paste.
          return false;
        }
        void pictureService?.add(options.target(), files);
        return true;
      },
      handleDrop: (view, event, _slice, moved) => {
        if (moved) {
          return false;
        }
        const files = droppedFiles(event);
        if (files.length === 0) {
          return false;
        }
        moveCaretToDropPoint(view, event);
        void pictureService?.add(options.target(), files);
        return true;
      },
    };
  }

  /** `selectedPictureId` follows the selection: the whole picture atom's asset id, else null. */
  function updatePictureSelected(): void {
    const current = options.editor();
    if (!current) {
      return;
    }
    const { selection } = current.state;
    if (selection instanceof NodeSelection && selection.node.type.name === EXAM_PICTURE_NODE) {
      const assetId = selection.node.attrs.assetId;
      selectedPictureId.value = typeof assetId === "string" ? assetId : null;
      return;
    }
    selectedPictureId.value = null;
  }

  /**
   * The target's `placePicture` body: one placement transaction for `assetId`,
   * dispatched and focused. The editor runs this inside `asToolbarEdit`, so
   * the whole placement is one undo step.
   */
  function placePictureAsset(assetId: string): void {
    const current = options.editor();
    if (!current || current.isDestroyed) {
      return;
    }
    const transaction = picturePlacement(current.state, assetId);
    if (transaction === null) {
      return;
    }
    current.view.dispatch(transaction);
    current.view.focus();
  }

  return { selectedPictureId, pictureEditorProps, updatePictureSelected, placePictureAsset };
}
