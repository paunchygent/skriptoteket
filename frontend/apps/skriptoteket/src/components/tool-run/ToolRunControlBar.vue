<script setup lang="ts">
import { computed } from "vue";

import { IconSettings } from "../icons";
import { UiDenseActionButton } from "../ui";

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
    <UiDenseActionButton
      label="Kör"
      class="min-w-[120px]"
      :disabled="!canRun || isRunning"
      :busy="isRunning"
      reserve-busy-slot
      @click="emit('run')"
    />

    <UiDenseActionButton
      v-if="hasSettings"
      label="Inställningar"
      :expanded="isSettingsOpen"
      @click="emit('toggle-settings')"
    >
      <template #leading>
        <IconSettings :size="isCompact ? 14 : 16" />
      </template>
    </UiDenseActionButton>

    <UiDenseActionButton
      v-if="hasResults"
      label="Rensa"
      @click="emit('clear')"
    />
  </div>
</template>
