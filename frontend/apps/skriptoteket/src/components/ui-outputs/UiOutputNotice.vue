<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";
import { SystemMessage } from "../ui";

type UiNoticeOutput = components["schemas"]["UiNoticeOutput"];

const props = defineProps<{ output: UiNoticeOutput; density?: "default" | "compact" }>();

const tone = computed(() => {
  if (props.output.level === "error") return "failure";
  if (props.output.level === "warning") return "warning";
  return "info";
});
</script>

<template>
  <SystemMessage :tone="tone">{{ output.message }}</SystemMessage>
</template>
