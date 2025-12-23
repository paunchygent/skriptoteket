<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  selectedFiles: File[];
  isRunning: boolean;
  hasResults: boolean;
}>();

const emit = defineEmits<{
  (e: "files-selected", files: File[]): void;
  (e: "run"): void;
  (e: "clear"): void;
}>();

const hasFiles = computed(() => props.selectedFiles.length > 0);
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
    <div class="flex-1 space-y-1">
      <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
        Filer
      </label>
      <div class="flex items-center gap-3 w-full border border-navy bg-canvas px-3 py-2">
        <label
          class="shrink-0 px-3 py-1 text-xs font-semibold uppercase tracking-wide bg-burgundy text-canvas border border-navy cursor-pointer btn-secondary-hover transition-colors active:translate-x-0.5 active:translate-y-0.5"
        >
          Välj filer
          <input
            type="file"
            multiple
            class="sr-only"
            @change="onFilesSelected"
          >
        </label>
        <span class="text-sm text-navy/60 truncate">
          {{ fileCountLabel }}
        </span>
      </div>
    </div>

    <button
      type="button"
      :disabled="!hasFiles || isRunning"
      class="min-w-[80px] px-4 py-2 text-xs font-bold uppercase tracking-widest bg-burgundy text-canvas border border-navy shadow-brutal-sm btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
      @click="emit('run')"
    >
      <span
        v-if="isRunning"
        class="inline-block w-3 h-3 border-2 border-canvas/30 border-t-canvas rounded-full animate-spin"
      />
      <span v-else>Kör</span>
    </button>

    <button
      v-if="hasResults"
      type="button"
      class="px-4 py-2 text-xs font-bold uppercase tracking-widest bg-white text-navy border border-navy shadow-brutal-sm hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
      @click="emit('clear')"
    >
      Rensa
    </button>
  </div>
</template>
