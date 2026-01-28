<script setup lang="ts">
import { computed, ref } from "vue";
import type { components } from "../../api/openapi";
import { isApiError } from "../../api/client";
import { useVaultFiles } from "../../composables/vault/useVaultFiles";
import { useToastStore } from "../../stores/toast";

type RunArtifact = components["schemas"]["RunArtifact"];
type ArtifactEntry = components["schemas"]["ArtifactEntry"];

const props = withDefaults(defineProps<{
  artifacts: (RunArtifact | ArtifactEntry)[];
  runId?: string | null;
  density?: "default" | "compact";
}>(), {
  runId: null,
  density: "default",
});

const isCompact = computed(() => props.density === "compact");
const toast = useToastStore();
const { saveFromRunArtifact } = useVaultFiles();

const savingIds = ref<Set<string>>(new Set());

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function filenameFromPath(path: string): string {
  const parts = path.split("/");
  const last = parts.at(-1);
  return last && last.length > 0 ? last : path;
}

async function saveToVault(artifact: RunArtifact | ArtifactEntry): Promise<void> {
  if (!props.runId) return;

  const artifactId = artifact.artifact_id;
  if (savingIds.value.has(artifactId)) return;

  const next = new Set(savingIds.value);
  next.add(artifactId);
  savingIds.value = next;

  try {
    const name = filenameFromPath(artifact.path);
    await saveFromRunArtifact({
      runId: props.runId,
      artifactId: artifactId,
      name,
    });
    toast.success("Sparade filen i Mina filer.");
  } catch (error: unknown) {
    if (isApiError(error)) {
      toast.failure(error.message);
    } else if (error instanceof Error) {
      toast.failure(error.message);
    } else {
      toast.failure("Det gick inte att spara filen i Mina filer.");
    }
  } finally {
    const cleared = new Set(savingIds.value);
    cleared.delete(artifactId);
    savingIds.value = cleared;
  }
}
</script>

<template>
  <div
    v-if="artifacts.length > 0"
    :class="[isCompact ? 'panel-inset' : 'space-y-2']"
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
        <button
          v-if="runId"
          type="button"
          class="btn-ghost border-navy/30 bg-canvas shadow-none ml-auto"
          :disabled="savingIds.has(artifact.artifact_id)"
          @click="void saveToVault(artifact)"
        >
          {{ savingIds.has(artifact.artifact_id) ? "Sparar…" : "Spara i Mina filer" }}
        </button>
      </li>
    </ul>
  </div>
</template>
