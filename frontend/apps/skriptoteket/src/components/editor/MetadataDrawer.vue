<script setup lang="ts">
import type { components } from "../../api/openapi";

type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];

type MetadataDrawerProps = {
  isOpen: boolean;
  metadataTitle: string;
  metadataSlug: string;
  metadataSummary: string;
  canEditSlug: boolean;
  slugError: string | null;
  professions: ProfessionItem[];
  categories: CategoryItem[];
  selectedProfessionIds: string[];
  selectedCategoryIds: string[];
  taxonomyError: string | null;
  taxonomySuccess: string | null;
  isLoading: boolean;
  isSaving: boolean;
};

const props = defineProps<MetadataDrawerProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "save"): void;
  (event: "update:metadataTitle", value: string): void;
  (event: "update:metadataSlug", value: string): void;
  (event: "update:metadataSummary", value: string): void;
  (event: "suggestSlugFromTitle"): void;
  (event: "update:selectedProfessionIds", value: string[]): void;
  (event: "update:selectedCategoryIds", value: string[]): void;
}>();

function toggleSelection(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function toggleProfession(value: string): void {
  emit("update:selectedProfessionIds", toggleSelection(props.selectedProfessionIds, value));
}

function toggleCategory(value: string): void {
  emit("update:selectedCategoryIds", toggleSelection(props.selectedCategoryIds, value));
}
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

  <!-- Drawer - direct grid participant on desktop -->
  <aside
    class="fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy shadow-brutal flex flex-col md:relative md:inset-auto md:z-auto md:w-full"
    role="dialog"
    aria-modal="true"
    aria-labelledby="metadata-drawer-title"
  >
    <div class="p-6 border-b border-navy flex items-start justify-between gap-4">
      <div>
        <h2
          id="metadata-drawer-title"
          class="text-lg font-semibold text-navy"
        >
          Redigera metadata
        </h2>
        <p class="text-sm text-navy/70">
          Uppdatera titel, sammanfattning och kategorisering.
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

    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      <!-- Title and Summary -->
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">Verktygsinfo</span>
        </div>

        <div class="space-y-3">
          <div class="space-y-1">
            <label class="block text-xs font-semibold uppercase tracking-wide text-navy/70">
              Titel
            </label>
            <input
              :value="metadataTitle"
              type="text"
              class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
              placeholder="Verktygets titel"
              :disabled="isSaving"
              @input="emit('update:metadataTitle', ($event.target as HTMLInputElement).value)"
            >
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="block text-xs font-semibold uppercase tracking-wide text-navy/70">
                URL-namn
              </label>
              <button
                type="button"
                class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide whitespace-nowrap"
                :disabled="isSaving || !canEditSlug"
                @click="emit('suggestSlugFromTitle')"
              >
                Använd nuvarande titel
              </button>
            </div>

            <input
              :value="metadataSlug"
              type="text"
              class="w-full border border-navy bg-white px-3 py-2 text-sm font-mono text-navy shadow-brutal-sm"
              placeholder="t.ex. mattest"
              :disabled="isSaving || !canEditSlug"
              @input="emit('update:metadataSlug', ($event.target as HTMLInputElement).value)"
            >

            <p class="text-xs text-navy/60">
              Används i länken <span class="font-mono">/tools/&lt;url-namn&gt;/run</span>.
              <span v-if="!canEditSlug">URL-namn är låst efter publicering.</span>
            </p>

            <p
              v-if="slugError"
              class="text-sm text-burgundy"
            >
              {{ slugError }}
            </p>
          </div>

          <div class="space-y-1">
            <label class="block text-xs font-semibold uppercase tracking-wide text-navy/70">
              Sammanfattning
            </label>
            <textarea
              :value="metadataSummary"
              rows="3"
              class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
              placeholder="Kort beskrivning av verktyget"
              :disabled="isSaving"
              @input="emit('update:metadataSummary', ($event.target as HTMLTextAreaElement).value)"
            />
          </div>
        </div>
      </div>

      <!-- Taxonomy section -->
      <div class="border-t border-navy/20 pt-4 space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">Taxonomi</span>
          <span
            v-if="isLoading"
            class="text-xs text-navy/60"
          >
            Laddar...
          </span>
        </div>

        <p
          v-if="taxonomyError"
          class="text-sm text-burgundy"
        >
          {{ taxonomyError }}
        </p>
        <p
          v-else-if="taxonomySuccess"
          class="text-sm text-navy"
        >
          {{ taxonomySuccess }}
        </p>

        <div
          v-if="!isLoading"
          class="space-y-4"
        >
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">Yrken</span>
              <span class="text-xs text-navy/60">Välj minst ett</span>
            </div>
            <div class="grid gap-2">
              <label
                v-for="profession in professions"
                :key="profession.id"
                class="flex items-center gap-2 border border-navy/30 bg-white px-3 py-2 shadow-brutal-sm text-xs text-navy"
              >
                <input
                  :value="profession.id"
                  type="checkbox"
                  class="border-navy"
                  :checked="selectedProfessionIds.includes(profession.id)"
                  @change="toggleProfession(profession.id)"
                >
                <span>{{ profession.label }}</span>
              </label>
            </div>
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">Kategorier</span>
              <span class="text-xs text-navy/60">Välj minst en</span>
            </div>
            <div class="grid gap-2">
              <label
                v-for="category in categories"
                :key="category.id"
                class="flex items-center gap-2 border border-navy/30 bg-white px-3 py-2 shadow-brutal-sm text-xs text-navy"
              >
                <input
                  :value="category.id"
                  type="checkbox"
                  class="border-navy"
                  :checked="selectedCategoryIds.includes(category.id)"
                  @change="toggleCategory(category.id)"
                >
                <span>{{ category.label }}</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="p-6 border-t border-navy">
      <button
        type="button"
        class="btn-primary w-full"
        :disabled="isSaving"
        @click="emit('save')"
      >
        {{ isSaving ? "Sparar..." : "Spara metadata" }}
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

.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: transform var(--huleedu-duration-slow) var(--huleedu-ease-default),
    opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.drawer-slide-enter-from,
.drawer-slide-leave-to {
  transform: translateX(8%);
  opacity: 0;
}
</style>
