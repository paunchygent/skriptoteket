<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";

import { useEditorCompareData, type WorkingCopyProvider } from "../../composables/editor/useEditorCompareData";
import type { EditorCompareTarget } from "../../composables/editor/useEditorCompareState";
import type { VirtualFileId, VirtualFileTextMap } from "../../composables/editor/virtualFiles";
import { VIRTUAL_FILE_IDS } from "../../composables/editor/virtualFiles";
import VirtualFileDiffViewer from "./diff/VirtualFileDiffViewer.vue";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];
type VersionState = components["schemas"]["VersionState"];

type EditorComparePanelProps = {
  versions: EditorVersionSummary[];
  baseVersion: EditorVersionSummary | null;
  baseFiles: VirtualFileTextMap;
  compareTarget: EditorCompareTarget | null;
  activeFileId: VirtualFileId | null;
  baseIsDirty: boolean;
  workingCopyProvider?: WorkingCopyProvider | null;
};

const props = defineProps<EditorComparePanelProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "updateCompareVersionId", versionId: string): void;
  (event: "updateActiveFileId", fileId: VirtualFileId): void;
}>();

const { compareEditor, compareFiles, isLoading, errorMessage } = useEditorCompareData(
  computed(() => props.compareTarget),
  { workingCopyProvider: props.workingCopyProvider ?? undefined },
);

function versionLabel(state: VersionState): string {
  const labels: Record<VersionState, string> = {
    draft: "Utkast",
    in_review: "Granskning",
    active: "Publicerad",
    archived: "Arkiverad",
  };
  return labels[state] ?? state;
}

function shortVersionLabel(version: EditorVersionSummary | null, fallback: string): string {
  if (!version) return fallback;
  return `v${version.version_number} · ${versionLabel(version.state)}`;
}

const baseLabel = computed(() => {
  const label = shortVersionLabel(props.baseVersion, "Nuvarande");
  return props.baseIsDirty ? `${label} (osparad)` : label;
});

const compareLabel = computed(() => {
  if (props.compareTarget?.kind === "working") {
    return "Lokalt arbetsexemplar";
  }
  const version = compareEditor.value?.selected_version ?? null;
  return shortVersionLabel(version, "Jämförelse");
});

const compareVersionId = computed(() => {
  const target = props.compareTarget;
  if (target?.kind !== "version") return "";
  return target.versionId;
});

const selectableCompareVersions = computed(() =>
  props.versions.filter((version) => version.id !== props.baseVersion?.id),
);

const isWorkingCompare = computed(() => props.compareTarget?.kind === "working");

const diffItems = computed(() => {
  if (!compareFiles.value) return [];
  return VIRTUAL_FILE_IDS.map((virtualFileId) => ({
    virtualFileId,
    beforeText: compareFiles.value![virtualFileId],
    afterText: props.baseFiles[virtualFileId],
  }));
});
</script>

<template>
  <div class="space-y-3">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="space-y-1 min-w-0">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
          Jämför versioner
        </h2>
        <p class="text-sm text-navy/70">
          {{ compareLabel }} → {{ baseLabel }}
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <template v-if="isWorkingCompare">
          <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Lokalt arbetsexemplar
          </span>
        </template>
        <template v-else>
          <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Jämför med
          </label>
          <select
            class="border border-navy bg-white px-3 py-2 text-xs text-navy shadow-brutal-sm"
            :value="compareVersionId"
            @change="emit('updateCompareVersionId', ($event.target as HTMLSelectElement).value)"
          >
            <option
              value=""
              disabled
            >
              Välj version...
            </option>
            <option
              v-for="version in selectableCompareVersions"
              :key="version.id"
              :value="version.id"
            >
              v{{ version.version_number }} · {{ versionLabel(version.state) }}
            </option>
          </select>
        </template>

        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="emit('close')"
        >
          Stäng jämförelse
        </button>
      </div>
    </div>

    <div
      v-if="isLoading"
      class="flex items-center gap-3 p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Laddar jämförelseversion...</span>
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>

    <VirtualFileDiffViewer
      v-else
      :items="diffItems"
      :active-file-id="props.activeFileId"
      :before-label="compareLabel"
      :after-label="baseLabel"
      @update:active-file-id="emit('updateActiveFileId', $event)"
    />
  </div>
</template>
