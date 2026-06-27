/**
 * Document Converter filename-intent state.
 *
 * Domain purpose:
 *   Keep the teacher-editable filename stem aligned with the active
 *   backend-provided result filename while preserving backend authority for
 *   extension, content type, and final sanitized filename.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Supplies stem intent to protected Document Converter save/download
 *     endpoints.
 */

import { computed, ref, watch, type Ref } from "vue";

type FilenameParts = {
  extension: string | null;
  stem: string;
};

function splitFilename(filename: string): FilenameParts {
  const dotIndex = filename.lastIndexOf(".");
  if (dotIndex <= 0 || dotIndex === filename.length - 1) {
    return { stem: filename, extension: null };
  }
  return {
    extension: filename.slice(dotIndex + 1),
    stem: filename.slice(0, dotIndex),
  };
}

export function useDocumentConverterFilenameIntent(resultTitle: Readonly<Ref<string>>) {
  const filenameStemIntent = ref("");
  const resultFilenameParts = computed(() => splitFilename(resultTitle.value));
  const filenameExtensionLabel = computed(() => resultFilenameParts.value.extension);

  watch(
    resultTitle,
    (nextTitle) => {
      filenameStemIntent.value = splitFilename(nextTitle).stem;
    },
    { immediate: true },
  );

  return {
    filenameExtensionLabel,
    filenameStemIntent,
  };
}
