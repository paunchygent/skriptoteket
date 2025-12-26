<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import type { components } from "../../api/openapi";

import { useSkriptoteketIntelligenceExtensions } from "../../composables/editor/useSkriptoteketIntelligenceExtensions";
import EntrypointDropdown from "./EntrypointDropdown.vue";
import InstructionsDrawer from "./InstructionsDrawer.vue";
import MaintainersDrawer from "./MaintainersDrawer.vue";
import MetadataDrawer from "./MetadataDrawer.vue";
import VersionHistoryDrawer from "./VersionHistoryDrawer.vue";

const CodeMirrorEditor = defineAsyncComponent(() => import("./CodeMirrorEditor.vue"));
const SandboxRunner = defineAsyncComponent(() => import("./SandboxRunner.vue"));

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];
type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];
type MaintainerSummary = components["schemas"]["MaintainerSummary"];

type EditorWorkspacePanelProps = {
  toolId: string;
  versions: EditorVersionSummary[];
  selectedVersion: EditorVersionSummary | null;
  entrypointOptions: string[];

  changeSummary: string;
  entrypoint: string;
  sourceCode: string;
  settingsSchemaText: string;
  inputSchemaText: string;
  usageInstructions: string;

  metadataTitle: string;
  metadataSlug: string;
  metadataSummary: string;
  slugError: string | null;

  selectedProfessionIds: string[];
  selectedCategoryIds: string[];

  canEditTaxonomy: boolean;
  canEditMaintainers: boolean;
  canEditSlug: boolean;
  canRollbackVersions: boolean;
  isWorkflowSubmitting: boolean;

  isSaving: boolean;
  hasDirtyChanges: boolean;

  isDrawerOpen: boolean;
  isHistoryDrawerOpen: boolean;
  isMetadataDrawerOpen: boolean;
  isMaintainersDrawerOpen: boolean;
  isInstructionsDrawerOpen: boolean;

  professions: ProfessionItem[];
  categories: CategoryItem[];
  taxonomyError: string | null;
  isTaxonomyLoading: boolean;
  isSavingAllMetadata: boolean;

  maintainers: MaintainerSummary[];
  ownerUserId: string | null;
  isMaintainersLoading: boolean;
  isMaintainersSaving: boolean;
  maintainersError: string | null;
};

const props = defineProps<EditorWorkspacePanelProps>();

const emit = defineEmits<{
  (event: "save"): void;
  (event: "openHistoryDrawer"): void;
  (event: "openMetadataDrawer"): void;
  (event: "openMaintainersDrawer"): void;
  (event: "openInstructionsDrawer"): void;
  (event: "closeDrawer"): void;
  (event: "selectHistoryVersion", versionId: string): void;
  (event: "rollbackVersion", versionId: string): void;
  (event: "saveAllMetadata"): void;
  (event: "suggestSlugFromTitle"): void;
  (event: "addMaintainer", email: string): void;
  (event: "removeMaintainer", userId: string): void;
  (event: "update:changeSummary", value: string): void;
  (event: "update:entrypoint", value: string): void;
  (event: "update:sourceCode", value: string): void;
  (event: "update:settingsSchemaText", value: string): void;
  (event: "update:inputSchemaText", value: string): void;
  (event: "update:usageInstructions", value: string): void;
  (event: "update:metadataTitle", value: string): void;
  (event: "update:metadataSlug", value: string): void;
  (event: "update:metadataSummary", value: string): void;
  (event: "update:slugError", value: string | null): void;
  (event: "update:taxonomyError", value: string | null): void;
  (event: "update:maintainersError", value: string | null): void;
  (event: "update:selectedProfessionIds", value: string[]): void;
  (event: "update:selectedCategoryIds", value: string[]): void;
}>();

const entrypointName = computed(() => props.entrypoint);
const { extensions: intelligenceExtensions } = useSkriptoteketIntelligenceExtensions({
  entrypointName,
});
</script>

