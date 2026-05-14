/**
 * Exam Converter source-file intake state.
 *
 * Domain purpose:
 *   Own the browser-local `.dxe` source-file selection used by the
 *   authenticated Exam Converter before any submit, conversion, or save
 *   behavior is introduced.
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
const MISSING_DXE_COPY = "Välj en .dxe-fil från Exam.net.";

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

export function useExamConverterSourceFile() {
  const selectedSourceFile = ref<ExamConverterSourceFileSelection | null>(null);
  const sourceFileError = ref<string | null>(null);

  function selectSourceFile(file: File): void {
    if (!isDxeFile(file)) {
      selectedSourceFile.value = null;
      sourceFileError.value = MISSING_DXE_COPY;
      return;
    }

    selectedSourceFile.value = {
      file,
      name: file.name,
      sizeLabel: formatFileSize(file.size),
    };
    sourceFileError.value = null;
  }

  function clearSourceFile(): void {
    selectedSourceFile.value = null;
    sourceFileError.value = null;
  }

  return {
    clearSourceFile,
    selectSourceFile,
    selectedSourceFile,
    sourceFileError,
  };
}
