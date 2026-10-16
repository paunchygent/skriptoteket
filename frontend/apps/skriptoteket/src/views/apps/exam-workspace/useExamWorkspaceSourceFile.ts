/**
 * Exam workspace source-file intake.
 *
 * Domain purpose:
 *   Accept one .docx exam from the file picker or a drop and hand it to the
 *   import; any other file, or several exams in one drop, leaves the
 *   current state and shows Swedish guidance instead. While the import is
 *   blocked (busy, or unsaved changes the new exam would discard) a picked
 *   or dropped file is ignored; the Filer pane explains why.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`; `ExamWorkspaceFilesMode` shows
 *     `sourceFileError`.
 *   - Imports through `useExamWorkspaceDocument.importDocument` and reads
 *     its `importBlocked` rule, the same one that disables the picker.
 */

import { ref } from "vue";
import type { Ref } from "vue";

const DOCX_EXTENSION = ".docx";
const INVALID_DOCX_COPY = "Det gick inte att använda filen. Välj en .docx-fil.";
const MULTIPLE_FILES_COPY = "Välj en provfil åt gången.";

function isDocxFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(DOCX_EXTENSION);
}

export function useExamWorkspaceSourceFile(
  importDocument: (file: File, courseKey: string | null) => Promise<void>,
  importBlocked: Readonly<Ref<boolean>>,
) {
  const sourceFileError = ref<string | null>(null);

  function handleSelectedFile(file: File, courseKey: string | null): void {
    if (importBlocked.value) {
      return;
    }
    if (!isDocxFile(file)) {
      sourceFileError.value = INVALID_DOCX_COPY;
      return;
    }
    sourceFileError.value = null;
    void importDocument(file, courseKey);
  }

  function handleDroppedFiles(files: File[], courseKey: string | null): void {
    if (importBlocked.value) {
      return;
    }
    const docxFiles = files.filter(isDocxFile);
    if (docxFiles.length > 1) {
      sourceFileError.value = MULTIPLE_FILES_COPY;
      return;
    }
    const [file] = docxFiles;
    if (file) {
      sourceFileError.value = null;
      void importDocument(file, courseKey);
      return;
    }
    sourceFileError.value = INVALID_DOCX_COPY;
  }

  return { handleDroppedFiles, handleSelectedFile, sourceFileError };
}
