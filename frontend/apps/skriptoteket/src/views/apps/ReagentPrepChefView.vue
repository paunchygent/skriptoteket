<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiGet, isApiError } from "../../api/client";
import VaultPickerModal from "../../components/vault/VaultPickerModal.vue";
import { useToast } from "../../composables/useToast";
import { useReagentPrepChefDefaults } from "../../composables/reagentPrepChef/useReagentPrepChefDefaults";
import { useReagentPrepChefForm } from "../../composables/reagentPrepChef/useReagentPrepChefForm";
import { useReagentPrepChefPrep } from "../../composables/reagentPrepChef/useReagentPrepChefPrep";
import { useReagentPrepChefRisk } from "../../composables/reagentPrepChef/useReagentPrepChefRisk";
import ReagentPrepChefStepClass from "./reagent-prep-chef/ReagentPrepChefStepClass.vue";
import ReagentPrepChefStepReagent from "./reagent-prep-chef/ReagentPrepChefStepReagent.vue";
import ReagentPrepChefStepResult from "./reagent-prep-chef/ReagentPrepChefStepResult.vue";
import ReagentPrepChefStepRisk from "./reagent-prep-chef/ReagentPrepChefStepRisk.vue";
import ReagentPrepChefStepSource from "./reagent-prep-chef/ReagentPrepChefStepSource.vue";
import ReagentPrepChefSdsModal from "./reagent-prep-chef/ReagentPrepChefSdsModal.vue";
import ReagentPrepChefSettingsPopover from "./reagent-prep-chef/ReagentPrepChefSettingsPopover.vue";

import type {
  AppDetailResponse,
  ReagentPrepChefChemicalOption,
  ReagentPrepChefChemicalsResult,
  StepId,
} from "./reagent-prep-chef/types";

const route = useRoute();
const toast = useToast();

const appId = computed(() => {
  const param = route.params.appId;
  return typeof param === "string" ? param : "";
});

const apiPrefix = computed(() => `/api/v1/apps/${encodeURIComponent(appId.value)}`);

const app = ref<AppDetailResponse | null>(null);
const chemicals = ref<ReagentPrepChefChemicalOption[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);
const actionErrorMessage = ref<string | null>(null);
const step = ref<StepId>("reagent");

const {
  form,
  selectedChemicalKey,
  chemicalQuery,
  chemicalSearchIsActive,
  chemicalSearchResults,
  derivedGroups,
  derivedTotalVolumeMl,
  canCalculate,
  applyDefaults,
  buildRequestPayload,
  loadDraft,
  saveDraft,
  clearDraft,
  resetForm,
  resetSelection,
  selectChemicalFromSearch,
} = useReagentPrepChefForm(chemicals);

const {
  prep,
  isCalculating,
  isExporting,
  isSavingPdfToVault,
  lastSavedPdfVaultRef,
  instructions,
  warnings,
  safety,
  safetyPpe,
  canExport,
  currentPrepPayload,
  calculate,
  exportPdf,
  savePdfToVault,
  resetPrep,
} = useReagentPrepChefPrep({
  apiPrefix,
  form,
  canCalculate,
  buildRequestPayload,
  actionErrorMessage,
});

const {
  defaults,
  isDefaultsLoading,
  isDefaultsSaving,
  isSavingDefaultsToVault,
  lastSavedDefaultsVaultRef,
  isLoadingDefaultsFromVault,
  isDefaultsVaultPickerOpen,
  defaultsVaultPickerDraft,
  fetchDefaults,
  saveDefaults,
  clearDefaults,
  saveDefaultsToVault,
  openDefaultsVaultPicker,
  closeDefaultsVaultPicker,
  onDefaultsVaultPickerConfirm,
} = useReagentPrepChefDefaults({
  apiPrefix,
  canCalculate,
  buildRequestPayload,
  applyDefaults,
  actionErrorMessage,
});

const {
  riskDraft,
  riskWarnings,
  isRiskLoading,
  isRiskSaving,
  isRiskExporting,
  isSavingRiskPdfToVault,
  lastSavedRiskPdfVaultRef,
  riskErrorMessage,
  riskContext,
  riskOverrides,
  riskMeasuresDraft,
  riskContextIsComplete,
  canExportRisk,
  loadRiskDraft,
  updateRiskMeasures,
  exportRiskPdf,
  saveRiskPdfToVault,
  openSds,
  closeSds,
  isSdsModalOpen,
  isSdsLoading,
  sdsDocument,
  resetRiskState,
} = useReagentPrepChefRisk({
  apiPrefix,
  prep,
  currentPrepPayload,
});

const sdsModalTitle = computed(() => {
  const ref = sdsDocument.value?.sds_ref;
  return ref ? `SDS: ${ref}` : "SDS";
});

