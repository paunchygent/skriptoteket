<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiMarkdownOutput = components["schemas"]["UiMarkdownOutput"];

defineProps<{ output: UiMarkdownOutput }>();
</script>

<template>
  <div class="p-4 border border-navy bg-white shadow-brutal-sm">
    <pre class="whitespace-pre-wrap font-mono text-sm text-navy">{{ output.markdown }}</pre>
  </div>
</template>

