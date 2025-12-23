<script setup lang="ts">
import type { StepResult } from "../../composables/tools/useToolRun";

defineProps<{
  steps: StepResult[];
  currentStepNumber: number;
}>();

const emit = defineEmits<{
  (e: "select-step", step: StepResult): void;
}>();

function stepStatusClass(step: StepResult): string {
  switch (step.status) {
    case "completed":
      return "bg-success text-white border-success";
    case "current":
      return "bg-burgundy text-canvas border-burgundy";
    default:
      return "bg-canvas text-navy/50 border-navy/30";
  }
}

function connectorClass(step: StepResult): string {
  return step.status === "completed" ? "bg-success" : "bg-navy/20";
}
</script>

<template>
  <div
    v-if="steps.length > 0"
    class="flex items-center gap-2"
  >
    <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">
      Steg
    </span>

    <div class="flex items-center gap-1">
      <template
        v-for="(step, index) in steps"
        :key="step.id"
      >
        <div
          v-if="index > 0"
          class="h-0.5 w-4 sm:w-6"
          :class="connectorClass(step)"
        />

        <button
          type="button"
          class="flex items-center justify-center w-6 h-6 text-xs font-bold border-2 rounded-full transition-colors"
          :class="[
            stepStatusClass(step),
            step.status === 'completed' ? 'cursor-pointer hover:ring-2 hover:ring-burgundy/30' : 'cursor-default',
          ]"
          :disabled="step.status !== 'completed'"
          :title="step.label"
          @click="step.status === 'completed' && emit('select-step', step)"
        >
          <template v-if="step.status === 'completed'">
            <svg
              class="w-3 h-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="3"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </template>
          <template v-else>
            {{ step.stepNumber }}
          </template>
        </button>
      </template>

      <template v-if="currentStepNumber > steps.length">
        <div
          v-if="steps.length > 0"
          class="h-0.5 w-4 sm:w-6 bg-navy/20"
        />
        <div
          class="flex items-center justify-center w-6 h-6 text-xs font-bold border-2 rounded-full bg-burgundy text-canvas border-burgundy"
        >
          {{ currentStepNumber }}
        </div>
      </template>
    </div>
  </div>
</template>