const sdsPdfUrl = computed(() => {
  const ref = sdsDocument.value?.sds_ref;
  if (!ref || !sdsDocument.value?.pdf_available) return null;
  return `${apiPrefix.value}/sds/${encodeURIComponent(ref)}`;
});

function loadDefaultsIntoForm(): void {
  const preset = defaults.value?.defaults ?? null;
  if (!preset) {
    toast.info("Inga standardinställningar sparade än.");
    return;
  }
  applyDefaults(preset);
  toast.success("Standardinställningar laddade.");
}

async function fetchApp(): Promise<void> {
  app.value = await apiGet<AppDetailResponse>(
    `/api/v1/apps/${encodeURIComponent(appId.value)}`,
  );
}

async function fetchChemicals(): Promise<void> {
  const response = await apiGet<ReagentPrepChefChemicalsResult>(`${apiPrefix.value}/chemicals`);
  chemicals.value = response.chemicals ?? [];
}

async function load(): Promise<void> {
  if (!appId.value) {
    errorMessage.value = "Saknar app-id i länken.";
    isLoading.value = false;
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;
  actionErrorMessage.value = null;
  app.value = null;
  chemicals.value = [];
  resetPrep();
  resetRiskState();

  try {
    await fetchApp();
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda appen.";
    }
    isLoading.value = false;
    return;
  }

  try {
    await fetchChemicals();
  } catch (error: unknown) {
    errorMessage.value = isApiError(error) ? error.message : "Det gick inte att ladda kemilistan.";
  }

  try {
    await fetchDefaults();
  } catch {
    // Defaults are optional; ignore load failures.
  } finally {
    isLoading.value = false;
  }
}

watch(appId, () => {
  void load();
});

watch(step, (next) => {
  saveDraft();
  if (next === "risk" && prep.value) {
    void loadRiskDraft();
  }
});

async function handleCalculate(): Promise<void> {
  const ok = await calculate();
  if (!ok) return;
  resetRiskState();
  step.value = "result";
}

function resetAll(): void {
  resetPrep();
  resetRiskState();
  resetSelection();
  resetForm();
  step.value = "reagent";
  actionErrorMessage.value = null;
  lastSavedPdfVaultRef.value = null;
  lastSavedRiskPdfVaultRef.value = null;
  lastSavedDefaultsVaultRef.value = null;
  clearDraft();
}

function goTo(nextStep: StepId): void {
  step.value = nextStep;
}

onMounted(() => {
  loadDraft();
  void load();
});
</script>