<template>
  <div class="border border-navy bg-white shadow-brutal-sm">
    <!-- Control row -->
    <div class="p-4 border-b border-navy/20">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <!-- Save group: Spara + Osparat + Ändringssammanfattning -->
        <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-3">
          <div class="flex items-center gap-2">
            <button
              type="button"
              :disabled="isSaving"
              class="btn-primary min-w-[80px]"
              @click="emit('save')"
            >
              <span
                v-if="isSaving"
                class="inline-block w-3 h-3 border-2 border-canvas/30 border-t-canvas rounded-full animate-spin"
              />
              <span v-else>Spara</span>
            </button>
            <span
              v-if="hasDirtyChanges"
              class="text-xs text-burgundy font-semibold uppercase tracking-wide"
            >
              Osparat
            </span>
          </div>

          <div class="min-w-[180px] max-w-xs space-y-1">
            <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
              Ändringssammanfattning
            </label>
            <input
              :value="changeSummary"
              class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
              placeholder="T.ex. fixade bugg..."
              @input="emit('update:changeSummary', ($event.target as HTMLInputElement).value)"
            >
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
            @click="emit('openHistoryDrawer')"
          >
            Öppna sparade
          </button>
          <button
            v-if="canEditTaxonomy"
            type="button"
            class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
            @click="emit('openMetadataDrawer')"
          >
            Metadata
          </button>
          <button
            v-if="canEditMaintainers"
            type="button"
            class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
            @click="emit('openMaintainersDrawer')"
          >
            Redigeringsbehörigheter
          </button>
          <button
            type="button"
            class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
            @click="emit('openInstructionsDrawer')"
          >
            Instruktioner
          </button>
        </div>
      </div>
    </div>

    <div
      :class="[
        'grid',
        isDrawerOpen ? 'md:grid-cols-[minmax(0,1fr)_400px]' : 'md:grid-cols-[minmax(0,1fr)]',
      ]"
    >
      <div class="p-4 space-y-4 min-w-0">
        <!-- Source code -->
        <div class="space-y-3">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
            Källkod
          </h2>
          <div class="h-[420px] border border-navy bg-canvas shadow-brutal-sm overflow-hidden">
            <Suspense>
              <template #default>
                <CodeMirrorEditor
                  :model-value="sourceCode"
                  :extensions="intelligenceExtensions"
                  @update:model-value="emit('update:sourceCode', $event)"
                />
              </template>
              <template #fallback>
                <div class="h-full w-full flex items-center justify-center gap-3 text-sm text-navy/70">
                  <span
                    class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin"
                  />
                  <span>Laddar kodredigerare...</span>
                </div>
              </template>
            </Suspense>
          </div>
        </div>

        <div class="border-t border-navy/20 pt-4 space-y-3">
          <div class="space-y-1">
            <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
              Inställningar (schema)
            </h2>
            <p class="text-sm text-navy/60">
              Valfritt. Ange en JSON-array av fält (samma typer som UI Actions: string, text,
              integer, number, boolean, enum, multi_enum).
            </p>
          </div>

          <label
            for="tool-settings-schema"
            class="text-xs font-semibold uppercase tracking-wide text-navy/70"
          >
            Schema (JSON)
          </label>
          <textarea
            id="tool-settings-schema"
            :value="settingsSchemaText"
            rows="10"
            class="w-full border border-navy bg-white px-3 py-2 text-sm font-mono text-navy shadow-brutal-sm"
            placeholder="[{&quot;name&quot;:&quot;theme_color&quot;,&quot;label&quot;:&quot;Färgtema&quot;,&quot;kind&quot;:&quot;string&quot;}]"
            @input="emit('update:settingsSchemaText', ($event.target as HTMLTextAreaElement).value)"
          />
        </div>

        <div class="border-t border-navy/20 pt-4 space-y-3">
          <div class="space-y-1">
            <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
              Indata (input_schema)
            </h2>
            <p class="text-sm text-navy/60">
              Valfritt. Ange en JSON-array av fält som visas innan körning (string, text, integer,
              number, boolean, enum, file). V1: max 1 file-fält och file-fält kräver min/max.
            </p>
          </div>

          <label
            for="tool-input-schema"
            class="text-xs font-semibold uppercase tracking-wide text-navy/70"
          >
            Schema (JSON)
          </label>
          <textarea
            id="tool-input-schema"
            :value="inputSchemaText"
            rows="10"
            class="w-full border border-navy bg-white px-3 py-2 text-sm font-mono text-navy shadow-brutal-sm"
            placeholder="[{&quot;name&quot;:&quot;title&quot;,&quot;label&quot;:&quot;Titel&quot;,&quot;kind&quot;:&quot;string&quot;}]"
            @input="emit('update:inputSchemaText', ($event.target as HTMLTextAreaElement).value)"
          />
        </div>

        <!-- Test section -->
        <div class="border-t border-navy/20 pt-4 space-y-3">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
            Testkör kod
          </h2>

          <!-- Entrypoint + file picker + run button -->
          <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
            <EntrypointDropdown
              :model-value="entrypoint"
              :options="entrypointOptions"
              @update:model-value="emit('update:entrypoint', $event)"
            />
          </div>

          <Suspense v-if="selectedVersion">
            <template #default>
              <SandboxRunner
                :version-id="selectedVersion.id"
                :tool-id="toolId"
              />
            </template>
            <template #fallback>
              <div class="flex items-center gap-3 p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70">
                <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
                <span>Laddar testkörning...</span>
              </div>
            </template>
          </Suspense>
          <p
            v-else
            class="text-sm text-navy/60"
          >
            Spara ett utkast för att kunna testa.
          </p>
        </div>
      </div>

      <!-- Drawers -->
      <VersionHistoryDrawer
        v-if="isHistoryDrawerOpen"
        :is-open="isHistoryDrawerOpen"
        :versions="versions"
        :active-version-id="selectedVersion?.id"
        :can-rollback="canRollbackVersions"
        :is-submitting="isWorkflowSubmitting"
        @close="emit('closeDrawer')"
        @select="emit('selectHistoryVersion', $event)"
        @rollback="emit('rollbackVersion', $event)"
      />

      <MetadataDrawer
        v-if="isMetadataDrawerOpen"
        :is-open="isMetadataDrawerOpen"
        :metadata-title="metadataTitle"
        :metadata-slug="metadataSlug"
        :metadata-summary="metadataSummary"
        :can-edit-slug="canEditSlug"
        :slug-error="slugError"
        :professions="professions"
        :categories="categories"
        :selected-profession-ids="selectedProfessionIds"
        :selected-category-ids="selectedCategoryIds"
        :taxonomy-error="taxonomyError"
        :is-loading="isTaxonomyLoading"
        :is-saving="isSavingAllMetadata"
        @close="emit('closeDrawer')"
        @save="emit('saveAllMetadata')"
        @update:metadata-title="emit('update:metadataTitle', $event)"
        @update:metadata-slug="emit('update:metadataSlug', $event)"
        @update:metadata-summary="emit('update:metadataSummary', $event)"
        @update:slug-error="emit('update:slugError', $event)"
        @suggest-slug-from-title="emit('suggestSlugFromTitle')"
        @update:selected-profession-ids="emit('update:selectedProfessionIds', $event)"
        @update:selected-category-ids="emit('update:selectedCategoryIds', $event)"
        @update:taxonomy-error="emit('update:taxonomyError', $event)"
      />

      <MaintainersDrawer
        v-if="isMaintainersDrawerOpen"
        :is-open="isMaintainersDrawerOpen"
        :maintainers="maintainers"
        :owner-user-id="ownerUserId"
        :is-superuser="canRollbackVersions"
        :is-loading="isMaintainersLoading"
        :is-saving="isMaintainersSaving"
        :error="maintainersError"
        @close="emit('closeDrawer')"
        @add="emit('addMaintainer', $event)"
        @remove="emit('removeMaintainer', $event)"
        @update:error="emit('update:maintainersError', $event)"
      />

      <InstructionsDrawer
        v-if="isInstructionsDrawerOpen"
        :is-open="isInstructionsDrawerOpen"
        :usage-instructions="usageInstructions"
        :is-saving="isSaving"
        @close="emit('closeDrawer')"
        @save="emit('save')"
        @update:usage-instructions="emit('update:usageInstructions', $event)"
      />
    </div>
  </div>
</template>
