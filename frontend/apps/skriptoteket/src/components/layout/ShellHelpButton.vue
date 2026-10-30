<script setup lang="ts">
/**
 * Hjälp opener of the shell top bars.
 *
 * Relationships:
 * - toggles the shared help panel through `useHelp` and records itself as the
 *   opener, so closing help returns focus here
 * - presents as a `ShellBarButton`, so it matches the other top-bar actions
 */

import { useHelp } from "../help/useHelp";
import ShellBarButton from "./ShellBarButton.vue";

withDefaults(
  defineProps<{
    wordFrom?: "always" | "desktop" | "tablet" | "never";
  }>(),
  {
    wordFrom: "desktop",
  },
);

const { isOpen, toggle } = useHelp();

function onToggle(event: MouseEvent): void {
  const opener = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
  toggle(opener);
}
</script>

<template>
  <ShellBarButton
    glyph="help"
    label="Hjälp"
    word="Hjälp"
    :word-from="wordFrom"
    aria-controls="help-panel"
    aria-haspopup="dialog"
    :aria-expanded="isOpen"
    @click="onToggle"
  />
</template>