<template>
  <div class="max-w-[52rem] space-y-6">
    <div class="flex items-center gap-3 text-sm text-navy/70">
      <RouterLink
        to="/browse"
        class="underline hover:text-burgundy"
      >
        ← Tillbaka till katalog
      </RouterLink>
      <span class="px-2 py-1 border border-navy bg-white shadow-brutal-sm uppercase tracking-wide font-semibold">
        Kurerad app
      </span>

      <ReagentPrepChefSettingsPopover
        :can-calculate="canCalculate"
        :is-defaults-saving="isDefaultsSaving"
        :is-defaults-loading="isDefaultsLoading"
        :defaults="defaults"
        :is-saving-defaults-to-vault="isSavingDefaultsToVault"
        :is-loading-defaults-from-vault="isLoadingDefaultsFromVault"
        :last-saved-defaults-vault-ref="lastSavedDefaultsVaultRef"
        @save-defaults="saveDefaults"
        @load-defaults="loadDefaultsIntoForm"
        @clear-defaults="clearDefaults"
        @save-defaults-to-vault="saveDefaultsToVault"
        @open-defaults-vault-picker="openDefaultsVaultPicker"
      />
    </div>

    <header class="space-y-2">
      <h1 class="page-title">{{ app?.title ?? (isLoading ? "Laddar..." : "Reagensberedning") }}</h1>
      <p
        v-if="app?.summary"
        class="page-description"
      >
        {{ app.summary }}
      </p>
    </header>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-navy/70 text-sm"
    >
      Laddar...
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
    >
      {{ errorMessage }}
    </div>

    <template v-else>
      <div class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/80 space-y-2">
        <p class="font-semibold">Säkerhet</p>
        <p>
          Den här appen ger endast råd för ämnen i listan. Om ämnet saknas: konsultera alltid SDS och lokala rutiner.
        </p>
      </div>

      <nav class="flex flex-wrap gap-2 text-xs">
        <button
          type="button"
          class="px-3 py-2 border border-navy shadow-brutal-sm uppercase tracking-wide font-semibold"
          :class="step === 'reagent' ? 'bg-navy text-canvas' : 'bg-white hover:bg-canvas'"
          @click="goTo('reagent')"
        >
          1. Ämne
        </button>
        <button
          type="button"
          class="px-3 py-2 border border-navy shadow-brutal-sm uppercase tracking-wide font-semibold"
          :class="step === 'class' ? 'bg-navy text-canvas' : 'bg-white hover:bg-canvas'"
          @click="goTo('class')"
        >
          2. Klass
        </button>
        <button
          type="button"
          class="px-3 py-2 border border-navy shadow-brutal-sm uppercase tracking-wide font-semibold"
          :class="step === 'source' ? 'bg-navy text-canvas' : 'bg-white hover:bg-canvas'"
          @click="goTo('source')"
        >
          3. Källa
        </button>
        <button
          type="button"
          class="px-3 py-2 border border-navy shadow-brutal-sm uppercase tracking-wide font-semibold"
          :class="step === 'result' ? 'bg-navy text-canvas' : 'bg-white hover:bg-canvas'"
          :disabled="prep === null"
          @click="goTo('result')"
        >
          4. Resultat
        </button>
        <button
          type="button"
          class="px-3 py-2 border border-navy shadow-brutal-sm uppercase tracking-wide font-semibold"
          :class="step === 'risk' ? 'bg-navy text-canvas' : 'bg-white hover:bg-canvas'"
          :disabled="prep === null"
          @click="goTo('risk')"
        >
          5. Riskbedömning
        </button>
      </nav>

      <ReagentPrepChefStepReagent
        v-if="step === 'reagent'"
        v-model:form="form"
        v-model:selected-chemical-key="selectedChemicalKey"
        v-model:chemical-query="chemicalQuery"
        :chemicals="chemicals"
        :chemical-search-is-active="chemicalSearchIsActive"
        :chemical-search-results="chemicalSearchResults"
        @select-chemical="selectChemicalFromSearch"
        @next="goTo('class')"
      />

      <ReagentPrepChefStepClass
        v-else-if="step === 'class'"
        v-model:form="form"
        :derived-groups="derivedGroups"
        :derived-total-volume-ml="derivedTotalVolumeMl"
        @back="goTo('reagent')"
        @next="goTo('source')"
      />

      <ReagentPrepChefStepSource
        v-else-if="step === 'source'"
        v-model:form="form"
        :is-calculating="isCalculating"
        :is-exporting="isExporting"
        :can-calculate="canCalculate"
        :action-error-message="actionErrorMessage"
        @back="goTo('class')"
        @calculate="handleCalculate"
        @reset="resetAll"
      />

      <ReagentPrepChefStepResult
        v-else-if="step === 'result' && prep"
        :prep="prep"
        :instructions="instructions"
        :warnings="warnings"
        :safety="safety"
        :safety-ppe="safetyPpe"
        :is-exporting="isExporting"
        :is-saving-pdf-to-vault="isSavingPdfToVault"
        :can-export="canExport"
        :last-saved-pdf-vault-ref="lastSavedPdfVaultRef"
        :action-error-message="actionErrorMessage"
        @back="goTo('source')"
        @export="exportPdf"
        @save="savePdfToVault"
        @reset="resetAll"
      />

      <ReagentPrepChefStepRisk
        v-else-if="step === 'risk'"
        v-model:risk-context="riskContext"
        v-model:risk-overrides="riskOverrides"
        v-model:risk-measures-draft="riskMeasuresDraft"
        :risk-draft="riskDraft"
        :risk-warnings="riskWarnings"
        :is-risk-loading="isRiskLoading"
        :is-risk-saving="isRiskSaving"
        :is-risk-exporting="isRiskExporting"
        :is-saving-risk-pdf-to-vault="isSavingRiskPdfToVault"
        :last-saved-risk-pdf-vault-ref="lastSavedRiskPdfVaultRef"
        :risk-error-message="riskErrorMessage"
        :risk-context-is-complete="riskContextIsComplete"
        :can-export-risk="canExportRisk"
        @refresh="loadRiskDraft"
        @open-sds="openSds"
        @update-measures="updateRiskMeasures"
        @back="goTo('result')"
        @export="exportRiskPdf"
        @save="saveRiskPdfToVault"
      />
    </template>

    <VaultPickerModal
      :is-open="isDefaultsVaultPickerOpen"
      title="Välj inställningsfil från Mina filer"
      :selected-refs="defaultsVaultPickerDraft"
      :max-selected="1"
      confirm-label="Ladda"
      :is-read-only="isLoadingDefaultsFromVault"
      @close="closeDefaultsVaultPicker"
      @confirm="onDefaultsVaultPickerConfirm"
    />

    <ReagentPrepChefSdsModal
      :is-open="isSdsModalOpen"
      :is-loading="isSdsLoading"
      :title="sdsModalTitle"
      :provider="sdsDocument?.provider ?? null"
      :revision="sdsDocument?.revision ?? null"
      :markdown="sdsDocument?.markdown ?? null"
      :pdf-url="sdsPdfUrl"
      @close="closeSds"
    />
  </div>
</template>
