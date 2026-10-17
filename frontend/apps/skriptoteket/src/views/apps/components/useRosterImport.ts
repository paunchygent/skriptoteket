import { computed, ref, watch, type Ref } from "vue";

import type { Roster } from "../classroomPlannerTypes";
import { useClassListImportFlow, type AmbiguousRow } from "../useClassListImportFlow";

interface RosterImportOptions {
  apiPath?: string;
  roster: () => Roster | null | undefined;
}

interface RosterImportFields {
  name: Ref<string>;
  rawStudents: Ref<string>;
  formError: Ref<string | null>;
}

/** Owns file intake and reconciliation of an import preview into the editable roster. */
export function useRosterImport(options: RosterImportOptions, fields: RosterImportFields) {
  const fileInput = ref<HTMLInputElement | null>(null);
  const ambiguousRows = ref<AmbiguousRow[]>([]);
  const isImportDropActive = ref(false);
  const { isUploading, preview, error: importError, uploadFile, cancel: resetImportState } =
    useClassListImportFlow({ apiPath: options.apiPath });

  const importDropZoneClass = computed(() => {
    if (isUploading.value) {
      return "border-navy/20 bg-navy/5 text-navy/45";
    }
    if (isImportDropActive.value) {
      return "border-action bg-panel text-navy";
    }
    return "border-navy/25 bg-panel/80 text-navy/70";
  });

  function resetImport(): void {
    ambiguousRows.value = [];
    isImportDropActive.value = false;
    resetImportState();
  }

  watch(options.roster, resetImport, { immediate: true });

  watch(preview, (nextPreview) => {
    if (!nextPreview) {
      ambiguousRows.value = [];
      return;
    }

    fields.name.value = nextPreview.suggested_class_name?.trim() || fields.name.value;
    fields.rawStudents.value = nextPreview.parsed_students.map((student) => student.full_name).join("\n");
    ambiguousRows.value = [...nextPreview.ambiguous_rows];
    fields.formError.value = null;
  });

  function triggerFileInput(): void {
    fileInput.value?.click();
  }

  function isFileDragEvent(event: DragEvent): boolean {
    const dataTransfer = event.dataTransfer;
    if (!dataTransfer) {
      return false;
    }
    if (dataTransfer.files.length > 0) {
      return true;
    }
    return Array.from(dataTransfer.types ?? []).includes("Files");
  }

  async function handleImportFile(file: File): Promise<void> {
    if (isUploading.value) {
      return;
    }

    isImportDropActive.value = false;
    importError.value = null;
    await uploadFile(file);
  }

  async function onFileSelected(event: Event): Promise<void> {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }

    const file = target.files?.[0];
    if (!file) {
      return;
    }

    await handleImportFile(file);
    target.value = "";
  }

  function onImportDragEnter(event: DragEvent): void {
    if (!isFileDragEvent(event) || isUploading.value) {
      return;
    }

    event.preventDefault();
    isImportDropActive.value = true;
  }

  function onImportDragOver(event: DragEvent): void {
    if (!isFileDragEvent(event) || isUploading.value) {
      return;
    }

    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "copy";
    }
    isImportDropActive.value = true;
  }

  function onImportDragLeave(event: DragEvent): void {
    const currentTarget = event.currentTarget;
    const relatedTarget = event.relatedTarget;
    if (
      currentTarget instanceof HTMLElement
      && relatedTarget instanceof Node
      && currentTarget.contains(relatedTarget)
    ) {
      return;
    }

    isImportDropActive.value = false;
  }

  async function onImportDrop(event: DragEvent): Promise<void> {
    event.preventDefault();
    isImportDropActive.value = false;

    if (isUploading.value) {
      return;
    }

    const files = event.dataTransfer?.files;
    if (!files || files.length === 0) {
      importError.value = "Ingen fil hittades i släppningen.";
      return;
    }
    if (files.length > 1) {
      importError.value = "Släpp en fil i taget.";
      return;
    }

    const [file] = Array.from(files);
    if (!file) {
      importError.value = "Ingen fil hittades i släppningen.";
      return;
    }

    await handleImportFile(file);
  }

  function appendAmbiguousRow(index: number): void {
    const row = ambiguousRows.value[index];
    if (!row) {
      return;
    }

    const nextValue = fields.rawStudents.value.trim();
    fields.rawStudents.value = nextValue.length > 0 ? `${nextValue}\n${row.raw_text}` : row.raw_text;
    ambiguousRows.value.splice(index, 1);
  }

  function dismissAmbiguousRow(index: number): void {
    ambiguousRows.value.splice(index, 1);
  }

  return {
    fileInput,
    ambiguousRows,
    isImportDropActive,
    isUploading,
    preview,
    importError,
    importDropZoneClass,
    resetImport,
    triggerFileInput,
    onFileSelected,
    onImportDragEnter,
    onImportDragOver,
    onImportDragLeave,
    onImportDrop,
    appendAmbiguousRow,
    dismissAmbiguousRow,
  };
}
