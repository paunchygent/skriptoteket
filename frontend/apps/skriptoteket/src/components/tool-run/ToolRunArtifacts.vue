<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";

type RunArtifact = components["schemas"]["RunArtifact"];
type ArtifactEntry = components["schemas"]["ArtifactEntry"];

const props = withDefaults(defineProps<{
  artifacts: (RunArtifact | ArtifactEntry)[];
  density?: "default" | "compact";
}>(), {
  density: "default",
});

const isCompact = computed(() => props.density === "compact");

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<template>
  <div
    v-if="artifacts.length > 0"
    :class="[isCompact ? 'border border-navy/20 bg-white shadow-brutal-sm' : 'space-y-2']"
  >
    <div
      v-if="isCompact"
      class="border-b border-navy/20 px-3 py-2 flex items-center justify-between gap-3"
    >
      <span class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
        Filer
      </span>
      <span class="text-[10px] text-navy/60">
        {{ artifacts.length }}
      </span>
    </div>
    <div
      v-else
      class="text-xs font-semibold uppercase tracking-wide text-navy/70"
    >
      Filer
    </div>

    <ul :class="[isCompact ? 'px-3 py-2 space-y-1' : 'space-y-1']">
      <li
        v-for="artifact in artifacts"
        :key="artifact.artifact_id"
        :class="[isCompact ? 'flex items-center gap-3 text-[11px]' : 'flex items-center gap-3 text-sm']"
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
