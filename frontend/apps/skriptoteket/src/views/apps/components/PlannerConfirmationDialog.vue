<script setup lang="ts">
/**
 * Reusable planner confirmation dialog.
 *
 * This component keeps destructive confirmations visually consistent across
 * Klassrumskartan without relying on browser-native confirm dialogs.
 */

defineProps<{
  eyebrow: string;
  title: string;
  message: string;
  confirmLabel: string;
  isSubmitting?: boolean;
  errorMessage?: string | null;
}>();

const emit = defineEmits<{
  (e: "cancel"): void;
  (e: "confirm"): void;
}>();
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-y-auto p-4">
    <button
      type="button"
      aria-label="Stäng bekräftelse"
      class="fixed inset-0 bg-navy/70"
      @click="emit('cancel')"
    />
    <div class="relative flex min-h-full items-center justify-center py-4">
      <div class="w-full max-w-[32rem] border border-navy bg-white p-6 shadow-brutal-sm">
        <div class="space-y-2">
          <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-burgundy">
            {{ eyebrow }}
          </p>
          <h2 class="font-serif text-2xl text-navy">
            {{ title }}
          </h2>
          <p class="text-sm leading-relaxed text-navy/70">
            {{ message }}
          </p>
        </div>

        <div
          v-if="errorMessage"
          class="system-message system-message-error mt-4"
        >
          <div class="system-message-content">
            {{ errorMessage }}
          </div>
        </div>

        <div class="mt-6 flex flex-wrap items-center justify-end gap-2 border-t border-navy/15 pt-4">
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-white shadow-none"
            :disabled="isSubmitting"
            @click="emit('cancel')"
          >
            Avbryt
          </button>
          <button
            type="button"
            class="btn-ghost border-burgundy/30 bg-white text-burgundy shadow-none disabled:text-burgundy/50"
            :disabled="isSubmitting"
            data-test="confirm-dialog-confirm"
            @click="emit('confirm')"
          >
            {{ isSubmitting ? "Arbetar..." : confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
