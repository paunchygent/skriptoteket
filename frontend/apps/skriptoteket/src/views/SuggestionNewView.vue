<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

import { apiGet, apiPost, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import { useToast } from "../composables/useToast";
import SystemMessage from "../components/ui/SystemMessage.vue";
import { IconHelp, IconX } from "../components/icons";

type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];
type SubmitSuggestionResponse = components["schemas"]["SubmitSuggestionResponse"];

const professions = ref<ProfessionItem[]>([]);
const categories = ref<CategoryItem[]>([]);

const title = ref("");
const description = ref("");
const showHelp = ref(false);
const helpTriggerRef = ref<HTMLButtonElement | null>(null);
const helpPopoverRef = ref<HTMLDivElement | null>(null);
const selectedProfessions = ref<string[]>([]);
const selectedCategories = ref<string[]>([]);

const isLoading = ref(true);
const isSubmitting = ref(false);
const loadErrorMessage = ref<string | null>(null);
const formErrorMessage = ref<string | null>(null);

const toast = useToast();

function closeHelp(): void {
  showHelp.value = false;
}

function toggleHelp(): void {
  showHelp.value = !showHelp.value;
}

function handleClickOutside(event: MouseEvent): void {
  if (!showHelp.value) return;
  const target = event.target as Node;
  if (
    helpTriggerRef.value?.contains(target) ||
    helpPopoverRef.value?.contains(target)
  ) {
    return;
  }
  closeHelp();
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key === "Escape" && showHelp.value) {
    closeHelp();
  }
}

async function loadTaxonomy(): Promise<void> {
  isLoading.value = true;
  loadErrorMessage.value = null;
  formErrorMessage.value = null;

  try {
    const [profResp, catResp] = await Promise.all([
      apiGet<{ professions: ProfessionItem[] }>("/api/v1/catalog/professions"),
      apiGet<{ categories: CategoryItem[] }>("/api/v1/catalog/categories"),
    ]);

    professions.value = profResp.professions;
    categories.value = catResp.categories;
  } catch (error: unknown) {
    if (isApiError(error)) {
      loadErrorMessage.value = error.message;
    } else if (error instanceof Error) {
      loadErrorMessage.value = error.message;
    } else {
      loadErrorMessage.value = "Det gick inte att ladda listor.";
    }
  } finally {
    isLoading.value = false;
  }
}

function resetForm(): void {
  title.value = "";
  description.value = "";
  selectedProfessions.value = [];
  selectedCategories.value = [];
}

async function submit(): Promise<void> {
  if (isSubmitting.value) return;

  formErrorMessage.value = null;

  if (!title.value.trim() || !description.value.trim()) {
    formErrorMessage.value = "Titel och beskrivning krävs.";
    return;
  }
  if (selectedProfessions.value.length === 0) {
    formErrorMessage.value = "Välj minst ett yrke.";
    return;
  }
  if (selectedCategories.value.length === 0) {
    formErrorMessage.value = "Välj minst en kategori.";
    return;
  }

  isSubmitting.value = true;

  try {
    await apiPost<SubmitSuggestionResponse>("/api/v1/suggestions", {
      title: title.value,
      description: description.value,
      profession_slugs: selectedProfessions.value,
      category_slugs: selectedCategories.value,
    });

    resetForm();
    toast.success("Förslaget skickades och väntar på granskning.");
  } catch (error: unknown) {
    if (isApiError(error)) {
      toast.failure(error.message);
    } else if (error instanceof Error) {
      toast.failure(error.message);
    } else {
      toast.failure("Kunde inte skicka förslaget.");
    }
  } finally {
    isSubmitting.value = false;
  }
}

