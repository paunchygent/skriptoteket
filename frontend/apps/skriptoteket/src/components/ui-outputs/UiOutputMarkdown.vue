<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";
import UiMarkdown from "../ui/UiMarkdown.vue";

type UiMarkdownOutput = components["schemas"]["UiMarkdownOutput"];

const props = withDefaults(defineProps<{ output: UiMarkdownOutput; density?: "default" | "compact" }>(), {
  density: "default",
});

const isCompact = computed(() => props.density === "compact");
</script>

<template>
  <div
    v-if="props.output.markdown"
    :class="[
      isCompact
        ? 'p-3 border border-navy/20 bg-white shadow-brutal-sm'
        : 'p-4 border border-navy bg-white shadow-brutal-sm',
    ]"
  >
    <UiMarkdown :markdown="props.output.markdown" />
  </div>
</template>
