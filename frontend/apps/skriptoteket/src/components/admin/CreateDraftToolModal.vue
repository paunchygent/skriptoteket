<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import SystemMessage from "../ui/SystemMessage.vue";

type CreateDraftToolModalProps = {
  isOpen: boolean;
  title: string;
  summary: string;
  error: string | null;
  isSubmitting: boolean;
};

const props = defineProps<CreateDraftToolModalProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "submit"): void;
  (event: "update:title", value: string): void;
  (event: "update:summary", value: string): void;
  (event: "update:error", value: string | null): void;
}>();

const titleInputRef = ref<HTMLInputElement | null>(null);

watch(
  () => props.isOpen,
  (isOpen) => {
    if (!isOpen) return;
    void nextTick().then(() => {
      titleInputRef.value?.focus();
    });
  },
);
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-tool-dialog-title"
        :aria-describedby="error ? 'create-tool-dialog-error' : undefined"
        @click.self="emit('close')"
      >
        <div class="relative w-full max-w-lg mx-4 p-6 bg-canvas border border-navy shadow-brutal">
          <button
            type="button"
            class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
            :disabled="isSubmitting"
            @click="emit('close')"
          >
            &times;
          </button>

          <h2
            id="create-tool-dialog-title"
            class="text-xl font-semibold text-navy"
          >
            Skapa nytt verktyg
          </h2>
          <p class="mt-2 text-sm text-navy/70">
            Skapa ett utkast. Du kan lägga till kod och publicera senare.
          </p>

          <div class="mt-5 space-y-4">
            <div class="space-y-1">
              <label class="block text-xs font-semibold uppercase tracking-wide text-navy/70">
                Titel
              </label>
              <input
                ref="titleInputRef"
                :value="title"
                type="text"
                class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
                placeholder="T.ex. Matteprovsgenerator"
                :disabled="isSubmitting"
                @input="emit('update:title', ($event.target as HTMLInputElement).value)"
              >
            </div>

            <div class="space-y-1">
              <label class="block text-xs font-semibold uppercase tracking-wide text-navy/70">
                Sammanfattning (valfritt)
              </label>
              <textarea
                :value="summary"
                rows="3"
                class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
                placeholder="Kort beskrivning..."
                :disabled="isSubmitting"
                @input="emit('update:summary', ($event.target as HTMLTextAreaElement).value)"
              />
            </div>

            <SystemMessage
              id="create-tool-dialog-error"
              :model-value="error"
              variant="error"
              @update:model-value="emit('update:error', $event)"
            />
          </div>

          <div class="mt-6 flex flex-wrap justify-end gap-3">
            <button
              type="button"
              class="btn-ghost"
              :disabled="isSubmitting"
              @click="emit('close')"
            >
              Avbryt
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="isSubmitting"
              @click="emit('submit')"
            >
              {{ isSubmitting ? "Skapar..." : "Skapa" }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
