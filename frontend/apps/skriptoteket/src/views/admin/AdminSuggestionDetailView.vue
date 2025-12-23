<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiGet, apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type SuggestionDetailResponse = components["schemas"]["SuggestionDetailResponse"];
type SuggestionDetail = components["schemas"]["SuggestionDetail"];
type SuggestionDecisionItem = components["schemas"]["SuggestionDecisionItem"];
type DecideSuggestionResponse = components["schemas"]["DecideSuggestionResponse"];
type SuggestionDecisionType = components["schemas"]["SuggestionDecisionType"];
type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];

const route = useRoute();
const router = useRouter();

const suggestionId = computed(() => {
  const raw = route.params.id;
  return typeof raw === "string" ? raw : "";
});

const suggestion = ref<SuggestionDetail | null>(null);
const decisions = ref<SuggestionDecisionItem[]>([]);
const professions = ref<ProfessionItem[]>([]);
const categories = ref<CategoryItem[]>([]);

const rationale = ref("");
const decision = ref<SuggestionDecisionType>("accept");
const title = ref<string | null>(null);
const description = ref<string | null>(null);
const selectedProfessions = ref<string[]>([]);
const selectedCategories = ref<string[]>([]);

const isLoading = ref(true);
const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

const canDecide = computed(() => suggestion.value?.status === "pending_review");

function statusLabel(status: SuggestionDetail["status"]): string {
  const labels: Record<SuggestionDetail["status"], string> = {
    pending_review: "Väntar på granskning",
    accepted: "Godkänd",
    denied: "Avslagen",
  };
  return labels[status];
}

function decisionLabel(decision: SuggestionDecisionType): string {
  return decision === "accept" ? "Godkänd" : "Avslagen";
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

async function loadTaxonomy(): Promise<void> {
  const [profResp, catResp] = await Promise.all([
    apiGet<{ professions: ProfessionItem[] }>("/api/v1/catalog/professions"),
    apiGet<{ categories: CategoryItem[] }>("/api/v1/catalog/categories"),
  ]);
  professions.value = profResp.professions;
  categories.value = catResp.categories;
}

async function load(): Promise<void> {
  if (!suggestionId.value) {
    errorMessage.value = "Saknar ID i länken.";
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;
  successMessage.value = null;

  try {
    await loadTaxonomy();
    const response = await apiGet<SuggestionDetailResponse>(
      `/api/v1/admin/suggestions/${encodeURIComponent(suggestionId.value)}`,
    );
    suggestion.value = response.suggestion;
    decisions.value = response.decisions;

    title.value = response.suggestion.title;
    description.value = response.suggestion.description;
    selectedProfessions.value = [...response.suggestion.profession_slugs];
    selectedCategories.value = [...response.suggestion.category_slugs];
  } catch (error: unknown) {
    suggestion.value = null;
    decisions.value = [];
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda förslaget.";
    }
  } finally {
    isLoading.value = false;
  }
}

async function submitDecision(): Promise<void> {
  if (!suggestion.value || !canDecide.value) return;
  if (isSubmitting.value) return;

  errorMessage.value = null;
  successMessage.value = null;

  if (!rationale.value.trim()) {
    errorMessage.value = "Motivering krävs.";
    return;
  }

  const payload: Record<string, unknown> = {
    decision: decision.value,
    rationale: rationale.value,
  };

  if (decision.value === "accept") {
    payload.title = title.value;
    payload.description = description.value;
    payload.profession_slugs = selectedProfessions.value;
    payload.category_slugs = selectedCategories.value;
  }

  isSubmitting.value = true;

  try {
    await apiPost<DecideSuggestionResponse>(
      `/api/v1/admin/suggestions/${encodeURIComponent(suggestion.value.id)}/decide`,
      payload,
    );

    successMessage.value = decision.value === "accept" ? "Förslag godkänt." : "Förslag avslaget.";
    await load();
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Kunde inte spara beslut.";
    }
  } finally {
    isSubmitting.value = false;
  }
}

