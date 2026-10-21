<script setup lang="ts">
import { computed } from "vue";

import { UiSegmentedToggle, type UiSegmentedToggleOption } from "../ui";

type EditorWorkspaceMode = "source" | "diff" | "metadata" | "test";

type EditorWorkspaceModeSelectorProps = {
  activeMode: EditorWorkspaceMode;
  canEnterDiff: boolean;
  openCompareTitle: string;
};

const props = defineProps<EditorWorkspaceModeSelectorProps>();

const emit = defineEmits<{
  (event: "select", mode: EditorWorkspaceMode): void;
}>();

type EditorWorkspaceModeOption = UiSegmentedToggleOption & {
  value: EditorWorkspaceMode;
};

const options = computed<EditorWorkspaceModeOption[]>(() => [
  { value: "source", label: "Källkod" },
  {
    value: "diff",
    label: "Diff",
    title: props.openCompareTitle || undefined,
    disabled: !props.canEnterDiff && props.activeMode !== "diff",
  },
  { value: "metadata", label: "Metadata" },
  { value: "test", label: "Testkör" },
]);

function isEditorWorkspaceMode(value: string): value is EditorWorkspaceMode {
  switch (value) {
    case "source":
    case "diff":
    case "metadata":
    case "test":
      return true;
    default:
      return false;
  }
}

function onSelect(value: string): void {
  if (isEditorWorkspaceMode(value)) {
    emit("select", value);
  }
}
</script>

<template>
  <UiSegmentedToggle
    :model-value="props.activeMode"
    :options="options"
    density="compact"
    aria-label="Välj editor-läge"
    :columns="4"
    width="full"
    @update:model-value="onSelect"
  />
</template>
