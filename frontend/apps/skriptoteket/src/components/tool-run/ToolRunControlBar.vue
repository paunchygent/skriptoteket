<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{
  isRunning: boolean;
  hasResults: boolean;
  hasSettings: boolean;
  isSettingsOpen: boolean;
  canRun?: boolean;
  density?: "default" | "compact";
}>(), {
  canRun: undefined,
  density: "default",
});

const emit = defineEmits<{
  (e: "run"): void;
  (e: "clear"): void;
  (e: "toggle-settings"): void;
}>();

const canRun = computed(() => props.canRun ?? false);
const isCompact = computed(() => props.density === "compact");
</script>

<template>
  <div :class="[isCompact ? 'flex flex-col gap-2 sm:flex-row sm:items-center' : 'flex flex-col gap-3 sm:flex-row sm:items-stretch']">
    <button
      type="button"
      :disabled="!canRun || isRunning"
      :class="[
        'btn-ghost min-w-[120px] border-navy/30 bg-canvas shadow-none',
        isCompact
          ? 'h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none'
          : 'h-[32px] px-3 py-1 text-xs font-semibold tracking-wide',
      ]"
      @click="emit('run')"
    >
      <span
        v-if="isRunning"
        class="inline-block w-3 h-3 border-2 border-navy/20 border-t-navy rounded-full animate-spin"
      />
      <span v-else>Kör</span>
    </button>

    <button
      v-if="hasSettings"
      type="button"
      :class="[
        'btn-ghost border-navy/30 shadow-none',
        isCompact
          ? 'h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none'
          : 'h-[32px] px-3 py-1 text-xs font-semibold tracking-wide',
        isSettingsOpen ? 'bg-canvas text-navy' : 'bg-white text-navy/70',
      ]"
      @click="emit('toggle-settings')"
    >
      ⚙ Inställningar
    </button>

    <button
      v-if="hasResults"
      type="button"
      :class="[
        'btn-ghost border-navy/30 bg-white shadow-none',
        isCompact
          ? 'h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none'
          : 'h-[32px] px-3 py-1 text-xs font-semibold tracking-wide',
      ]"
      @click="emit('clear')"
    >
      Rensa
    </button>
  </div>
</template>
