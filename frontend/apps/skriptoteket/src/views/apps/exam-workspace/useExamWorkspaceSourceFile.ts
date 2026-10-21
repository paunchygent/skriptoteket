/**
 * Exam workspace source-file intake.
 *
 * Domain purpose:
 *   Accept one exam file, a Word .docx, a PDF .pdf, a DigiExam .dxe or a QTI .zip
 *   package, from the file picker or a drop and hand it to the import; any
 *   other file, or several exams in one drop, leaves the current state and
 *   shows Swedish guidance instead. While the import is
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

const EXAM_FILE_EXTENSIONS = [".docx", ".pdf", ".dxe", ".zip"];
const INVALID_FILE_COPY =
  "Det gick inte att använda filen. Välj en Word-fil (.docx), en PDF-fil (.pdf), en DigiExam-fil (.dxe) eller en QTI-fil (.zip).";
const MULTIPLE_FILES_COPY = "Välj en provfil åt gången.";

function isExamFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return EXAM_FILE_EXTENSIONS.some((extension) => name.endsWith(extension));
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
    if (!isExamFile(file)) {
      sourceFileError.value = INVALID_FILE_COPY;
      return;
    }
    sourceFileError.value = null;
    void importDocument(file, courseKey);
  }

  function handleDroppedFiles(files: File[], courseKey: string | null): void {
    if (importBlocked.value) {
      return;
    }
    const examFiles = files.filter(isExamFile);
    if (examFiles.length > 1) {
      sourceFileError.value = MULTIPLE_FILES_COPY;
      return;
    }
    const [file] = examFiles;
    if (file) {
      sourceFileError.value = null;
      void importDocument(file, courseKey);
      return;
    }
    sourceFileError.value = INVALID_FILE_COPY;
  }

  return { handleDroppedFiles, handleSelectedFile, sourceFileError };
}
