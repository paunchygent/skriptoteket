<script setup lang="ts">
/**
 * Course dropdown that doubles as a search field (TASK-SKRIPT-39-08-01, D17).
 *
 * Shared by the import panel and the document metadata drawer. `modelValue` is the
 * catalog entry key or null. Typing searches name and code in the browser; every
 * option shows name, code and school form. U3 implements the behaviour; this shell
 * fixes the component contract for its consumers.
 */
import type { ExamCourse } from "../../../api/examWorkspace";

defineProps<{
  modelValue: string | null;
  courses: ExamCourse[];
  disabled?: boolean;
  inputId: string;
  /** Raw course hint shown beside an empty field when nothing is preselected (D6). */
  hint?: string | null;
}>();

defineEmits<{
  "update:modelValue": [key: string | null];
}>();
</script>

<template>
  <div data-test="exam-course-combobox" />
</template>
