/**
 * Exam workspace source-file intake.
 *
 * Domain purpose:
 *   Accept one .docx exam from the file picker or a drop and hand it to the
 *   import; any other file, or several exams in one drop, leaves the
 *   current state and shows Swedish guidance instead.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`; `ExamWorkspaceFilesMode` shows
 *     `sourceFileError`.
 *   - Imports through `useExamWorkspaceDocument.importDocument`.
 */

import { ref } from "vue";

const DOCX_EXTENSION = ".docx";
const INVALID_DOCX_COPY = "Det gick inte att använda filen. Välj en .docx-fil.";
const MULTIPLE_FILES_COPY = "Välj en provfil åt gången.";

function isDocxFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(DOCX_EXTENSION);
}

export function useExamWorkspaceSourceFile(importDocument: (file: File) => Promise<void>) {
  const sourceFileError = ref<string | null>(null);

  function handleSelectedFile(file: File): void {
    if (!isDocxFile(file)) {
      sourceFileError.value = INVALID_DOCX_COPY;
      return;
    }
    sourceFileError.value = null;
    void importDocument(file);
  }

  function handleDroppedFiles(files: File[]): void {
    const docxFiles = files.filter(isDocxFile);
    if (docxFiles.length > 1) {
      sourceFileError.value = MULTIPLE_FILES_COPY;
      return;
    }
    const [file] = docxFiles;
    if (file) {
      sourceFileError.value = null;
      void importDocument(file);
      return;
    }
    sourceFileError.value = INVALID_DOCX_COPY;
  }

  return { handleDroppedFiles, handleSelectedFile, sourceFileError };
}
