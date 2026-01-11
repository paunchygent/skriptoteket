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
    class="border border-navy/30 bg-canvas/30 px-3 py-2"
  >
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="min-w-0 space-y-0.5">
        <p class="text-[11px] text-navy/70">
          <span class="font-semibold text-navy">Lokalt arbetsexemplar hittades.</span>
          Osparade &auml;ndringar finns sparade lokalt.
        </p>
        <p
          v-if="updatedAtLabel"
          class="text-[10px] text-navy/60"
        >
          Senast sparat: {{ updatedAtLabel }}
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
          @click="emit('restore')"
        >
          &Aring;terst&auml;ll
        </button>
        <button
          type="button"
          class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
          @click="emit('discard')"
        >
          Kasta
        </button>
        <button
          type="button"
          class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
          :disabled="props.diffItems.length === 0"
          @click="openDiff"
        >
          Visa diff
        </button>
      </div>
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
        <div
          class="relative w-full max-w-6xl mx-4 p-4 bg-canvas border border-navy shadow-brutal flex flex-col min-h-0 h-[min(760px,calc(100vh-3rem))]"
        >
          <button
            type="button"
            class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
            @click="closeDiff"
          >
            &times;
          </button>

          <div class="flex-1 min-h-0 overflow-hidden">
            <VirtualFileDiffViewer
              :items="props.diffItems"
              :active-file-id="activeFileId"
              before-label="Serverversion"
              after-label="Lokalt arbetsexemplar"
              @update:active-file-id="activeFileId = $event"
            />
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
