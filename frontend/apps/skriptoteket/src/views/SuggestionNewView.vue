<script setup lang="ts">
import { onMounted, ref } from "vue";

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
const isHelpLayoutActive = ref(false);
const selectedProfessions = ref<string[]>([]);
const selectedCategories = ref<string[]>([]);

const isLoading = ref(true);
const isSubmitting = ref(false);
const loadErrorMessage = ref<string | null>(null);
const formErrorMessage = ref<string | null>(null);

const toast = useToast();

function openHelp(): void {
  isHelpLayoutActive.value = true;
  showHelp.value = true;
}

function closeHelp(): void {
  showHelp.value = false;
}

function toggleHelp(): void {
  if (showHelp.value) {
    closeHelp();
    return;
  }

  openHelp();
}

function onHelpAfterLeave(): void {
  if (!showHelp.value) {
    isHelpLayoutActive.value = false;
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
});
</script>

<template>
  <div class="max-w-3xl space-y-6">
    <div class="space-y-2">
      <h1 class="page-title">Föreslå ett nytt verktyg</h1>
      <p class="page-description">Kom med ett förslag på ett nytt verktyg som du skulle vilja skapa själv eller tillsammans med Skriptotekets admins.</p>
    </div>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
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
        class="space-y-4"
        @submit.prevent="submit"
      >
        <SystemMessage
          v-model="formErrorMessage"
          variant="error"
        />

        <div class="space-y-2">
          <label
            for="title"
            class="text-sm font-semibold text-navy"
          >Titel</label>
          <input
            id="title"
            v-model="title"
            type="text"
            required
            placeholder="T.ex. ”Skapa slumpade elevgrupper”"
            class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
          >
        </div>

        <div
          class="space-y-2"
          @keydown.esc="closeHelp"
        >
          <div class="flex items-center gap-1">
            <label
              for="description"
              class="text-sm font-semibold text-navy"
            >Beskrivning</label>

            <button
              type="button"
              class="ml-1 inline-flex items-center justify-center text-navy/60 hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
              aria-label="Visa hjälp"
              :aria-expanded="showHelp"
              aria-controls="suggestion-description-help"
              @click="toggleHelp"
            >
              <IconHelp :size="16" />
            </button>
          </div>

          <div
            class="description-help-grid"
            :class="{ 'description-help-grid--with-help': isHelpLayoutActive }"
          >
            <textarea
              id="description"
              v-model="description"
              required
              rows="5"
              placeholder="Beskriv problemet och hur du vill att verktyget ska hjälpa dig..."
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
            />

            <Transition
              name="fade"
              @after-leave="onHelpAfterLeave"
            >
              <aside
                v-show="showHelp"
                id="suggestion-description-help"
                class="sticky-note text-sm text-navy/70"
                role="note"
              >
                <button
                  type="button"
                  class="sticky-note-close"
                  aria-label="Stäng hjälp"
                  @click="closeHelp"
                >
                  <IconX :size="16" />
                </button>

                <ul class="list-disc pl-5">
                  <li>Vilket problem vill du lösa?</li>
                  <li>Vilken typ av material matar du in?</li>
                  <li>Vad vill du få tillbaka?</li>
                  <li>Hur gör du uppgiften idag?</li>
                </ul>

                <p class="mt-6">
                  Exempel: "Jag vill kunna ladda upp en klasslista och få ut slumpmässiga grupper."
                </p>
              </aside>
            </Transition>
          </div>
        </div>

        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-sm font-semibold text-navy">Yrken</label>
            <span class="text-xs text-navy/60">Välj minst ett</span>
          </div>
          <div class="p-4 border border-navy bg-white shadow-brutal-sm">
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

        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-sm font-semibold text-navy">Kategorier</label>
            <span class="text-xs text-navy/60">Välj minst en</span>
          </div>
          <div class="p-4 border border-navy bg-white shadow-brutal-sm">
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
.description-help-grid {
  display: grid;
  gap: var(--huleedu-space-4);
}

@media (min-width: 768px) {
  .description-help-grid--with-help {
    grid-template-columns: minmax(0, 1fr) 22rem;
    align-items: start;
  }
}

.sticky-note {
  --note-line: var(--huleedu-grid-size);

  position: relative;
  padding: var(--huleedu-space-4);
  max-width: 22rem;
  background-color: #fff;
  border: 1px solid var(--huleedu-navy-20);
  box-shadow:
    4px 4px 0 var(--huleedu-navy),
    8px 8px 0 var(--huleedu-navy-20);
  line-height: var(--note-line);
  background-position: 0 var(--huleedu-space-4);
  background-image: repeating-linear-gradient(
    transparent,
    transparent calc(var(--note-line) - 1px),
    var(--huleedu-navy-10) calc(var(--note-line) - 1px),
    var(--huleedu-navy-10) var(--note-line)
  );
}

.sticky-note-close {
  position: absolute;
  top: var(--huleedu-space-1);
  right: var(--huleedu-space-1);
  width: 2rem;
  height: 2rem;
  display: grid;
  place-items: center;
  border: 1px solid transparent;
  border-radius: var(--huleedu-radius-sm);
  background: transparent;
  cursor: pointer;
  color: var(--huleedu-navy-60);
  transition:
    color var(--huleedu-duration-default) var(--huleedu-ease-default),
    border-color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.sticky-note-close:hover {
  color: var(--huleedu-burgundy);
  border-color: var(--huleedu-navy);
}

.sticky-note-close:active {
  border-color: var(--huleedu-navy);
}

.sticky-note-close:focus-visible {
  outline: 2px solid var(--huleedu-burgundy-40);
  outline-offset: 2px;
  border-color: var(--huleedu-navy);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 200ms var(--huleedu-ease-default);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