function toggleSelection(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

onMounted(() => {
  void loadTaxonomy();
  document.addEventListener("click", handleClickOutside);
  document.addEventListener("keydown", handleEscape);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
  document.removeEventListener("keydown", handleEscape);
});
</script>

<template>
  <div class="space-y-6">
    <header class="expand-left-40 space-y-1">
      <h1 class="page-title">Föreslå ett nytt verktyg</h1>
      <p class="page-description">Kom med ett förslag på ett nytt verktyg som du skulle vilja skapa själv eller tillsammans med Skriptotekets admins.</p>
    </header>

    <div
      v-if="isLoading"
      class="expand-left-40 p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Laddar formulär...
    </div>

    <div
      v-else
      class="space-y-4"
    >
      <SystemMessage
        v-model="loadErrorMessage"
        variant="error"
      />

      <form
        class="expand-left-40 border border-navy bg-white p-4 shadow-brutal-sm space-y-4"
        @submit.prevent="submit"
      >
        <SystemMessage
          v-model="formErrorMessage"
          variant="error"
        />

        <div class="expand-left-40 space-y-2">
          <label
            for="title"
            class="text-sm font-semibold text-navy"
          >Titel</label>
          <input
            id="title"
            v-model="title"
            type="text"
            required
            placeholder="T.ex. 'Skapa slumpade elevgrupper'"
            class="w-full border border-navy bg-white px-3 py-2 text-navy"
          >
        </div>

        <div class="expand-left-40 space-y-2">
          <div class="relative flex items-center gap-1">
            <label
              for="description"
              class="text-sm font-semibold text-navy"
            >Beskrivning</label>

            <button
              ref="helpTriggerRef"
              type="button"
              class="help-trigger"
              aria-label="Visa hjälp"
              :aria-expanded="showHelp"
              aria-controls="suggestion-description-help"
              @click.stop="toggleHelp"
            >
              <IconHelp :size="16" />
            </button>

            <Transition name="popover">
              <div
                v-if="showHelp"
                id="suggestion-description-help"
                ref="helpPopoverRef"
                class="help-popover"
                role="tooltip"
              >
                <button
                  type="button"
                  class="help-popover-close"
                  aria-label="Stäng hjälp"
                  @click="closeHelp"
                >
                  <IconX :size="14" />
                </button>

                <p class="font-semibold text-navy mb-2">Tips för en bra beskrivning:</p>
                <ul class="list-disc pl-4 space-y-1">
                  <li>Vilket problem vill du lösa?</li>
                  <li>Vilken typ av material matar du in?</li>
                  <li>Vad vill du få tillbaka?</li>
                  <li>Hur gör du uppgiften idag?</li>
                </ul>

                <p class="mt-3 pt-3 border-t border-navy/10 text-navy/60 italic">
                  Exempel: "Jag vill kunna ladda upp en klasslista och få ut slumpmässiga grupper."
                </p>
              </div>
            </Transition>
          </div>

          <textarea
            id="description"
            v-model="description"
            required
            rows="5"
            placeholder="Beskriv problemet och hur du vill att verktyget ska hjälpa dig..."
            class="w-full border border-navy bg-white px-3 py-2 text-navy"
          />
        </div>

        <div class="expand-left-40 space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-sm font-semibold text-navy">Yrken</label>
            <span class="text-xs text-navy/60">Välj minst ett</span>
          </div>
          <div class="p-4 border border-navy bg-white">
            <div class="grid gap-3 sm:grid-cols-2">
              <label
                v-for="profession in professions"
                :key="profession.slug"
                class="flex items-center gap-2 text-sm text-navy cursor-pointer"
              >
                <input
                  :value="profession.slug"
                  type="checkbox"
                  class="h-4 w-4 accent-burgundy"
                  :checked="selectedProfessions.includes(profession.slug)"
                  @change="selectedProfessions = toggleSelection(selectedProfessions, profession.slug)"
                >
                <span>{{ profession.label }}</span>
              </label>
            </div>
          </div>
        </div>

        <div class="expand-left-40 space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-sm font-semibold text-navy">Kategorier</label>
            <span class="text-xs text-navy/60">Välj minst en</span>
          </div>
          <div class="p-4 border border-navy bg-white">
            <div class="grid gap-3 sm:grid-cols-2">
              <label
                v-for="category in categories"
                :key="category.slug"
                class="flex items-center gap-2 text-sm text-navy cursor-pointer"
              >
                <input
                  :value="category.slug"
                  type="checkbox"
                  class="h-4 w-4 accent-burgundy"
                  :checked="selectedCategories.includes(category.slug)"
                  @change="selectedCategories = toggleSelection(selectedCategories, category.slug)"
                >
                <span>{{ category.label }}</span>
              </label>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <button
            type="submit"
            class="btn-cta"
            :disabled="isSubmitting"
          >
            {{ isSubmitting ? "Skickar..." : "Skicka förslag" }}
          </button>

          <button
            type="button"
            class="btn-ghost"
            :disabled="isSubmitting"
            @click="resetForm"
          >
            Rensa
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.help-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
  color: var(--huleedu-navy-60);
  border-radius: var(--huleedu-radius-sm);
  transition:
    color var(--huleedu-duration-default) var(--huleedu-ease-default),
    background-color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.help-trigger:hover {
  color: var(--huleedu-burgundy);
  background-color: var(--huleedu-burgundy-10);
}

.help-trigger:focus-visible {
  outline: 2px solid var(--huleedu-burgundy-40);
  outline-offset: 2px;
}

.help-popover {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  z-index: 50;
  width: max-content;
  max-width: min(20rem, calc(100vw - 2rem));
  padding: 1rem;
  padding-right: 2.5rem;
  background-color: #fff;
  border: 1px solid var(--huleedu-navy);
  box-shadow: 4px 4px 0 var(--huleedu-navy);
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--huleedu-navy-80);
}

.help-popover-close {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  display: grid;
  place-items: center;
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--huleedu-radius-sm);
  background: transparent;
  color: var(--huleedu-navy-60);
  cursor: pointer;
  transition:
    color var(--huleedu-duration-default) var(--huleedu-ease-default),
    border-color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.help-popover-close:hover {
  color: var(--huleedu-burgundy);
  border-color: var(--huleedu-navy);
}

.help-popover-close:focus-visible {
  outline: 2px solid var(--huleedu-burgundy-40);
  outline-offset: 2px;
}

.popover-enter-active,
.popover-leave-active {
  transition:
    opacity 150ms var(--huleedu-ease-default),
    transform 150ms var(--huleedu-ease-default);
}

.popover-enter-from,
.popover-leave-to {
  opacity: 0;
  transform: translateY(-0.25rem);
}
</style>
