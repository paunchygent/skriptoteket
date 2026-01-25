<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{
  isRunning: boolean;
  hasResults: boolean;
  hasSettings: boolean;
  isSettingsOpen: boolean;
  canRun?: boolean;
}>(), {
  canRun: undefined,
});

const emit = defineEmits<{
  (e: "run"): void;
  (e: "clear"): void;
  (e: "toggle-settings"): void;
}>();

const canRun = computed(() => props.canRun ?? false);
</script>

<template>
  <div class="flex flex-col gap-3 sm:flex-row sm:items-stretch">
    <button
      type="button"
      :disabled="!canRun || isRunning"
      class="btn-ghost min-w-[120px] h-[32px] px-3 py-1 text-xs font-semibold tracking-wide border-navy/30 bg-canvas shadow-none"
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
        'btn-ghost h-[32px] px-3 py-1 text-xs font-semibold tracking-wide border-navy/30 shadow-none',
        isSettingsOpen ? 'bg-canvas text-navy' : 'bg-white text-navy/70',
      ]"
      @click="emit('toggle-settings')"
    >
      ⚙ Inställningar
    </button>

    <button
      v-if="hasResults"
      type="button"
      class="btn-ghost h-[32px] px-3 py-1 text-xs font-semibold tracking-wide border-navy/30 bg-white shadow-none"
      @click="emit('clear')"
    >
      Rensa
    </button>
  </div>
</template>
