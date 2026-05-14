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

export type ExamConverterTargetFormat = "pdf" | "qti";

export type ExamConverterTargetSelection = Record<ExamConverterTargetFormat, boolean>;

const DXE_EXTENSION = ".dxe";
const PDF_EXTENSION = ".pdf";
const MISSING_DXE_COPY = "Välj en .dxe-fil från Exam.net.";
const MISSING_PDF_COPY = "Välj en PDF-fil för svarsmall.";
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

function isPdfFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(PDF_EXTENSION);
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
  const selectedSupportingFile = ref<ExamConverterSourceFileSelection | null>(null);
  const selectedTargetFormats = ref<ExamConverterTargetSelection>({
    pdf: true,
    qti: true,
  });
  const sourceFileError = ref<string | null>(null);
  const supportingFileError = ref<string | null>(null);

  function selectSourceFile(file: File): void {
    if (!isDxeFile(file)) {
      selectedSourceFile.value = null;
      sourceFileError.value = MISSING_DXE_COPY;
      return;
    }

    selectedSourceFile.value = toSelection(file);
    sourceFileError.value = null;
  }

  function selectSupportingFile(file: File): void {
    if (!isPdfFile(file)) {
      selectedSupportingFile.value = null;
      supportingFileError.value = MISSING_PDF_COPY;
      return;
    }

    selectedSupportingFile.value = toSelection(file);
    supportingFileError.value = null;
  }

  function selectDroppedFiles(files: File[]): void {
    const dxeFiles = files.filter(isDxeFile);
    const pdfFiles = files.filter(isPdfFile);

    if (dxeFiles.length > 1) {
      selectedSourceFile.value = null;
      sourceFileError.value = MULTIPLE_DXE_COPY;
    } else if (dxeFiles[0]) {
      selectedSourceFile.value = toSelection(dxeFiles[0]);
      sourceFileError.value = null;
    } else {
      sourceFileError.value = MISSING_DXE_COPY;
    }

    if (pdfFiles[0]) {
      selectedSupportingFile.value = toSelection(pdfFiles[0]);
      supportingFileError.value = null;
    }
  }

  function clearSourceFile(): void {
    selectedSourceFile.value = null;
    sourceFileError.value = null;
  }

  function clearSupportingFile(): void {
    selectedSupportingFile.value = null;
    supportingFileError.value = null;
  }

  function toggleTargetFormat(format: ExamConverterTargetFormat): void {
    selectedTargetFormats.value = {
      ...selectedTargetFormats.value,
      [format]: !selectedTargetFormats.value[format],
    };
  }

  function resetLocalChoices(): void {
    clearSourceFile();
    clearSupportingFile();
    selectedTargetFormats.value = {
      pdf: true,
      qti: true,
    };
  }

  return {
    clearSupportingFile,
    clearSourceFile,
    resetLocalChoices,
    selectDroppedFiles,
    selectSupportingFile,
    selectSourceFile,
    selectedSupportingFile,
    selectedSourceFile,
    selectedTargetFormats,
    supportingFileError,
    sourceFileError,
    toggleTargetFormat,
  };
}
