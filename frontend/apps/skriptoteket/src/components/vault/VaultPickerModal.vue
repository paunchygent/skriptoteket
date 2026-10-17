<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";

import { UiDenseIconButton, UiGlyph } from "../ui/shared";

import VaultPanel from "./VaultPanel.vue";

const props = withDefaults(defineProps<{
  isOpen: boolean;
  title?: string;
  selectedRefs: string[];
  maxSelected: number;
  confirmLabel?: string;
  isReadOnly?: boolean;
}>(), {
  title: "Välj filer från Mina filer",
  confirmLabel: "Bekräfta",
  isReadOnly: false,
});

const emit = defineEmits<{
  close: [];
  confirm: [value: string[]];
}>();

const draft = ref<string[]>([]);
const titleId = useId();

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      draft.value = [...props.selectedRefs];
    }
  },
  { immediate: true },
);

const selectionLabel = computed(() => {
  const count = draft.value.length;
  if (count === 0) return "Inga valda";
  return count === 1 ? "1 vald" : `${count} valda`;
});

function updateDraft(value: string[]): void {
  draft.value = value;
}

function onConfirm(): void {
  emit("confirm", [...draft.value]);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        @click.self="emit('close')"
      >
        <div class="relative w-full max-w-3xl mx-4 p-6 rounded-[var(--huleedu-panel-radius)] bg-modal border border-[var(--huleedu-panel-border)] shadow-md">
          <UiDenseIconButton
            label="Stäng"
            class="absolute top-3 right-3"
            @click="emit('close')"
          >
            <UiGlyph
              meaning="close"
              :size="16"
            />
          </UiDenseIconButton>

          <div class="flex items-start justify-between gap-4">
            <div>
              <h2
                :id="titleId"
                class="text-xl font-semibold text-navy"
              >
                {{ title }}
              </h2>
              <p class="mt-1 text-sm text-navy/70">
                {{ selectionLabel }}
              </p>
            </div>
          </div>

          <div class="mt-5">
            <VaultPanel
              mode="picker"
              :model-value="draft"
              :max-selected="maxSelected"
              :is-read-only="isReadOnly"
              @update:model-value="updateDraft"
            />
          </div>

          <div class="mt-5 flex flex-wrap gap-3 justify-end">
            <button
              type="button"
              class="btn-ghost"
              @click="emit('close')"
            >
              Avbryt
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="isReadOnly"
              @click="onConfirm"
            >
              {{ confirmLabel }}
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
