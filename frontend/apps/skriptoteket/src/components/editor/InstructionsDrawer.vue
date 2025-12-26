<script setup lang="ts">
import { defineAsyncComponent, ref } from "vue";

const UiMarkdown = defineAsyncComponent(() => import("../ui/UiMarkdown.vue"));

type InstructionsDrawerProps = {
  isOpen: boolean;
  usageInstructions: string;
  isSaving: boolean;
};

defineProps<InstructionsDrawerProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "save"): void;
  (event: "update:usageInstructions", value: string): void;
}>();

const showPreview = ref(false);
</script>

<template>
  <!-- Mobile backdrop -->
  <Teleport to="body">
    <Transition name="drawer-backdrop">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-40 bg-navy/40 md:hidden"
        @click="emit('close')"
      />
    </Transition>
  </Teleport>

  <!-- Drawer -->
  <aside
    class="fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy shadow-brutal flex flex-col md:relative md:inset-auto md:z-auto md:w-full"
    role="dialog"
    aria-modal="true"
    aria-labelledby="instructions-drawer-title"
  >
    <div class="p-6 border-b border-navy flex items-start justify-between gap-4">
      <div>
        <h2
          id="instructions-drawer-title"
          class="text-lg font-semibold text-navy"
        >
          Instruktioner
        </h2>
        <p class="text-sm text-navy/70">
          Skriv instruktioner i Markdown-format.
        </p>
      </div>
      <button
        type="button"
        class="text-navy/60 hover:text-navy text-2xl leading-none"
        @click="emit('close')"
      >
        &times;
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-6 space-y-4">
      <!-- Toggle preview -->
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          {{ showPreview ? "Forhandsgranska" : "Redigera" }}
        </span>
        <button
          type="button"
          class="text-xs text-navy/70 hover:text-burgundy underline"
          @click="showPreview = !showPreview"
        >
          {{ showPreview ? "Visa redigerare" : "Visa forhandsgranska" }}
        </button>
      </div>

      <!-- Editor mode -->
      <div
        v-if="!showPreview"
        class="space-y-2"
      >
        <label
          for="usage-instructions-textarea"
          class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
        >
          Instruktioner (Markdown)
        </label>
        <textarea
          id="usage-instructions-textarea"
          :value="usageInstructions"
          rows="16"
          class="w-full border border-navy bg-white px-3 py-2 text-sm font-mono text-navy shadow-brutal-sm"
          placeholder="## Sa har gor du&#10;&#10;1. Ladda upp en fil&#10;2. Klicka pa Kor&#10;3. Ladda ner resultatet"
          :disabled="isSaving"
          @input="emit('update:usageInstructions', ($event.target as HTMLTextAreaElement).value)"
        />
      </div>

      <!-- Preview mode -->
      <div
        v-else
        class="border border-navy/20 bg-white p-4 shadow-brutal-sm min-h-[300px]"
      >
        <Suspense v-if="usageInstructions.trim()">
          <template #default>
            <UiMarkdown :markdown="usageInstructions" />
          </template>
          <template #fallback>
            <div class="flex items-center gap-3 text-sm text-navy/70">
              <span
                class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin"
              />
              <span>Laddar förhandsgranskning...</span>
            </div>
          </template>
        </Suspense>
        <p
          v-else
          class="text-sm text-navy/50 italic"
        >
          Inga instruktioner annu.
        </p>
      </div>
    </div>

    <div class="p-6 border-t border-navy">
      <button
        type="button"
        class="btn-primary w-full"
        :disabled="isSaving"
        @click="emit('save')"
      >
        {{ isSaving ? "Sparar..." : "Spara" }}
      </button>
    </div>
  </aside>
</template>

<style scoped>
.drawer-backdrop-enter-active,
.drawer-backdrop-leave-active {
  transition: opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to {
  opacity: 0;
}
</style>
