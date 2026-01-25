<script setup lang="ts">
import { computed } from "vue";

import UiSegmentedToggle, { type UiSegmentedToggleOption } from "../ui/UiSegmentedToggle.vue";

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

const options = computed<UiSegmentedToggleOption[]>(() => [
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

function onSelect(value: string): void {
  emit("select", value as EditorWorkspaceMode);
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
