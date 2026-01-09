<script setup lang="ts">
import { computed, defineAsyncComponent, ref } from "vue";

const UiMarkdown = defineAsyncComponent(() => import("../ui/UiMarkdown.vue"));

type InstructionsDrawerProps = {
  isOpen: boolean;
  variant?: "drawer" | "panel";
  usageInstructions: string;
  isSaving: boolean;
  isReadOnly: boolean;
};

const props = withDefaults(defineProps<InstructionsDrawerProps>(), {
  variant: "drawer",
});

const isPanel = computed(() => props.variant === "panel");

const emit = defineEmits<{
  (event: "close"): void;
  (event: "save"): void;
  (event: "update:usageInstructions", value: string): void;
}>();

const showPreview = ref(false);
</script>

<template>
  <!-- Mobile backdrop -->
  <Teleport
    v-if="!isPanel"
    to="body"
  >
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
    :class="[
      isPanel
        ? 'relative w-full bg-white border border-navy/20 shadow-brutal-sm flex flex-col min-h-0'
        : 'fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy shadow-brutal flex flex-col md:relative md:inset-auto md:z-auto md:w-full md:h-full md:overflow-hidden',
    ]"
    :role="isPanel ? 'region' : 'dialog'"
    :aria-modal="!isPanel"
    aria-labelledby="instructions-drawer-title"
  >
    <div
      v-if="isPanel"
      class="border-b border-navy/20 px-3 py-2 flex items-center justify-between gap-3"
    >
      <span
        id="instructions-drawer-title"
        class="text-[10px] font-semibold uppercase tracking-wide text-navy/60"
      >
        Instruktioner
      </span>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
          @click="showPreview = !showPreview"
        >
          {{ showPreview ? "Redigera" : "F&ouml;rhandsgranska" }}
        </button>
        <button
          type="button"
          class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
          :disabled="isSaving || isReadOnly"
          @click="emit('save')"
        >
          {{ isSaving ? "Sparar..." : "Spara" }}
        </button>
      </div>
    </div>

    <div
      v-else
      class="border-b border-navy flex items-start justify-between gap-4 p-4"
    >
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

    <div
      :class="[
        isPanel ? 'p-3 space-y-3' : 'flex-1 overflow-y-auto p-4 space-y-4',
      ]"
    >
      <!-- Toggle preview -->
      <div
        v-if="!isPanel"
        class="flex items-center justify-between"
      >
        <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          {{ showPreview ? "F&ouml;rhandsgranska" : "Redigera" }}
        </span>
        <button
          type="button"
          class="text-xs text-navy/70 hover:text-burgundy underline"
          @click="showPreview = !showPreview"
        >
          {{ showPreview ? "Visa redigerare" : "Visa f&ouml;rhandsgranskning" }}
        </button>
      </div>

      <!-- Editor mode -->
      <div
        v-if="!showPreview"
        class="space-y-2"
      >
        <label
          for="usage-instructions-textarea"
          class="block text-[10px] font-semibold uppercase tracking-wide text-navy/60"
        >
          Markdown
        </label>
        <textarea
          id="usage-instructions-textarea"
          :value="usageInstructions"
          rows="16"
          class="w-full border border-navy/30 bg-white px-2.5 py-1.5 text-[11px] font-mono text-navy shadow-none leading-snug"
          placeholder="## Sa har gor du&#10;&#10;1. Ladda upp en fil&#10;2. Klicka pa Kor&#10;3. Ladda ner resultatet"
          :disabled="isSaving || isReadOnly"
          @input="emit('update:usageInstructions', ($event.target as HTMLTextAreaElement).value)"
        />
      </div>

      <!-- Preview mode -->
      <div
        v-else
        class="border border-navy/30 bg-white p-3 shadow-none min-h-[240px]"
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
          Inga instruktioner &auml;nnu.
        </p>
      </div>

      <!-- Save button -->
      <div
        v-if="!isPanel"
        class="pt-4 border-t border-navy/20"
      >
        <button
          type="button"
          class="btn-ghost"
          :disabled="isSaving || isReadOnly"
          @click="emit('save')"
        >
          {{ isSaving ? "Sparar..." : "Spara" }}
        </button>
      </div>
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
