<script setup lang="ts">
/** Document metadata lifecycle, separate from question selection and the toolbar. */
import { ref, watch } from "vue";
import type { ExamCourseChoice, ExamWorkspaceDocumentSummary, NativeExamDocument } from "../../../api/examWorkspace";
import ExamWorkspaceMetadataDrawer from "./ExamWorkspaceMetadataDrawer.vue";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import type { ExamWorkspaceRenameFailure } from "./useExamWorkspaceRename";

const props = defineProps<{
  document: NativeExamDocument;
  summary: ExamWorkspaceDocumentSummary;
  renameFile: (fileId: string, stem: string) => Promise<string | null>;
  renameFailure: ExamWorkspaceRenameFailure | null;
  disabled: boolean;
  layout: ExamWorkspaceLayout;
  detailsOpen: boolean;
  drawerId: string;
  setTitle: (title: string) => void;
  setCourse: (course: ExamCourseChoice | null) => void;
}>();
const emit = defineEmits<{ open: [] }>();
const isOpen = ref(false);
watch(() => props.detailsOpen, (value) => { if (value) isOpen.value = false; });
watch(() => props.summary.lineage_id, () => { isOpen.value = false; });
function open(): void {
  emit("open");
  isOpen.value = true;
}
defineExpose({ open, isOpen });
</script>

<template>
  <ExamWorkspaceMetadataDrawer
    v-if="isOpen"
    :id="drawerId"
    :title="document.title"
    :header="document.header"
    :name="summary.name"
    :vault-file-id="summary.vault_file_id"
    :rename-file="renameFile"
    :rename-failure="renameFailure"
    :disabled="disabled"
    :layout="layout"
    @update:title="setTitle"
    @update:course="setCourse"
    @close="isOpen = false"
  />
</template>
