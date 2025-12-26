<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{
  selectedFiles: File[];
  isRunning: boolean;
  hasResults: boolean;
  hasSettings: boolean;
  isSettingsOpen: boolean;
  showFilePicker?: boolean;
  fileLabel?: string;
  fileAccept?: string;
  fileMultiple?: boolean;
  fileError?: string | null;
  canRun?: boolean;
}>(), {
  showFilePicker: true,
  fileLabel: "Filer",
  fileAccept: undefined,
  fileMultiple: true,
  fileError: null,
  canRun: undefined,
});

const emit = defineEmits<{
  (e: "files-selected", files: File[]): void;
  (e: "run"): void;
  (e: "clear"): void;
  (e: "toggle-settings"): void;
}>();

const hasFiles = computed(() => props.selectedFiles.length > 0);
const canRun = computed(() => props.canRun ?? hasFiles.value);
const fileCountLabel = computed(() => {
  if (!hasFiles.value) return "Inga filer valda";
  return `${props.selectedFiles.length} fil(er) valda`;
});

function onFilesSelected(event: Event): void {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    emit("files-selected", Array.from(target.files));
  }
}
</script>

<template>
  <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
    <div
      v-if="showFilePicker"
      class="flex-1 space-y-1"
    >
      <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
        {{ fileLabel }}
      </label>
      <div class="flex items-center gap-3 w-full border border-navy bg-canvas px-3 py-2">
        <label
          class="btn-cta shrink-0 px-3 py-1 text-xs font-semibold tracking-wide"
        >
          Välj filer
          <input
            type="file"
            :multiple="fileMultiple"
            :accept="fileAccept"
            class="sr-only"
            @change="onFilesSelected"
          >
        </label>
        <span class="text-sm text-navy/60 truncate">
          {{ fileCountLabel }}
        </span>
      </div>
      <p
        v-if="fileError"
        class="text-xs font-semibold text-burgundy"
      >
        {{ fileError }}
      </p>
    </div>

    <button
      type="button"
      :disabled="!canRun || isRunning"
      class="btn-cta min-w-[80px]"
      @click="emit('run')"
    >
      <span
        v-if="isRunning"
        class="inline-block w-3 h-3 border-2 border-canvas/30 border-t-canvas rounded-full animate-spin"
      />
      <span v-else>Kör</span>
    </button>

    <button
      v-if="hasSettings"
      type="button"
      :class="isSettingsOpen ? 'btn-primary' : 'btn-ghost'"
      @click="emit('toggle-settings')"
    >
      ⚙ Inställningar
    </button>

    <button
      v-if="hasResults"
      type="button"
      class="btn-ghost"
      @click="emit('clear')"
    >
      Rensa
    </button>
  </div>
</template>
