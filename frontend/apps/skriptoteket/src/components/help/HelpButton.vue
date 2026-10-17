<script setup lang="ts">
/**
 * Shared help drawer opener.
 *
 * Relationships:
 * - records the triggering button for drawer focus restoration
 * - delegates global open/close state to `useHelp`
 */
import { useHelp } from "./useHelp";
import UiDenseActionButton from "../ui/shared/components/UiDenseActionButton.vue";

const props = withDefaults(
  defineProps<{
    label?: string;
  }>(),
  {
    label: "Hjälp",
  },
);

const { isOpen, toggle } = useHelp();

function onToggle(event: MouseEvent): void {
  const opener = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
  toggle(opener);
}
</script>

<template>
  <UiDenseActionButton
    :label="props.label"
    :expanded="isOpen"
    aria-controls="help-panel"
    aria-haspopup="dialog"
    @click="onToggle"
  />
</template>
