/**
 * Exam Converter source-file intake state.
 *
 * Domain purpose:
 *   Own browser-local intake choices used by the authenticated Exam Converter
 *   before any submit, conversion, or save behavior is introduced.
 *
 * Relationships:
 *   - Used by `ExamConverterAuthenticatedView`.
 *   - Feeds selected-file presentation into the workflow rail and idle
 *     workspace drop zone.
 */

import { ref } from "vue";

export type ExamConverterSourceFileSelection = {
  file: File;
  name: string;
  sizeLabel: string;
};

const DXE_EXTENSION = ".dxe";
const MISSING_DXE_COPY = "Det gick inte att använda filen. Välj en .dxe-fil från Exam.net.";
const MULTIPLE_DXE_COPY = "Välj en provfil åt gången.";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const kibibytes = bytes / 1024;
  if (kibibytes < 1024) {
    return `${kibibytes.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} kB`;
  }
  return `${(kibibytes / 1024).toLocaleString("sv-SE", {
    maximumFractionDigits: 1,
  })} MB`;
}

function isDxeFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(DXE_EXTENSION);
}

function toSelection(file: File): ExamConverterSourceFileSelection {
  return {
    file,
    name: file.name,
    sizeLabel: formatFileSize(file.size),
  };
}

export function useExamConverterSourceFile() {
  const selectedSourceFile = ref<ExamConverterSourceFileSelection | null>(null);
  const sourceFileError = ref<string | null>(null);

  function selectSourceFile(file: File): void {
    if (!isDxeFile(file)) {
      sourceFileError.value = MISSING_DXE_COPY;
      return;
    }

    selectedSourceFile.value = toSelection(file);
    sourceFileError.value = null;
  }

  function selectDroppedFiles(files: File[]): void {
    const dxeFiles = files.filter(isDxeFile);

    if (dxeFiles.length > 1) {
      sourceFileError.value = MULTIPLE_DXE_COPY;
      return;
    }
    if (dxeFiles[0]) {
      selectedSourceFile.value = toSelection(dxeFiles[0]);
      sourceFileError.value = null;
      return;
    }
    sourceFileError.value = MISSING_DXE_COPY;
  }

  function clearSourceFile(): void {
    selectedSourceFile.value = null;
    sourceFileError.value = null;
  }

  function resetLocalChoices(): void {
    clearSourceFile();
  }

  return {
    clearSourceFile,
    resetLocalChoices,
    selectDroppedFiles,
    selectSourceFile,
    selectedSourceFile,
    sourceFileError,
  };
}
