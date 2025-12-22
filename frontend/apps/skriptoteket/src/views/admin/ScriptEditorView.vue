<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";

import type { components } from "../../api/openapi";
import CodeMirrorEditor from "../../components/editor/CodeMirrorEditor.vue";
import SandboxRunner from "../../components/editor/SandboxRunner.vue";
import { useScriptEditor } from "../../composables/editor/useScriptEditor";
import { useToolTaxonomy } from "../../composables/editor/useToolTaxonomy";
import { useAuthStore } from "../../stores/auth";

type VersionState = components["schemas"]["VersionState"];

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const toolId = computed(() => {
  const param = route.params.toolId;
  return typeof param === "string" ? param : "";
});

const versionId = computed(() => {
  const param = route.params.versionId;
  return typeof param === "string" ? param : "";
});

const canEditTaxonomy = computed(() => auth.hasAtLeastRole("admin"));

const {
  editor,
  entrypoint,
  sourceCode,
  changeSummary,
  isLoading,
  isSaving,
  errorMessage,
  successMessage,
  selectedVersion,
  editorToolId,
  saveButtonLabel,
  hasDirtyChanges,
  save,
} = useScriptEditor({
  toolId,
  versionId,
  route,
  router,
});

const {
  professions,
  categories,
  selectedProfessionIds,
  selectedCategoryIds,
  taxonomyError,
  taxonomySuccess,
  isTaxonomyLoading,
  isTaxonomySaving,
  saveTaxonomy,
  toggleSelection,
} = useToolTaxonomy({
  toolId: editorToolId,
  canEdit: canEditTaxonomy,
});

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

function versionLabel(state: VersionState): string {
  const labels: Record<VersionState, string> = {
    draft: "Utkast",
    in_review: "Granskning",
    active: "Publicerad",
    archived: "Arkiverad",
  };
  return labels[state] ?? state;
}

const beforeUnloadHandler = (event: BeforeUnloadEvent) => {
  if (!hasDirtyChanges.value || isSaving.value) return;
  event.preventDefault();
  event.returnValue = "";
};

onBeforeRouteLeave((_to, _from, next) => {
  if (!hasDirtyChanges.value || isSaving.value) {
    next();
    return;
  }

  if (window.confirm("Du har osparade ändringar. Vill du lämna sidan?")) {
    next();
  } else {
    next(false);
  }
});

onMounted(() => {
  window.addEventListener("beforeunload", beforeUnloadHandler);
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", beforeUnloadHandler);
});
</script>

