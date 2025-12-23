<script setup lang="ts">
import type { components } from "../../api/openapi";

type RunArtifact = components["schemas"]["RunArtifact"];
type ArtifactEntry = components["schemas"]["ArtifactEntry"];

defineProps<{
  artifacts: (RunArtifact | ArtifactEntry)[];
}>();

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<template>
  <div
    v-if="artifacts.length > 0"
    class="space-y-2"
  >
    <div class="text-xs font-semibold uppercase tracking-wide text-navy/70">
      Filer
    </div>
    <ul class="space-y-1">
      <li
        v-for="artifact in artifacts"
        :key="artifact.artifact_id"
        class="flex items-center gap-3 text-sm"
      >
        <a
          :href="artifact.download_url"
          class="underline text-burgundy hover:text-navy"
          download
        >
          {{ artifact.path }}
        </a>
        <span class="text-navy/50 text-xs">
          {{ formatBytes(artifact.bytes) }}
        </span>
      </li>
    </ul>
  </div>
</template>
