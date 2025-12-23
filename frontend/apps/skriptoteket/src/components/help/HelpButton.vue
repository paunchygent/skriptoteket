<script setup lang="ts">
import { useHelp } from "./useHelp";

const props = withDefaults(
  defineProps<{
    label?: string;
  }>(),
  {
    label: "Hjälp",
  },
);

const { isOpen, toggle } = useHelp();
</script>

<template>
  <button
    type="button"
    class="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-navy hover:text-burgundy transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40"
    :aria-expanded="isOpen"
    aria-controls="help-panel"
    aria-haspopup="dialog"
    @click="toggle"
  >
    {{ props.label }}
  </button>
</template>
