<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";

type UiHtmlSandboxedOutput = components["schemas"]["UiHtmlSandboxedOutput"];

const props = withDefaults(defineProps<{ output: UiHtmlSandboxedOutput; density?: "default" | "compact" }>(), {
  density: "default",
});

const isCompact = computed(() => props.density === "compact");
</script>

<template>
  <div :class="[isCompact ? 'panel-inset' : 'border border-navy bg-white shadow-brutal-sm']">
    <iframe
      sandbox=""
      :srcdoc="props.output.html"
      :class="[isCompact ? 'block w-full min-h-[240px] border-0 bg-canvas' : 'block w-full min-h-[260px] border-0 bg-canvas']"
    />
  </div>
</template>
