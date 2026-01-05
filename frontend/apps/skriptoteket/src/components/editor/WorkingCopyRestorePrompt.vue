<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { VirtualFileId } from "../../composables/editor/virtualFiles";
import VirtualFileDiffViewer from "./diff/VirtualFileDiffViewer.vue";

type DiffItem = {
  virtualFileId: VirtualFileId;
  beforeText: string;
  afterText: string;
};

const props = defineProps<{
  isOpen: boolean;
  diffItems: DiffItem[];
  updatedAt: number | null;
}>();

const emit = defineEmits<{
  (event: "restore"): void;
  (event: "discard"): void;
}>();

const isDiffOpen = ref(false);
const activeFileId = ref<VirtualFileId | null>(null);

const updatedAtLabel = computed(() => {
  if (!props.updatedAt) return null;
  const date = new Date(props.updatedAt);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
});

function openDiff(): void {
  if (props.diffItems.length === 0) return;
  isDiffOpen.value = true;
}

function closeDiff(): void {
  isDiffOpen.value = false;
}

watch(
  () => props.isOpen,
  (isOpen) => {
    if (!isOpen) {
      isDiffOpen.value = false;
    }
  },
);
</script>

<template>
  <div
    v-if="props.isOpen"
    class="border border-warning bg-white shadow-brutal-sm p-4 space-y-3"
  >
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="space-y-1 min-w-0">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-warning">
          Lokalt arbetsexemplar hittades
        </h2>
        <p class="text-sm text-navy/70">
          Det finns osparade ändringar sparade lokalt för det här verktyget.
        </p>
        <p
          v-if="updatedAtLabel"
          class="text-xs text-navy/60"
        >
          Senast sparat: {{ updatedAtLabel }}
        </p>
      </div>

      <button
        type="button"
        class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
        :disabled="props.diffItems.length === 0"
        @click="openDiff"
      >
        Visa diff
      </button>
    </div>

    <div class="flex flex-wrap gap-2">
      <button
        type="button"
        class="btn-primary"
        @click="emit('restore')"
      >
        Återställ lokalt
      </button>
      <button
        type="button"
        class="btn-ghost"
        @click="emit('discard')"
      >
        Kasta lokalt
      </button>
    </div>
  </div>

  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isDiffOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
        role="dialog"
        aria-modal="true"
        @click.self="closeDiff"
      >
        <div class="relative w-full max-w-6xl mx-4 p-4 bg-canvas border border-navy shadow-brutal">
          <button
            type="button"
            class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
            @click="closeDiff"
          >
            &times;
          </button>

          <VirtualFileDiffViewer
            :items="props.diffItems"
            :active-file-id="activeFileId"
            before-label="Serverversion"
            after-label="Lokalt arbetsexemplar"
            @update:active-file-id="activeFileId = $event"
          />
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
