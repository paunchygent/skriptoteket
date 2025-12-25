<script setup lang="ts">
import { onMounted, ref } from "vue";

import { apiGet, apiPost, isApiError } from "../api/client";
import type { components } from "../api/openapi";

type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];
type SubmitSuggestionResponse = components["schemas"]["SubmitSuggestionResponse"];

const professions = ref<ProfessionItem[]>([]);
const categories = ref<CategoryItem[]>([]);

const title = ref("");
const description = ref("");
const selectedProfessions = ref<string[]>([]);
const selectedCategories = ref<string[]>([]);

const isLoading = ref(true);
const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

async function loadTaxonomy(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    const [profResp, catResp] = await Promise.all([
      apiGet<{ professions: ProfessionItem[] }>("/api/v1/catalog/professions"),
      apiGet<{ categories: CategoryItem[] }>("/api/v1/catalog/categories"),
    ]);

    professions.value = profResp.professions;
    categories.value = catResp.categories;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda listor.";
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

  errorMessage.value = null;
  successMessage.value = null;

  if (!title.value.trim() || !description.value.trim()) {
    errorMessage.value = "Titel och beskrivning krävs.";
    return;
  }
  if (selectedProfessions.value.length === 0) {
    errorMessage.value = "Välj minst ett yrke.";
    return;
  }
  if (selectedCategories.value.length === 0) {
    errorMessage.value = "Välj minst en kategori.";
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
    successMessage.value = "Förslaget skickades och väntar på granskning.";
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Kunde inte skicka förslaget.";
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
      <h1 class="text-2xl font-semibold text-navy">Föreslå ett skript</h1>
      <p class="text-sm text-navy/70">
        Dela ett skriptförslag med teamet. Ange titel, beskrivning, yrken och kategorier.
      </p>
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
      <div
        v-if="errorMessage"
        class="p-3 border border-burgundy bg-white shadow-brutal-sm text-burgundy text-sm"
      >
        {{ errorMessage }}
      </div>

      <div
        v-if="successMessage"
        class="p-3 border border-navy bg-white shadow-brutal-sm text-navy text-sm"
      >
        {{ successMessage }}
      </div>

      <form
        class="space-y-4"
        @submit.prevent="submit"
      >
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
            class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
          >
        </div>

        <div class="space-y-2">
          <label
            for="description"
            class="text-sm font-semibold text-navy"
          >Beskrivning</label>
          <textarea
            id="description"
            v-model="description"
            required
            rows="5"
            class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
          />
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
