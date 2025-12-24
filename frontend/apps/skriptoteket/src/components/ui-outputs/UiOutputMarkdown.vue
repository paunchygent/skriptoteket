<script setup lang="ts">
import { computed } from "vue";
import DOMPurify from "dompurify";
import { marked } from "marked";
import type { components } from "../../api/openapi";

type UiMarkdownOutput = components["schemas"]["UiMarkdownOutput"];

const props = defineProps<{ output: UiMarkdownOutput }>();

const renderedHtml = computed(() => {
  if (!props.output.markdown) return "";
  const html = marked.parse(props.output.markdown, { breaks: true, gfm: true }) as string;

  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["style", "script", "iframe", "object", "embed", "svg", "math"],
    FORBID_ATTR: ["style"],
  });
});
</script>

<!-- eslint-disable vue/no-v-html -- sanitized with DOMPurify -->
<template>
  <div
    class="p-4 border border-navy bg-white shadow-brutal-sm prose prose-sm max-w-none text-navy prose-a:text-burgundy prose-code:font-mono prose-pre:font-mono"
    v-html="renderedHtml"
  />
</template>
