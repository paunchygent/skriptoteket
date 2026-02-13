import { computed, ref } from "vue";

import type { Ref } from "vue";

import { apiFetchBlob, apiPost, isApiError } from "../../api/client";
import { useToast } from "../useToast";

import type {
  ReagentPrepChefFormState,
  ReagentPrepChefPrepRequestInput,
  ReagentPrepChefPrepResult,
  ReagentPrepChefPrepSheet,
  ReagentPrepChefSavePdfResult,
} from "../../views/apps/reagent-prep-chef/types";

type PrepOptions = {
  apiPrefix: Ref<string>;
  form: ReagentPrepChefFormState;
  canCalculate: Ref<boolean>;
  buildRequestPayload: () => ReagentPrepChefPrepRequestInput;
  actionErrorMessage: Ref<string | null>;
};

export function useReagentPrepChefPrep(options: PrepOptions) {
  const toast = useToast();
  const prep = ref<ReagentPrepChefPrepSheet | null>(null);
  const lastPrepRequest = ref<ReagentPrepChefPrepRequestInput | null>(null);
  const isCalculating = ref(false);
  const isExporting = ref(false);
  const isSavingPdfToVault = ref(false);
  const lastSavedPdfVaultRef = ref<string | null>(null);

  const instructions = computed(() => prep.value?.instructions ?? []);
  const warnings = computed(() => prep.value?.warnings ?? []);
  const safety = computed(() => prep.value?.safety ?? null);
  const safetyPpe = computed(() => safety.value?.ppe ?? []);
  const canExport = computed(() => prep.value !== null && options.canCalculate.value);

  function currentPrepPayload(): ReagentPrepChefPrepRequestInput {
    return lastPrepRequest.value ?? options.buildRequestPayload();
  }

  async function calculate(): Promise<boolean> {
    if (!options.canCalculate.value) return false;
    if (isCalculating.value) return false;

    isCalculating.value = true;
    options.actionErrorMessage.value = null;

    try {
      const payload = options.buildRequestPayload();
      const response = await apiPost<ReagentPrepChefPrepResult>(
        `${options.apiPrefix.value}/prep`,
        payload,
      );
      prep.value = response.sheet;
      lastPrepRequest.value = payload;
      return true;
    } catch (error: unknown) {
      if (isApiError(error)) {
        options.actionErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        options.actionErrorMessage.value = error.message;
      } else {
        options.actionErrorMessage.value = "Det gick inte att beräkna just nu.";
      }
      return false;
    } finally {
      isCalculating.value = false;
    }
  }

  async function exportPdf(): Promise<void> {
    if (!canExport.value) return;
    if (isExporting.value) return;

    isExporting.value = true;
    options.actionErrorMessage.value = null;

    try {
      const blob = await apiFetchBlob(`${options.apiPrefix.value}/export-pdf`, {
        method: "POST",
        body: currentPrepPayload(),
        headers: { Accept: "application/pdf" },
      });

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "reagensberedning.pdf";
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error: unknown) {
      if (isApiError(error)) {
        options.actionErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        options.actionErrorMessage.value = error.message;
      } else {
        options.actionErrorMessage.value = "Det gick inte att exportera PDF just nu.";
      }
    } finally {
      isExporting.value = false;
    }
  }

  function defaultVaultPdfName(): string {
    const formula = prep.value?.chemistry.formula_clean?.trim() ?? options.form.chemicalFormula.trim();
    if (!formula) return "reagensberedning.pdf";
    return `reagensberedning-${formula}.pdf`;
  }

  async function savePdfToVault(): Promise<void> {
    if (!canExport.value) return;
    if (isSavingPdfToVault.value) return;

    isSavingPdfToVault.value = true;
    options.actionErrorMessage.value = null;

    try {
      const response = await apiPost<ReagentPrepChefSavePdfResult>(
        `${options.apiPrefix.value}/save-pdf`,
        {
          prep: currentPrepPayload(),
          name: defaultVaultPdfName(),
        },
      );
      lastSavedPdfVaultRef.value = response.file.ref;
      toast.success("PDF sparad i Mina filer.");
    } catch (error: unknown) {
      if (isApiError(error)) {
        options.actionErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        options.actionErrorMessage.value = error.message;
      } else {
        options.actionErrorMessage.value = "Det gick inte att spara PDF i Mina filer just nu.";
      }
    } finally {
      isSavingPdfToVault.value = false;
    }
  }

  function resetPrep(): void {
    prep.value = null;
    lastPrepRequest.value = null;
    lastSavedPdfVaultRef.value = null;
  }

  return {
    prep,
    lastPrepRequest,
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
  };
}
