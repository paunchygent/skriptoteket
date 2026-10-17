<script setup lang="ts">
import { computed } from "vue";
import { UiDenseActionButton, UiDenseSpinner } from "../ui";
import type { components } from "../../api/openapi";

import {
  bundleDiffItems,
  type BundleFiles,
  type EditorFileDiffItem,
  type EditorFileId,
} from "../../composables/editor/bundleFiles";
import { useEditorCompareData, type WorkingCopyProvider } from "../../composables/editor/useEditorCompareData";
import type { EditorCompareTarget } from "../../composables/editor/useEditorCompareState";
import type { VirtualFileTextMap } from "../../composables/editor/virtualFiles";
import { VIRTUAL_DIFF_FILE_IDS } from "../../composables/editor/virtualFiles";
import VirtualFileDiffViewer from "./diff/VirtualFileDiffViewer.vue";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];
type VersionState = components["schemas"]["VersionState"];

type EditorComparePanelProps = {
  versions: EditorVersionSummary[];
  baseVersion: EditorVersionSummary | null;
  baseFiles: VirtualFileTextMap;
  baseBundleFiles: BundleFiles;
  compareTarget: EditorCompareTarget | null;
  activeFileId: EditorFileId | null;
  baseIsDirty: boolean;
  canCompareWorkingCopy: boolean;
  workingCopyProvider?: WorkingCopyProvider | null;
};

const props = defineProps<EditorComparePanelProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "updateCompareTargetValue", value: string): void;
  (event: "updateActiveFileId", fileId: EditorFileId): void;
}>();

const { compareEditor, compareFiles, compareBundleFiles, isLoading, errorMessage } = useEditorCompareData(
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

const diffItems = computed<EditorFileDiffItem[]>(() => {
  if (!compareFiles.value) return [];
  const virtualItems: EditorFileDiffItem[] = VIRTUAL_DIFF_FILE_IDS.map((virtualFileId) => ({
    virtualFileId,
    beforeText: compareFiles.value![virtualFileId],
    afterText: props.baseFiles[virtualFileId],
  }));
  return [...virtualItems, ...bundleDiffItems(compareBundleFiles.value ?? {}, props.baseBundleFiles)];
});
</script>

<template>
  <div class="flex flex-col min-h-0 gap-3 h-full">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="text-sm text-navy/70">
          {{ compareLabel }} → {{ baseLabel }}
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <label class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
          Diff mot
        </label>
        <select
          class="h-[28px] border border-navy/30 bg-panel px-2.5 text-[11px] text-navy shadow-none leading-none"
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

        <UiDenseActionButton
          label="Stäng diff"
          @click="emit('close')"
        />
      </div>
    </div>

    <div class="flex-1 min-h-0">
      <div
        v-if="isLoading"
        class="h-full w-full flex items-center justify-center gap-3 p-4 panel-inset text-sm text-navy/70"
        data-editor-state="diff-loading"
      >
        <UiDenseSpinner :size="16" />
        <span>Laddar diffversion...</span>
      </div>

      <div
        v-else-if="errorMessage"
        class="h-full w-full flex items-center justify-center p-4 panel-inset text-sm text-critical"
        data-editor-state="diff-error"
      >
        {{ errorMessage }}
      </div>

      <VirtualFileDiffViewer
        v-else
        class="h-full"
        :items="diffItems"
        :active-file-id="props.activeFileId"
        :before-label="compareLabel"
        :after-label="baseLabel"
        @update:active-file-id="emit('updateActiveFileId', $event)"
      />
    </div>
  </div>
</template>
