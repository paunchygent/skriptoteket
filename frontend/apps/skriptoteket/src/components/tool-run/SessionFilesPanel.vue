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
  density?: "default" | "compact";
  canReuse?: boolean;
  canClear?: boolean;
  helperText?: string | null;
}>(), {
  density: "default",
  canReuse: true,
  canClear: true,
  helperText: null,
});

const emit = defineEmits<{
  (e: "update:mode", value: SessionFilesMode): void;
}>();

const isCompact = computed(() => props.density === "compact");
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
  <div
    :class="[
      isCompact
        ? 'border border-navy/20 bg-white shadow-brutal-sm'
        : 'border border-navy bg-white shadow-brutal-sm',
    ]"
  >
    <div
      :class="[
        'px-3 py-2 border-b border-navy/20',
        isCompact ? 'flex items-center justify-between gap-3' : '',
      ]"
    >
      <h3
        :class="[
          isCompact
            ? 'text-[10px] font-semibold uppercase tracking-wide text-navy/60'
            : 'text-xs font-semibold uppercase tracking-wide text-navy/70',
        ]"
      >
        Sparade filer
      </h3>
      <p
        v-if="!isCompact"
        class="text-xs text-navy/60"
      >
        Används endast när du kör utan att ladda upp nya filer.
      </p>
    </div>

    <div class="px-3 py-2">
      <ul
        v-if="files.length > 0"
        :class="[isCompact ? 'space-y-1 text-[11px] text-navy/70' : 'space-y-1 text-xs text-navy/70']"
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
        :class="[isCompact ? 'text-[11px] text-navy/60' : 'text-xs text-navy/60']"
      >
        Inga sparade filer.
      </p>
    </div>

    <div class="px-3 py-2 border-t border-navy/20 flex flex-wrap gap-3 items-center">
      <label
        :class="[
          'flex items-center gap-2 font-semibold text-navy/70',
          isCompact ? 'text-[11px]' : 'text-xs',
        ]"
      >
        <input
          type="checkbox"
          :class="[isCompact ? 'accent-navy h-3.5 w-3.5' : 'accent-navy']"
          :checked="isReuse"
          :disabled="!canReuse"
          @change="toggleReuse"
        >
        Återanvänd sparade filer
      </label>

      <button
        type="button"
        :class="[
          isCompact
            ? 'btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none'
            : 'btn-ghost px-3 py-1 text-xs',
        ]"
        :disabled="!canClear"
        @click="toggleClear"
      >
        Rensa sparade filer
      </button>

      <span
        v-if="isClear"
        :class="[isCompact ? 'text-[10px] font-semibold text-burgundy' : 'text-xs font-semibold text-burgundy']"
      >
        Rensar vid nästa körning.
      </span>
    </div>

    <p
      v-if="helperText"
      :class="[isCompact ? 'px-3 pb-2 text-[10px] text-navy/60' : 'px-3 pb-2 text-xs text-navy/60']"
    >
      {{ helperText }}
    </p>
  </div>
</template>
