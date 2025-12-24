<script setup lang="ts">
import { computed } from "vue";
import { marked } from "marked";
import type { components } from "../../api/openapi";

type UiMarkdownOutput = components["schemas"]["UiMarkdownOutput"];

const props = defineProps<{ output: UiMarkdownOutput }>();

// Configure marked for safe output
marked.setOptions({
  breaks: true,
  gfm: true,
});

const renderedHtml = computed(() => {
  if (!props.output.markdown) return "";
  return marked.parse(props.output.markdown) as string;
});
</script>

<template>
  <div
    class="p-4 border border-navy bg-white shadow-brutal-sm prose prose-sm prose-navy max-w-none"
    v-html="renderedHtml"
  />
</template>
