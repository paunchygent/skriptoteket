<script setup lang="ts">
import { computed } from "vue";
import DOMPurify from "dompurify";
import { marked } from "marked";

const props = defineProps<{ markdown: string }>();

const renderedHtml = computed(() => {
  const html = marked.parse(props.markdown, { breaks: true, gfm: true }) as string;

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
    class="prose prose-sm max-w-none text-navy prose-a:text-burgundy prose-code:font-mono prose-pre:font-mono"
    v-html="renderedHtml"
  />
</template>
