<script setup lang="ts">
import SystemMessage from "../ui/SystemMessage.vue";

type WorkflowActionMeta = {
  title: string;
  description?: string;
  confirmLabel: string;
  noteLabel: string;
  notePlaceholder: string;
};

type WorkflowActionModalProps = {
  isOpen: boolean;
  actionMeta: WorkflowActionMeta | null;
  note: string;
  showNoteField: boolean;
  error: string | null;
  isSubmitting: boolean;
  confirmButtonClass: string;
};

defineProps<WorkflowActionModalProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "submit"): void;
  (event: "update:note", value: string): void;
  (event: "update:error", value: string | null): void;
}>();
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isOpen && actionMeta"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workflow-modal-title"
        :aria-describedby="error ? 'workflow-modal-error' : undefined"
        @click.self="emit('close')"
      >
        <div class="relative w-full max-w-lg mx-4 p-6 bg-canvas border border-navy shadow-brutal">
          <button
            type="button"
            class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
            @click="emit('close')"
          >
            &times;
          </button>

          <h2
            id="workflow-modal-title"
            class="text-xl font-semibold text-navy"
          >
            {{ actionMeta.title }}
          </h2>

          <p
            v-if="actionMeta.description"
            class="mt-2 text-sm text-navy/70"
          >
            {{ actionMeta.description }}
          </p>

          <SystemMessage
            id="workflow-modal-error"
            class="mt-4"
            :model-value="error"
            variant="error"
            @update:model-value="emit('update:error', $event)"
          />

          <form
            class="mt-5 space-y-4"
            @submit.prevent="emit('submit')"
          >
            <div v-if="showNoteField">
              <label class="block text-sm font-semibold text-navy mb-1">
                {{ actionMeta.noteLabel }}
              </label>
              <textarea
                :value="note"
                rows="4"
                class="w-full px-3 py-2 border border-navy bg-white text-navy"
                :placeholder="actionMeta.notePlaceholder"
                :disabled="isSubmitting"
                @input="emit('update:note', ($event.target as HTMLTextAreaElement).value)"
              />
            </div>

            <div class="flex flex-wrap gap-3">
              <button
                type="button"
                class="btn-ghost"
                :disabled="isSubmitting"
                @click="emit('close')"
              >
                Avbryt
              </button>
              <button
                type="submit"
                :class="confirmButtonClass"
                :disabled="isSubmitting"
              >
                {{ isSubmitting ? "Arbetar..." : actionMeta.confirmLabel }}
              </button>
            </div>
          </form>
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