function toggleSelection(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

watch(
  () => decision.value,
  (value) => {
    if (value === "deny") {
      // Clear optional fields when denying.
      title.value = suggestion.value?.title ?? null;
      description.value = suggestion.value?.description ?? null;
      selectedProfessions.value = [...(suggestion.value?.profession_slugs ?? [])];
      selectedCategories.value = [...(suggestion.value?.category_slugs ?? [])];
    }
  },
);

onMounted(() => {
  void load();
});

watch(suggestionId, () => {
  void load();
});

const showDecisionFields = computed(() => decision.value === "accept");
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold text-navy">Granska förslag</h1>
        <p class="text-sm text-navy/70">Läs, besluta och se historik.</p>
      </div>
      <button
        type="button"
        class="text-sm underline text-burgundy hover:text-navy"
        @click="router.back()"
      >
        ← Tillbaka
      </button>
    </div>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Laddar...
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else-if="!suggestion"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy"
    >
      Förslaget hittades inte.
    </div>

    <div
      v-else
      class="space-y-6"
    >
      <div class="border border-navy bg-white shadow-brutal-sm p-4 space-y-2">
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-xl font-semibold text-navy">{{ suggestion.title }}</h2>
          <span class="px-2 py-1 border border-navy bg-canvas shadow-brutal-sm text-xs font-semibold uppercase tracking-wide text-navy/70">
            {{ statusLabel(suggestion.status) }}
          </span>
        </div>

        <p class="text-sm text-navy/80 whitespace-pre-line">{{ suggestion.description }}</p>

        <div class="grid gap-2 sm:grid-cols-2 text-sm text-navy/70">
          <div>
            <span class="font-semibold text-navy">Inskickat:</span>
            {{ formatDateTime(suggestion.created_at) }}
          </div>
          <div>
            <span class="font-semibold text-navy">Av:</span>
            <span class="font-mono">{{ suggestion.submitted_by_user_id }}</span>
          </div>
          <div>
            <span class="font-semibold text-navy">Yrken:</span>
            {{ suggestion.profession_slugs.join(", ") }}
          </div>
          <div>
            <span class="font-semibold text-navy">Kategorier:</span>
            {{ suggestion.category_slugs.join(", ") }}
          </div>
          <div>
            <span class="font-semibold text-navy">Granskad:</span>
            {{ formatDateTime(suggestion.reviewed_at) }}
          </div>
          <div>
            <span class="font-semibold text-navy">Granskare:</span>
            <span class="font-mono">{{ suggestion.reviewed_by_user_id ?? "—" }}</span>
          </div>
        </div>

        <div
          v-if="suggestion.review_rationale"
          class="text-sm text-navy/80"
        >
          <span class="font-semibold text-navy">Motivering:</span>
          {{ suggestion.review_rationale }}
        </div>

        <div
          v-if="suggestion.draft_tool_id"
          class="text-sm text-navy/80"
        >
          <span class="font-semibold text-navy">Utkast-tool:</span>
          <span class="font-mono">{{ suggestion.draft_tool_id }}</span>
        </div>
      </div>

      <div class="border border-navy bg-white shadow-brutal-sm p-4 space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-navy">Historik</h3>
          <span class="text-xs text-navy/60">Senaste först</span>
        </div>

        <div
          v-if="decisions.length === 0"
          class="text-sm text-navy/70"
        >
          Inga beslut ännu.
        </div>

        <ul
          v-else
          class="space-y-3"
        >
          <li
            v-for="decisionItem in decisions"
            :key="decisionItem.id"
            class="border border-navy/30 bg-canvas px-3 py-2 shadow-brutal-sm space-y-1"
          >
            <div class="flex flex-wrap items-center gap-2 text-sm text-navy/80">
              <span class="font-semibold text-navy">{{ decisionLabel(decisionItem.decision) }}</span>
              <span class="text-xs text-navy/60">{{ formatDateTime(decisionItem.decided_at) }}</span>
              <span class="text-xs font-mono">{{ decisionItem.decided_by_user_id }}</span>
            </div>
            <div class="text-sm text-navy/80">Motivering: {{ decisionItem.rationale }}</div>
            <div class="text-sm text-navy/70">Titel: {{ decisionItem.title }}</div>
            <div class="text-sm text-navy/70">Yrken: {{ decisionItem.profession_slugs.join(", ") }}</div>
            <div class="text-sm text-navy/70">Kategorier: {{ decisionItem.category_slugs.join(", ") }}</div>
            <div
              v-if="decisionItem.created_tool_id"
              class="text-sm text-navy/70"
            >
              Utkast-tool: <span class="font-mono">{{ decisionItem.created_tool_id }}</span>
            </div>
          </li>
        </ul>
      </div>

      <div
        v-if="canDecide"
        class="border border-navy bg-white shadow-brutal-sm p-4 space-y-4"
      >
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-navy">Beslut</h3>
          <span class="text-xs text-navy/60">Obligatoriskt: motivering</span>
        </div>

        <div class="flex flex-wrap gap-4">
          <label class="inline-flex items-center gap-2 text-sm text-navy cursor-pointer">
            <input
              v-model="decision"
              type="radio"
              value="accept"
              class="h-4 w-4 accent-burgundy"
            >
            <span>Acceptera</span>
          </label>
          <label class="inline-flex items-center gap-2 text-sm text-navy cursor-pointer">
            <input
              v-model="decision"
              type="radio"
              value="deny"
              class="h-4 w-4 accent-burgundy"
            >
            <span>Avslå</span>
          </label>
        </div>

        <div class="space-y-2">
          <label
            class="text-sm font-semibold text-navy"
            for="rationale"
          >Motivering</label>
          <textarea
            id="rationale"
            v-model="rationale"
            rows="3"
            required
            class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
          />
        </div>

        <div
          v-if="showDecisionFields"
          class="space-y-4"
        >
          <div class="space-y-2">
            <label
              class="text-sm font-semibold text-navy"
              for="title"
            >Titel</label>
            <input
              id="title"
              v-model="title"
              type="text"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
            >
          </div>

          <div class="space-y-2">
            <label
              class="text-sm font-semibold text-navy"
              for="description"
            >Beskrivning</label>
            <textarea
              id="description"
              v-model="description"
              rows="4"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
            />
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-sm font-semibold text-navy">Yrken</label>
              <span class="text-xs text-navy/60">Justera vid behov</span>
            </div>
            <div class="grid gap-2 sm:grid-cols-2">
              <label
                v-for="profession in professions"
                :key="profession.slug"
                class="flex items-center gap-2 border border-navy/30 bg-white px-3 py-2 shadow-brutal-sm text-sm text-navy"
              >
                <input
                  :value="profession.slug"
                  type="checkbox"
                  class="border-navy"
                  :checked="selectedProfessions.includes(profession.slug)"
                  @change="selectedProfessions = toggleSelection(selectedProfessions, profession.slug)"
                >
                <span>{{ profession.label }}</span>
              </label>
            </div>
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-sm font-semibold text-navy">Kategorier</label>
              <span class="text-xs text-navy/60">Justera vid behov</span>
            </div>
            <div class="grid gap-2 sm:grid-cols-2">
              <label
                v-for="category in categories"
                :key="category.slug"
                class="flex items-center gap-2 border border-navy/30 bg-white px-3 py-2 shadow-brutal-sm text-sm text-navy"
              >
                <input
                  :value="category.slug"
                  type="checkbox"
                  class="border-navy"
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
            type="button"
            class="px-4 py-2 border border-navy bg-burgundy text-canvas shadow-brutal font-semibold uppercase tracking-wide btn-secondary-hover transition-colors disabled:opacity-50"
            :disabled="isSubmitting"
            @click="submitDecision"
          >
            {{ isSubmitting ? "Sparar..." : "Spara beslut" }}
          </button>

          <button
            type="button"
            class="px-4 py-2 border border-navy bg-white text-navy shadow-brutal-sm font-semibold hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="isSubmitting"
            @click="router.push({ name: 'admin-suggestions' })"
          >
            Avbryt
          </button>
        </div>

        <div
          v-if="successMessage"
          class="p-3 border border-navy bg-white shadow-brutal-sm text-sm text-navy"
        >
          {{ successMessage }}
        </div>
        <div
          v-if="errorMessage"
          class="p-3 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
        >
          {{ errorMessage }}
        </div>
      </div>

      <div
        v-else
        class="p-3 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
      >
        Förslaget är redan granskat.
      </div>
    </div>
  </div>
</template>
