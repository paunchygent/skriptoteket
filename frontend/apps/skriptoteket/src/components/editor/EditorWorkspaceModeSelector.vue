<script setup lang="ts">
type EditorWorkspaceMode = "source" | "diff" | "metadata" | "test";

type EditorWorkspaceModeSelectorProps = {
  activeMode: EditorWorkspaceMode;
  canEnterDiff: boolean;
  openCompareTitle: string;
};

const props = defineProps<EditorWorkspaceModeSelectorProps>();

const emit = defineEmits<{
  (event: "select", mode: EditorWorkspaceMode): void;
}>();

const modeButtonBase =
  "inline-flex items-center justify-center px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border border-navy/30 transition-colors";
const modeButtonActive = "bg-navy text-canvas border-navy";
const modeButtonInactive = "bg-canvas text-navy/70";
const modeButtonDisabled = "opacity-40 cursor-not-allowed";
</script>

<template>
  <div class="inline-flex items-center gap-1 rounded-[4px] border border-navy/30 bg-canvas p-1">
    <button
      type="button"
      :class="[modeButtonBase, props.activeMode === 'source' ? modeButtonActive : modeButtonInactive]"
      :aria-pressed="props.activeMode === 'source'"
      @click="emit('select', 'source')"
    >
      Källkod
    </button>
    <button
      type="button"
      :class="[
        modeButtonBase,
        props.activeMode === 'diff' ? modeButtonActive : modeButtonInactive,
        props.canEnterDiff ? '' : modeButtonDisabled,
      ]"
      :aria-pressed="props.activeMode === 'diff'"
      :disabled="!props.canEnterDiff && props.activeMode !== 'diff'"
      :title="props.openCompareTitle || undefined"
      @click="emit('select', 'diff')"
    >
      Diff
    </button>
    <button
      type="button"
      :class="[modeButtonBase, props.activeMode === 'metadata' ? modeButtonActive : modeButtonInactive]"
      :aria-pressed="props.activeMode === 'metadata'"
      @click="emit('select', 'metadata')"
    >
      Metadata
    </button>
    <button
      type="button"
      :class="[modeButtonBase, props.activeMode === 'test' ? modeButtonActive : modeButtonInactive]"
      :aria-pressed="props.activeMode === 'test'"
      @click="emit('select', 'test')"
    >
      Testk&ouml;r
    </button>
  </div>
</template>
