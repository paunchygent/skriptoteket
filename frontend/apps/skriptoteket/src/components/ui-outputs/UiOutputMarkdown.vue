<script setup lang="ts">
import type { components } from "../../api/openapi";
import UiMarkdown from "../ui/UiMarkdown.vue";

type UiMarkdownOutput = components["schemas"]["UiMarkdownOutput"];

const props = defineProps<{ output: UiMarkdownOutput }>();
</script>

<template>
  <div
    v-if="props.output.markdown"
    class="p-4 border border-navy bg-white shadow-brutal-sm"
  >
    <UiMarkdown :markdown="props.output.markdown" />
  </div>
</template>
