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

export function useDocumentConverterFilenameIntent(resultFilename: Readonly<Ref<string | null>>) {
  const filenameStemIntent = ref("");
  const resultFilenameParts = computed<FilenameParts>(() => {
    if (!resultFilename.value) {
      return { stem: "", extension: null };
    }
    return splitFilename(resultFilename.value);
  });
  const filenameExtensionLabel = computed(() => resultFilenameParts.value.extension);

  watch(
    resultFilename,
    (nextFilename) => {
      filenameStemIntent.value = nextFilename ? splitFilename(nextFilename).stem : "";
    },
    { immediate: true },
  );

  return {
    filenameExtensionLabel,
    filenameStemIntent,
  };
}
