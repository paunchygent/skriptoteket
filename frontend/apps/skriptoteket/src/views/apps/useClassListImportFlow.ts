/**
 * Class-list import flow state for Klassrumskartan.
 *
 * This composable owns the upload/preview state used inside the class-list
 * create/edit modal. It stays transport-focused so the modal can prefill the
 * editable class name and student list before the normal save flow persists
 * the roster.
 */

import { ref } from "vue";

import { apiPost, isApiError } from "../../api/client";

export interface ParsedStudentRow {
  full_name: string;
  given_name?: string | null;
  family_name?: string | null;
  row_number?: number | null;
}

export interface AmbiguousRow {
  raw_text: string;
  row_number?: number | null;
  reason?: string | null;
}

export interface ClassListImportPreview {
  suggested_class_name?: string | null;
  parsed_students: ParsedStudentRow[];
  ambiguous_rows: AmbiguousRow[];
  file_name: string;
}

function getImportErrorMessage(error: unknown, fallbackMessage: string): string {
  if (isApiError(error)) {
    return error.message;
  }
  return fallbackMessage;
}

export function useClassListImportFlow() {
  const isUploading = ref(false);
  const preview = ref<ClassListImportPreview | null>(null);
  const error = ref<string | null>(null);

  async function uploadFile(file: File): Promise<void> {
    isUploading.value = true;
    error.value = null;
    preview.value = null;

    const formData = new FormData();
    formData.append("file", file);

    try {
      preview.value = await apiPost<ClassListImportPreview>(
        "/api/v1/apps/classroom.group-seating-studio/rosters/import-preview",
        formData,
      );
    } catch (uploadError: unknown) {
      error.value = getImportErrorMessage(uploadError, "Misslyckades att läsa in filen.");
    } finally {
      isUploading.value = false;
    }
  }

  function cancel() {
    preview.value = null;
    error.value = null;
  }

  return {
    isUploading,
    preview,
    error,
    uploadFile,
    cancel,
  };
}
