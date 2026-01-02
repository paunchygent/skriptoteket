<script setup lang="ts">
import { computed } from "vue";

type SessionFilesMode = "none" | "reuse" | "clear";

type SessionFileInfo = {
  name: string;
  bytes: number;
};

const props = withDefaults(defineProps<{
  files: SessionFileInfo[];
  mode: SessionFilesMode;
  canReuse?: boolean;
  canClear?: boolean;
  helperText?: string | null;
}>(), {
  canReuse: true,
  canClear: true,
  helperText: null,
});

const emit = defineEmits<{
  (e: "update:mode", value: SessionFilesMode): void;
}>();

const isReuse = computed(() => props.mode === "reuse");
const isClear = computed(() => props.mode === "clear");

function toggleReuse(): void {
  emit("update:mode", isReuse.value ? "none" : "reuse");
}

function toggleClear(): void {
  emit("update:mode", isClear.value ? "none" : "clear");
}
</script>

<template>
  <div class="border border-navy bg-white shadow-brutal-sm">
    <div class="px-3 py-2 border-b border-navy/20">
      <h3 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
        Sparade filer
      </h3>
      <p class="text-xs text-navy/60">
        Används endast när du kör utan att ladda upp nya filer.
      </p>
    </div>

    <div class="px-3 py-2">
      <ul
        v-if="files.length > 0"
        class="space-y-1 text-xs text-navy/70"
      >
        <li
          v-for="file in files"
          :key="file.name"
          class="font-mono truncate"
        >
          {{ file.name }}
        </li>
      </ul>
      <p
        v-else
        class="text-xs text-navy/60"
      >
        Inga sparade filer.
      </p>
    </div>

    <div class="px-3 py-2 border-t border-navy/20 flex flex-wrap gap-3 items-center">
      <label class="flex items-center gap-2 text-xs font-semibold text-navy/70">
        <input
          type="checkbox"
          class="accent-navy"
          :checked="isReuse"
          :disabled="!canReuse"
          @change="toggleReuse"
        >
        Återanvänd sparade filer
      </label>

      <button
        type="button"
        class="btn-ghost px-3 py-1 text-xs"
        :disabled="!canClear"
        @click="toggleClear"
      >
        Rensa sparade filer
      </button>

      <span
        v-if="isClear"
        class="text-xs font-semibold text-burgundy"
      >
        Rensar vid nästa körning.
      </span>
    </div>

    <p
      v-if="helperText"
      class="px-3 pb-2 text-xs text-navy/60"
    >
      {{ helperText }}
    </p>
  </div>
</template>
