import { computed, nextTick, reactive, ref, watch } from "vue";

import type { Ref } from "vue";

import { apiFetchBlob, apiGet, apiPost, isApiError } from "../../api/client";
import { useToast } from "../useToast";

import type {
  ReagentPrepChefPrepSheet,
  ReagentPrepChefPrepRequestInput,
  ReagentPrepChefRiskAssessmentInputs,
  ReagentPrepChefRiskAssessmentRequest,
  ReagentPrepChefRiskAssessmentResult,
  ReagentPrepChefRiskContext,
  ReagentPrepChefRiskItemOverride,
  ReagentPrepChefSdsMarkdownResult,
  ReagentPrepChefSavePdfResult,
  RiskOverrideDraft,
} from "../../views/apps/reagent-prep-chef/types";

type RiskOptions = {
  apiPrefix: Ref<string>;
  prep: Ref<ReagentPrepChefPrepSheet | null>;
  currentPrepPayload: () => ReagentPrepChefPrepRequestInput;
};

export function useReagentPrepChefRisk(options: RiskOptions) {
  const toast = useToast();
  const riskDraft = ref<ReagentPrepChefRiskAssessmentResult["draft"] | null>(null);
  const riskWarnings = ref<string[]>([]);
  const riskStateRev = ref(0);
  const isRiskLoading = ref(false);
  const isRiskSaving = ref(false);
  const isRiskExporting = ref(false);
  const isSavingRiskPdfToVault = ref(false);
  const lastSavedRiskPdfVaultRef = ref<string | null>(null);
  const riskErrorMessage = ref<string | null>(null);
  const riskInitialized = ref(false);
  const riskSaveTimerId = ref<number | null>(null);

  const isSdsModalOpen = ref(false);
  const isSdsLoading = ref(false);
  const sdsDocument = ref<ReagentPrepChefSdsMarkdownResult | null>(null);

  const riskContext = reactive<ReagentPrepChefRiskContext>({
    scope: "",
    location: "",
    participants: "",
    approver: "",
    assessment_date: null,
    next_review_date: null,
    local_routines: "",
  });

  const riskOverrides = reactive<Record<string, RiskOverrideDraft>>({});
  const riskMeasuresDraft = reactive<Record<string, string>>({});

  const riskContextIsComplete = computed(() => {
    if (!riskDraft.value) return false;
    return (riskDraft.value.export_gate?.missing_context_fields?.length ?? 0) === 0;
  });

  const canExportRisk = computed(() => {
    if (!riskDraft.value) return false;
    return Boolean(riskDraft.value.export_gate?.ready);
  });

  function resetRiskState(): void {
    riskDraft.value = null;
    riskWarnings.value = [];
    riskStateRev.value = 0;
    riskErrorMessage.value = null;
    riskInitialized.value = false;
    isSdsModalOpen.value = false;
    isSdsLoading.value = false;
    sdsDocument.value = null;
    if (riskSaveTimerId.value !== null) {
      window.clearTimeout(riskSaveTimerId.value);
      riskSaveTimerId.value = null;
    }
    for (const key of Object.keys(riskOverrides)) {
      delete riskOverrides[key];
    }
    for (const key of Object.keys(riskMeasuresDraft)) {
      delete riskMeasuresDraft[key];
    }
    riskContext.scope = "";
    riskContext.location = "";
    riskContext.participants = "";
    riskContext.approver = "";
    riskContext.assessment_date = null;
    riskContext.next_review_date = null;
    riskContext.local_routines = "";
  }

  function buildRiskInputs(): ReagentPrepChefRiskAssessmentInputs {
    const overrides = (riskDraft.value?.risks ?? []).map<ReagentPrepChefRiskItemOverride>(
      (risk) => {
        const override = riskOverrides[risk.id];
        return {
          id: risk.id,
          measures: override?.measures ?? null,
          confirmed: override?.confirmed ?? false,
        };
      },
    );

    const context: ReagentPrepChefRiskContext = {
      scope: riskContext.scope?.trim() || null,
      location: riskContext.location?.trim() || null,
      participants: riskContext.participants?.trim() || null,
      approver: riskContext.approver?.trim() || null,
      assessment_date: riskContext.assessment_date || null,
      next_review_date: riskContext.next_review_date || null,
      local_routines: riskContext.local_routines?.trim() || null,
    };

    return { context, overrides };
  }

  async function applyRiskResult(result: ReagentPrepChefRiskAssessmentResult): Promise<void> {
    riskInitialized.value = false;
    riskDraft.value = result.draft;
    riskWarnings.value = result.warnings ?? [];
    riskStateRev.value = result.state_rev;

    const context = result.draft.context;
    riskContext.scope = context?.scope ?? "";
    riskContext.location = context?.location ?? "";
    riskContext.participants = context?.participants ?? "";
    riskContext.approver = context?.approver ?? "";
    riskContext.assessment_date = context?.assessment_date ?? null;
    riskContext.next_review_date = context?.next_review_date ?? null;
    riskContext.local_routines = context?.local_routines ?? "";

    for (const key of Object.keys(riskOverrides)) {
      delete riskOverrides[key];
    }
    for (const key of Object.keys(riskMeasuresDraft)) {
      delete riskMeasuresDraft[key];
    }

    for (const item of result.draft.risks) {
      const measures = item.measures ?? [];
      riskOverrides[item.id] = {
        id: item.id,
        measures: [...measures],
        confirmed: item.confirmed,
      };
      riskMeasuresDraft[item.id] = measures.join("\n");
    }

    await nextTick();
    riskInitialized.value = true;
  }

  async function loadRiskDraft(): Promise<void> {
    if (!options.prep.value) {
      riskErrorMessage.value = "Beräkna först ett resultat.";
      return;
    }
    if (isRiskLoading.value) return;

    isRiskLoading.value = true;
    riskErrorMessage.value = null;

    try {
      const response = await apiPost<ReagentPrepChefRiskAssessmentResult>(
        `${options.apiPrefix.value}/risk-assessment`,
        {
          prep: options.currentPrepPayload(),
        },
      );
      await applyRiskResult(response);
    } catch (error: unknown) {
      if (isApiError(error)) {
        riskErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        riskErrorMessage.value = error.message;
      } else {
        riskErrorMessage.value = "Det gick inte att hämta riskutkast just nu.";
      }
    } finally {
      isRiskLoading.value = false;
    }
  }

  function scheduleRiskSave(): void {
    if (!riskInitialized.value) return;
    if (riskSaveTimerId.value !== null) {
      window.clearTimeout(riskSaveTimerId.value);
    }
    riskSaveTimerId.value = window.setTimeout(() => {
      riskSaveTimerId.value = null;
      void saveRiskDraft();
    }, 600);
  }

  async function saveRiskDraft(): Promise<void> {
    if (!options.prep.value || !riskDraft.value) return;
    if (isRiskSaving.value) return;

    isRiskSaving.value = true;
    riskErrorMessage.value = null;

    const payload: ReagentPrepChefRiskAssessmentRequest = {
      prep: options.currentPrepPayload(),
      expected_state_rev: riskStateRev.value,
      inputs: buildRiskInputs(),
      reset: false,
    };

    try {
      const response = await apiPost<ReagentPrepChefRiskAssessmentResult>(
        `${options.apiPrefix.value}/risk-assessment`,
        payload,
      );
      await applyRiskResult(response);
    } catch (error: unknown) {
      if (isApiError(error)) {
        riskErrorMessage.value =
          error.status === 409
            ? "Riskutkastet ändrades i en annan flik. Ladda om och försök igen."
            : error.message;
      } else if (error instanceof Error) {
        riskErrorMessage.value = error.message;
      } else {
        riskErrorMessage.value = "Det gick inte att spara riskutkast just nu.";
      }
    } finally {
      isRiskSaving.value = false;
    }
  }

  function updateRiskMeasures(riskId: string): void {
    const raw = riskMeasuresDraft[riskId] ?? "";
    const measures = raw
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    if (!riskOverrides[riskId]) {
      riskOverrides[riskId] = {
        id: riskId,
        measures,
        confirmed: false,
      };
    } else {
      riskOverrides[riskId].measures = measures;
    }
    scheduleRiskSave();
  }

  async function exportRiskPdf(): Promise<void> {
    if (!riskDraft.value || !canExportRisk.value) return;
    if (isRiskExporting.value) return;

    isRiskExporting.value = true;
    riskErrorMessage.value = null;

    try {
      const blob = await apiFetchBlob(`${options.apiPrefix.value}/export-risk-pdf`, {
        method: "POST",
        body: {
          prep: options.currentPrepPayload(),
          expected_state_rev: riskStateRev.value,
          inputs: buildRiskInputs(),
        },
        headers: { Accept: "application/pdf" },
      });

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "riskbedomning.pdf";
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error: unknown) {
      if (isApiError(error)) {
        riskErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        riskErrorMessage.value = error.message;
      } else {
        riskErrorMessage.value = "Det gick inte att exportera riskbedömningen just nu.";
      }
    } finally {
      isRiskExporting.value = false;
    }
  }

  async function saveRiskPdfToVault(): Promise<void> {
    if (!riskDraft.value || !canExportRisk.value) return;
    if (isSavingRiskPdfToVault.value) return;

    isSavingRiskPdfToVault.value = true;
    riskErrorMessage.value = null;

    try {
      const response = await apiPost<ReagentPrepChefSavePdfResult>(
        `${options.apiPrefix.value}/save-risk-pdf`,
        {
          prep: options.currentPrepPayload(),
          expected_state_rev: riskStateRev.value,
          inputs: buildRiskInputs(),
        },
      );
      lastSavedRiskPdfVaultRef.value = response.file.ref;
      toast.success("Riskbedömningen sparades i Mina filer.");
    } catch (error: unknown) {
      if (isApiError(error)) {
        riskErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        riskErrorMessage.value = error.message;
      } else {
        riskErrorMessage.value = "Det gick inte att spara riskbedömningen just nu.";
      }
    } finally {
      isSavingRiskPdfToVault.value = false;
    }
  }

  async function openSds(): Promise<void> {
    const sds = riskDraft.value?.sds;
    if (!sds?.markdown_available || !sds.sds_ref) {
      toast.failure("SDS saknas offline.");
      return;
    }
    if (isSdsLoading.value) return;

    isSdsLoading.value = true;
    riskErrorMessage.value = null;

    try {
      sdsDocument.value = await apiGet<ReagentPrepChefSdsMarkdownResult>(
        `${options.apiPrefix.value}/sds/${encodeURIComponent(sds.sds_ref)}/markdown`,
      );
      isSdsModalOpen.value = true;
    } catch (error: unknown) {
      if (isApiError(error)) {
        toast.failure(error.message);
      } else if (error instanceof Error) {
        toast.failure(error.message);
      } else {
        toast.failure("Det gick inte att öppna SDS just nu.");
      }
    } finally {
      isSdsLoading.value = false;
    }
  }

  function closeSds(): void {
    isSdsModalOpen.value = false;
  }

  watch(
    riskContext,
    () => {
      scheduleRiskSave();
    },
    { deep: true },
  );

  watch(
    riskOverrides,
    () => {
      scheduleRiskSave();
    },
    { deep: true },
  );

  watch(
    options.prep,
    (next) => {
      if (!next) {
        resetRiskState();
      }
    },
  );

  return {
    riskDraft,
    riskWarnings,
    riskStateRev,
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
    saveRiskDraft,
    updateRiskMeasures,
    exportRiskPdf,
    saveRiskPdfToVault,
    openSds,
    closeSds,
    isSdsModalOpen,
    isSdsLoading,
    sdsDocument,
    resetRiskState,
  };
}