<template>
  <div class="space-y-6">
    <RouterLink
      to="/admin/tools"
      class="text-sm text-navy/70 underline hover:text-burgundy"
    >
      ← Tillbaka till verktyg
    </RouterLink>

    <div class="border border-navy bg-white shadow-brutal-sm p-4 space-y-2">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="space-y-1">
          <h1 class="text-2xl font-semibold text-navy">
            {{ editor?.tool.title ?? (isLoading ? "Laddar..." : "Skripteditorn") }}
          </h1>
          <p class="text-sm text-navy/70">
            <span
              v-if="editor"
              class="font-mono"
            >{{ editor.tool.slug }}</span>
            <span v-else>Förbered editor</span>
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs">
          <span
            class="px-2 py-1 border border-navy bg-canvas text-navy/70 uppercase tracking-wide font-semibold"
          >
            {{ editor ? (editor.tool.is_published ? "Publicerad" : "Ej publicerad") : "Status" }}
          </span>
          <span
            class="px-2 py-1 border border-navy bg-white text-navy uppercase tracking-wide font-semibold"
          >
            <template v-if="selectedVersion">
              v{{ selectedVersion.version_number }} · {{ versionLabel(selectedVersion.state) }}
            </template>
            <template v-else>
              Nytt utkast
            </template>
          </span>
        </div>
      </div>

      <p
        v-if="editor?.tool.summary"
        class="text-sm text-navy/70"
      >
        {{ editor.tool.summary }}
      </p>
    </div>

    <div
      v-if="successMessage"
      class="p-4 border border-success bg-success/10 shadow-brutal-sm text-sm text-success"
    >
      {{ successMessage }}
    </div>

    <div
      v-if="errorMessage"
      class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Laddar...
    </div>

    <div
      v-else-if="!editor"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Det gick inte att ladda editorn.
    </div>

    <div
      v-else
      class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]"
    >
      <section class="space-y-4">
        <div class="border border-navy bg-white shadow-brutal-sm p-4 space-y-3">
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
              Källkod
            </h2>
            <span
              v-if="hasDirtyChanges"
              class="text-xs text-burgundy font-semibold uppercase tracking-wide"
            >
              Osparat
            </span>
          </div>

          <div class="h-[420px] border border-navy bg-canvas shadow-brutal-sm">
            <CodeMirrorEditor v-model="sourceCode" />
          </div>
        </div>

        <div class="border border-navy bg-white shadow-brutal-sm p-4 space-y-3">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
            Testa i sandbox
          </h2>

          <SandboxRunner
            v-if="selectedVersion"
            :version-id="selectedVersion.id"
            :tool-id="editor.tool.id"
          />
          <p
            v-else
            class="text-sm text-navy/60"
          >
            Spara ett utkast för att kunna testa.
          </p>
        </div>
      </section>

      <aside class="space-y-4">
        <div class="border border-navy bg-white shadow-brutal-sm p-4 space-y-4">
          <div class="space-y-2">
            <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">Startfunktion</label>
            <input
              v-model="entrypoint"
              class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
              placeholder="run_tool"
            >
          </div>

          <div class="space-y-2">
            <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
              Ändringssammanfattning
            </label>
            <input
              v-model="changeSummary"
              class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
              placeholder="T.ex. fixade bugg..."
            >
          </div>

          <button
            type="button"
            :disabled="isSaving"
            class="w-full px-4 py-2 text-xs font-bold uppercase tracking-widest bg-burgundy text-canvas border border-navy shadow-brutal-sm hover:bg-navy transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
            @click="save"
          >
            {{ saveButtonLabel }}
          </button>

          <p
            v-if="hasDirtyChanges"
            class="text-xs text-navy/60"
          >
            Du har osparade ändringar.
          </p>
        </div>

        <div class="border border-navy bg-white shadow-brutal-sm p-4 space-y-3">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
            Historik
          </h2>

          <p
            v-if="editor.versions.length === 0"
            class="text-sm text-navy/60"
          >
            Inga versioner ännu.
          </p>

          <ul
            v-else
            class="space-y-2"
          >
            <li
              v-for="version in editor.versions"
              :key="version.id"
              class="border border-navy/30 bg-canvas shadow-brutal-sm"
            >
              <RouterLink
                :to="`/admin/tool-versions/${version.id}`"
                class="flex items-center justify-between gap-3 px-3 py-2"
              >
                <div>
                  <div class="text-sm font-semibold text-navy">
                    v{{ version.version_number }}
                  </div>
                  <div class="text-xs text-navy/60">
                    {{ formatDateTime(version.created_at) }}
                  </div>
                </div>
                <span
                  :class="[
                    'px-2 py-0.5 border text-xs font-semibold uppercase tracking-wide',
                    version.state === 'active'
                      ? 'border-burgundy text-burgundy'
                      : 'border-navy/40 text-navy/70',
                  ]"
                >
                  {{ versionLabel(version.state) }}
                </span>
              </RouterLink>
            </li>
          </ul>
        </div>

        <div
          v-if="canEditTaxonomy"
          class="border border-navy bg-white shadow-brutal-sm p-4 space-y-3"
        >
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
              Taxonomi
            </h2>
            <span
              v-if="isTaxonomyLoading"
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
            v-if="!isTaxonomyLoading"
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
                    @change="selectedProfessionIds = toggleSelection(selectedProfessionIds, profession.id)"
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
                    @change="selectedCategoryIds = toggleSelection(selectedCategoryIds, category.id)"
                  >
                  <span>{{ category.label }}</span>
                </label>
              </div>
            </div>

            <button
              type="button"
              class="w-full px-4 py-2 text-xs font-bold uppercase tracking-widest bg-navy text-canvas border border-navy shadow-brutal-sm hover:bg-burgundy transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="isTaxonomySaving"
              @click="saveTaxonomy"
            >
              {{ isTaxonomySaving ? "Sparar..." : "Spara taxonomi" }}
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>
