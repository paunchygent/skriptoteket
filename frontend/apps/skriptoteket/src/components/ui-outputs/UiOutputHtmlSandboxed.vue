<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiHtmlSandboxedOutput = components["schemas"]["UiHtmlSandboxedOutput"];

defineProps<{ output: UiHtmlSandboxedOutput }>();
</script>

<template>
  <div class="border border-navy bg-white shadow-brutal-sm">
    <iframe
      sandbox=""
      :srcdoc="output.html"
      class="block w-full min-h-[260px] border-0 bg-canvas"
    />
  </div>
</template>
