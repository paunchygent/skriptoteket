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
  canCompareWorkingCopy: boolean;
  workingCopyProvider?: WorkingCopyProvider | null;
};

const props = defineProps<EditorComparePanelProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "updateCompareTargetValue", value: string): void;
  (event: "updateActiveFileId", fileId: VirtualFileId): void;
}>();

const { compareEditor, compareFiles, isLoading, errorMessage } = useEditorCompareData(
  computed(() => props.compareTarget),
  { workingCopyProvider: props.workingCopyProvider ?? undefined },
);

function versionLabel(state: VersionState): string {
  const labels: Record<VersionState, string> = {
    draft: "Arbetsversion",
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
  return shortVersionLabel(version, "Diff");
});

const compareTargetValue = computed(() => {
  const target = props.compareTarget;
  if (!target) return "";
  return target.kind === "working" ? "working" : target.versionId;
});

const selectableCompareVersions = computed(() =>
  props.versions.filter((version) => version.id !== props.baseVersion?.id),
);

const isWorkingCompare = computed(() => props.compareTarget?.kind === "working");
const showWorkingCompareOption = computed(
  () => isWorkingCompare.value || props.canCompareWorkingCopy,
);
const workingCompareLabel = computed(() =>
  props.canCompareWorkingCopy ? "Lokalt arbetsexemplar" : "Lokalt arbetsexemplar (saknas)",
);

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
  <div class="flex flex-col min-h-0 gap-3">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="text-sm text-navy/70">
          {{ compareLabel }} → {{ baseLabel }}
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Diff mot
        </label>
        <select
          class="border border-navy bg-white px-3 py-2 text-xs text-navy shadow-brutal-sm"
          :value="compareTargetValue"
          @change="emit('updateCompareTargetValue', ($event.target as HTMLSelectElement).value)"
        >
          <option
            v-if="showWorkingCompareOption"
            value="working"
            :disabled="!props.canCompareWorkingCopy"
          >
            {{ workingCompareLabel }}
          </option>
          <option
            v-for="version in selectableCompareVersions"
            :key="version.id"
            :value="version.id"
          >
            v{{ version.version_number }} · {{ versionLabel(version.state) }}
          </option>
        </select>

        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="emit('close')"
        >
          Stäng diff
        </button>
      </div>
    </div>

    <div
      v-if="isLoading"
      class="flex items-center gap-3 p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Laddar diffversion...</span>
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>

    <VirtualFileDiffViewer
      v-else
      class="flex-1 min-h-0"
      :items="diffItems"
      :active-file-id="props.activeFileId"
      :before-label="compareLabel"
      :after-label="baseLabel"
      @update:active-file-id="emit('updateActiveFileId', $event)"
    />
  </div>
</template>
