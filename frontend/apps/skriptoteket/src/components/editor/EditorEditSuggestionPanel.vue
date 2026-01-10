<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{
  instruction: string;
  suggestion: string;
  isLoading: boolean;
  error: string | null;
  isReadOnly: boolean;
  canApply: boolean;
}>();

const emit = defineEmits<{
  (event: "request"): void;
  (event: "apply"): void;
  (event: "clear"): void;
  (event: "update:instruction", value: string): void;
}>();

const requestLabel = computed(() => (props.isLoading ? "Föreslår..." : "Föreslå ändring"));
</script>

<template>
  <div class="p-4 panel-inset-canvas space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
        AI-redigering
      </h3>
      <span class="text-xs text-navy/60">Markera kod i editorn och beskriv ändringen</span>
    </div>

    <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div class="space-y-2">
        <label
          for="ai-edit-instruction"
          class="text-xs font-semibold uppercase tracking-wide text-navy/70"
        >
          Instruktion
        </label>
        <textarea
          id="ai-edit-instruction"
          :value="instruction"
          rows="4"
          class="w-full border border-navy/30 bg-white px-3 py-2 text-sm text-navy shadow-none"
          placeholder="T.ex. förenkla logiken, lägg till felhantering..."
          :disabled="isReadOnly"
          @input="emit('update:instruction', ($event.target as HTMLTextAreaElement).value)"
        />
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="btn-ghost h-[28px] px-3 py-1 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas"
            :disabled="isReadOnly || isLoading"
            @click="emit('request')"
          >
            {{ requestLabel }}
          </button>
          <button
            type="button"
            class="btn-ghost h-[28px] px-3 py-1 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas"
            :disabled="isReadOnly || isLoading"
            @click="emit('clear')"
          >
            Rensa
          </button>
        </div>
      </div>

      <div class="space-y-2">
        <label
          for="ai-edit-suggestion"
          class="text-xs font-semibold uppercase tracking-wide text-navy/70"
        >
          Förslag
        </label>
        <textarea
          id="ai-edit-suggestion"
          :value="suggestion"
          rows="4"
          class="w-full border border-navy/30 bg-white px-3 py-2 text-sm font-mono text-navy shadow-none"
          placeholder="Förslag visas här"
          readonly
        />
        <button
          type="button"
          class="btn-ghost h-[28px] px-3 py-1 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] bg-navy text-canvas border-navy shadow-none"
          :disabled="!canApply"
          @click="emit('apply')"
        >
          Använd förslag
        </button>
      </div>
    </div>

    <p
      v-if="error"
      class="text-sm text-burgundy"
    >
      {{ error }}
    </p>
  </div>
</template>
