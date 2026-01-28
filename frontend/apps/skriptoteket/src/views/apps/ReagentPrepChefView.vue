<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiFetch, apiFetchBlob, apiGet, apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useToast } from "../../composables/useToast";
import { IconSettings, IconX } from "../../components/icons";
import UiSearchBar from "../../components/ui/UiSearchBar.vue";
import VaultPickerModal from "../../components/vault/VaultPickerModal.vue";

type AppDetailResponse = components["schemas"]["AppDetailResponse"];

type SourceType = "solid" | "liquid_stock";
type StepId = "reagent" | "class" | "source" | "result" | "risk";

type ReagentPrepChefPrepRequestInput = components["schemas"]["ReagentPrepChefPrepRequest-Input"];
type ReagentPrepChefPrepRequestOutput = components["schemas"]["ReagentPrepChefPrepRequest-Output"];
type ReagentPrepChefPrepResult = components["schemas"]["ReagentPrepChefPrepResult"];
type ReagentPrepChefChemicalsResult = components["schemas"]["ReagentPrepChefChemicalsResult"];
type ReagentPrepChefChemicalOption = components["schemas"]["ReagentPrepChefChemicalOption"];
type ReagentPrepChefDefaultsResult = components["schemas"]["ReagentPrepChefDefaultsResult"];
type ReagentPrepChefUpdateDefaultsRequest = components["schemas"]["ReagentPrepChefUpdateDefaultsRequest"];
type ReagentPrepChefSavePdfResult = components["schemas"]["ReagentPrepChefSavePdfResult"];
type ReagentPrepChefSaveDefaultsResult = components["schemas"]["ReagentPrepChefSaveDefaultsResult"];
type ReagentPrepChefLoadDefaultsRequest = components["schemas"]["ReagentPrepChefLoadDefaultsRequest"];
type ReagentPrepChefPrepSheet = ReagentPrepChefPrepResult["sheet"];
type ReagentPrepChefRiskAssessmentRequest = components["schemas"]["ReagentPrepChefRiskAssessmentRequest"];
type ReagentPrepChefRiskAssessmentResult = components["schemas"]["ReagentPrepChefRiskAssessmentResult"];
type ReagentPrepChefRiskAssessmentInputs = components["schemas"]["ReagentPrepChefRiskAssessmentInputs"];
type ReagentPrepChefRiskContext = components["schemas"]["ReagentPrepChefRiskContext"];
type ReagentPrepChefRiskItemOverride = components["schemas"]["ReagentPrepChefRiskItemOverride"];

type RiskOverrideDraft = {
  id: string;
  severity: number | null;
  likelihood: number | null;
  measures: string[] | null;
  confirmed: boolean;
};

const route = useRoute();
const toast = useToast();

const appId = computed(() => {
  const param = route.params.appId;
  return typeof param === "string" ? param : "";
});

const apiPrefix = computed(() => `/api/v1/apps/${encodeURIComponent(appId.value)}`);

const app = ref<AppDetailResponse | null>(null);
const chemicals = ref<ReagentPrepChefChemicalOption[]>([]);
const selectedChemicalKey = ref<string>("");
const chemicalQuery = ref<string>("");
const prep = ref<ReagentPrepChefPrepSheet | null>(null);
const lastPrepRequest = ref<ReagentPrepChefPrepRequestInput | null>(null);

const riskDraft = ref<ReagentPrepChefRiskAssessmentResult["draft"] | null>(null);
const riskWarnings = ref<string[]>([]);
const riskStateRev = ref<number>(0);
const isRiskLoading = ref(false);
const isRiskSaving = ref(false);
const isRiskExporting = ref(false);
const isSavingRiskPdfToVault = ref(false);
const lastSavedRiskPdfVaultRef = ref<string | null>(null);
const riskErrorMessage = ref<string | null>(null);
const riskInitialized = ref(false);
const riskSaveTimerId = ref<number | null>(null);

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

const defaults = ref<ReagentPrepChefDefaultsResult | null>(null);
const defaultsStateRev = ref<number>(0);
const isDefaultsLoading = ref(false);
const isDefaultsSaving = ref(false);
const isSavingPdfToVault = ref(false);
const lastSavedPdfVaultRef = ref<string | null>(null);
const isSavingDefaultsToVault = ref(false);
const lastSavedDefaultsVaultRef = ref<string | null>(null);
const isLoadingDefaultsFromVault = ref(false);
const isDefaultsVaultPickerOpen = ref(false);
const defaultsVaultPickerDraft = ref<string[]>([]);

const showSettings = ref(false);
const settingsTriggerRef = ref<HTMLButtonElement | null>(null);
const settingsPopoverRef = ref<HTMLDivElement | null>(null);

const isLoading = ref(true);
const isCalculating = ref(false);
const isExporting = ref(false);
const errorMessage = ref<string | null>(null);
const actionErrorMessage = ref<string | null>(null);

const step = ref<StepId>("reagent");

const form = reactive({
  chemicalFormula: "",
  targetMolarity: "0.1",
  volPerGroupMl: "50",
  studentCount: 30,
  studentsPerGroup: 2,
  safetyFactor: "0.10",
  sourceType: "solid" as SourceType,
  stockMolarity: "1.0",
  solutePurity: "1.0",
});

const instructions = computed(() => prep.value?.instructions ?? []);
const warnings = computed(() => prep.value?.warnings ?? []);
const safety = computed(() => prep.value?.safety ?? null);
const safetyPpe = computed(() => safety.value?.ppe ?? []);

const chemicalSearchMinChars = 2;
const chemicalSearchIsActive = computed(() => chemicalQuery.value.trim().length >= chemicalSearchMinChars);
const chemicalSearchResults = computed(() => {
  const query = chemicalQuery.value.trim().toLowerCase();
  if (query.length < chemicalSearchMinChars) {
    return [];
  }
  return chemicals.value.filter((item) => {
    const haystack = `${item.display_name} ${item.key} ${(item.aliases ?? []).join(" ")}`.toLowerCase();
    return haystack.includes(query);
  });
});

function parseDecimal(value: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (!normalized) return null;
  const numberValue = Number(normalized);
  return Number.isFinite(numberValue) ? numberValue : null;
}

const derivedGroups = computed(() => {
  if (form.studentCount <= 0 || form.studentsPerGroup <= 0) return null;
  return Math.ceil(form.studentCount / form.studentsPerGroup);
});

const derivedTotalVolumeMl = computed(() => {
  const groups = derivedGroups.value;
  const vol = parseDecimal(form.volPerGroupMl);
  const safetyFactor = parseDecimal(form.safetyFactor);
  if (groups === null || vol === null || safetyFactor === null) return null;
  return groups * vol * (1 + safetyFactor);
});

const canCalculate = computed(() => {
  if (!form.chemicalFormula.trim()) return false;
  if (parseDecimal(form.targetMolarity) === null) return false;
  if (parseDecimal(form.volPerGroupMl) === null) return false;
  if (derivedGroups.value === null) return false;

  const safetyFactor = parseDecimal(form.safetyFactor);
  if (safetyFactor === null || safetyFactor < 0 || safetyFactor > 0.5) return false;

  const purity = parseDecimal(form.solutePurity);
  if (purity === null || purity <= 0 || purity > 1) return false;

  if (form.sourceType === "liquid_stock" && parseDecimal(form.stockMolarity) === null) return false;
  return true;
});

const canExport = computed(() => prep.value !== null && canCalculate.value);

const riskContextIsComplete = computed(() => {
  if (!riskDraft.value) return false;
  if (!riskContext.scope?.trim()) return false;
  if (!riskContext.participants?.trim()) return false;
  if (!riskContext.approver?.trim()) return false;
  if (!riskContext.assessment_date) return false;
  if (!riskContext.next_review_date) return false;
  return true;
});

const canExportRisk = computed(() => {
  if (!riskDraft.value) return false;
  if (riskDraft.value.requires_confirmation) return false;
  return riskContextIsComplete.value;
});

const draftKey = "skriptoteket.reagent-prep-chef.draft.v1";

function loadDraft(): void {
  try {
    const raw = localStorage.getItem(draftKey);
    if (!raw) return;
    const parsed = JSON.parse(raw) as Partial<typeof form> & { selectedChemicalKey?: unknown };

    if (typeof parsed.chemicalFormula === "string") form.chemicalFormula = parsed.chemicalFormula;
    if (typeof parsed.targetMolarity === "string") form.targetMolarity = parsed.targetMolarity;
    if (typeof parsed.volPerGroupMl === "string") form.volPerGroupMl = parsed.volPerGroupMl;
    if (typeof parsed.studentCount === "number") form.studentCount = parsed.studentCount;
    if (typeof parsed.studentsPerGroup === "number") form.studentsPerGroup = parsed.studentsPerGroup;
    if (typeof parsed.safetyFactor === "string") form.safetyFactor = parsed.safetyFactor;
    if (parsed.sourceType === "solid" || parsed.sourceType === "liquid_stock") form.sourceType = parsed.sourceType;
    if (typeof parsed.stockMolarity === "string") form.stockMolarity = parsed.stockMolarity;
    if (typeof parsed.solutePurity === "string") form.solutePurity = parsed.solutePurity;
    if (typeof parsed.selectedChemicalKey === "string") selectedChemicalKey.value = parsed.selectedChemicalKey;
  } catch {
    // ignore invalid drafts
  }
}

function saveDraft(): void {
  try {
    localStorage.setItem(
      draftKey,
      JSON.stringify({
        ...form,
        selectedChemicalKey: selectedChemicalKey.value,
      }),
    );
  } catch {
    // ignore storage failures
  }
}

async function fetchApp(): Promise<void> {
  app.value = await apiGet<AppDetailResponse>(`/api/v1/apps/${encodeURIComponent(appId.value)}`);
}

async function fetchChemicals(): Promise<void> {
  const response = await apiGet<ReagentPrepChefChemicalsResult>(`${apiPrefix.value}/chemicals`);
  chemicals.value = response.chemicals ?? [];
}

async function fetchDefaults(): Promise<void> {
  isDefaultsLoading.value = true;
  try {
    const response = await apiGet<ReagentPrepChefDefaultsResult>(`${apiPrefix.value}/defaults`);
    defaults.value = response;
    defaultsStateRev.value = response.state_rev;
  } finally {
    isDefaultsLoading.value = false;
  }
}

function applyDefaults(preset: ReagentPrepChefPrepRequestOutput): void {
  form.chemicalFormula = preset.chemical_formula;
  form.targetMolarity = String(preset.target_molarity);
  form.volPerGroupMl = String(preset.vol_per_group_ml);
  form.studentCount = preset.student_count;
  form.studentsPerGroup = preset.students_per_group;
  form.safetyFactor = String(preset.safety_factor);
  form.sourceType = preset.source_type;
  form.stockMolarity =
    preset.stock_molarity === null || preset.stock_molarity === undefined
      ? "1.0"
      : String(preset.stock_molarity);
  form.solutePurity = String(preset.solute_purity);
  selectedChemicalKey.value = preset.chemical_formula;
}

function loadDefaultsIntoForm(): void {
  const preset = defaults.value?.defaults ?? null;
  if (!preset) {
    toast.info("Inga standardinställningar sparade än.");
    return;
  }
  applyDefaults(preset);
  toast.success("Standardinställningar laddade.");
}

async function saveDefaults(): Promise<void> {
  if (isDefaultsSaving.value) return;

  isDefaultsSaving.value = true;
  actionErrorMessage.value = null;

  const payload: ReagentPrepChefUpdateDefaultsRequest = {
    expected_state_rev: defaultsStateRev.value,
    defaults: buildRequestPayload(),
  };

  try {
    const response = await apiFetch<ReagentPrepChefDefaultsResult>(`${apiPrefix.value}/defaults`, {
      method: "PUT",
      body: payload,
    });
    defaults.value = response;
    defaultsStateRev.value = response.state_rev;
    toast.success("Standardinställningar sparade.");
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionErrorMessage.value = error.message;
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att spara standardinställningarna.";
    }
  } finally {
    isDefaultsSaving.value = false;
  }
}

async function clearDefaults(): Promise<void> {
  if (isDefaultsSaving.value) return;

  isDefaultsSaving.value = true;
  actionErrorMessage.value = null;

  const payload: ReagentPrepChefUpdateDefaultsRequest = {
    expected_state_rev: defaultsStateRev.value,
    defaults: null,
  };

  try {
    const response = await apiFetch<ReagentPrepChefDefaultsResult>(`${apiPrefix.value}/defaults`, {
      method: "PUT",
      body: payload,
    });
    defaults.value = response;
    defaultsStateRev.value = response.state_rev;
    toast.success("Standardinställningar rensade.");
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionErrorMessage.value = error.message;
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att rensa standardinställningarna.";
    }
  } finally {
    isDefaultsSaving.value = false;
  }
}

function defaultVaultDefaultsName(): string {
  return "reagensberedning-standardinstallningar.json";
}

function vaultFileIdFromRef(refValue: string): string | null {
  const prefix = "vault:";
  if (!refValue.startsWith(prefix)) return null;
  const candidate = refValue.slice(prefix.length).trim();
  return candidate.length > 0 ? candidate : null;
}

async function saveDefaultsToVault(): Promise<void> {
  if (!canCalculate.value) return;
  if (isSavingDefaultsToVault.value) return;

  isSavingDefaultsToVault.value = true;
  actionErrorMessage.value = null;

  try {
    const response = await apiPost<ReagentPrepChefSaveDefaultsResult>(`${apiPrefix.value}/save-defaults`, {
      defaults: buildRequestPayload(),
      name: defaultVaultDefaultsName(),
    });
    lastSavedDefaultsVaultRef.value = response.file.ref;
    toast.success("Standardinställningar sparade i Mina filer.");
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionErrorMessage.value = error.message;
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att spara standardinställningarna i Mina filer just nu.";
    }
  } finally {
    isSavingDefaultsToVault.value = false;
  }
}

function openDefaultsVaultPicker(): void {
  defaultsVaultPickerDraft.value = [];
  isDefaultsVaultPickerOpen.value = true;
}

function closeDefaultsVaultPicker(): void {
  isDefaultsVaultPickerOpen.value = false;
}

async function loadDefaultsFromVaultFileRef(refValue: string): Promise<void> {
  const fileId = vaultFileIdFromRef(refValue);
  if (!fileId) {
    actionErrorMessage.value = "Ogiltig filreferens. Välj en fil från Mina filer igen.";
    return;
  }

  if (isLoadingDefaultsFromVault.value) return;

  isLoadingDefaultsFromVault.value = true;
  actionErrorMessage.value = null;

  const payload: ReagentPrepChefLoadDefaultsRequest = {
    expected_state_rev: defaultsStateRev.value,
    file_id: fileId,
  };

  try {
    const response = await apiPost<ReagentPrepChefDefaultsResult>(`${apiPrefix.value}/load-defaults`, payload);
    defaults.value = response;
    defaultsStateRev.value = response.state_rev;

    if (!response.defaults) {
      toast.info("Filen innehöll inga standardinställningar.");
      return;
    }

    applyDefaults(response.defaults);
    toast.success("Standardinställningar laddade från Mina filer.");
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionErrorMessage.value = error.message;
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att ladda standardinställningar från Mina filer.";
    }
  } finally {
    isLoadingDefaultsFromVault.value = false;
  }
}

function onDefaultsVaultPickerConfirm(refs: string[]): void {
  closeDefaultsVaultPicker();
  const refValue = refs.at(0);
  if (!refValue) return;
  void loadDefaultsFromVaultFileRef(refValue);
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
  prep.value = null;
  lastPrepRequest.value = null;
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
  showSettings.value = false;
  void load();
});

watch(form, saveDraft, { deep: true });
watch(selectedChemicalKey, saveDraft);
watch(step, (next) => {
  saveDraft();
  if (next === "risk" && prep.value) {
    void loadRiskDraft();
  }
});

watch(prep, (next) => {
  if (!next) {
    resetRiskState();
  }
});

watch(riskContext, () => {
  scheduleRiskSave();
}, { deep: true });

watch(riskOverrides, () => {
  scheduleRiskSave();
}, { deep: true });

watch(selectedChemicalKey, (value) => {
  const match = chemicals.value.find((item) => item.key === value);
  if (!match) return;
  form.chemicalFormula = match.key;
  if (value) {
    chemicalQuery.value = "";
  }
});

function selectChemicalFromSearch(item: ReagentPrepChefChemicalOption): void {
  selectedChemicalKey.value = item.key;
  form.chemicalFormula = item.key;
  chemicalQuery.value = "";
}

function closeSettings(): void {
  showSettings.value = false;
}

function toggleSettings(): void {
  showSettings.value = !showSettings.value;
}

function handleSettingsClickOutside(event: MouseEvent): void {
  if (!showSettings.value) return;
  const target = event.target as Node;
  if (
    settingsTriggerRef.value?.contains(target) ||
    settingsPopoverRef.value?.contains(target)
  ) {
    return;
  }
  closeSettings();
}

function handleSettingsEscape(event: KeyboardEvent): void {
  if (event.key === "Escape" && showSettings.value) {
    closeSettings();
  }
}

onMounted(() => {
  loadDraft();
  void load();
  document.addEventListener("click", handleSettingsClickOutside);
  document.addEventListener("keydown", handleSettingsEscape);
});

onUnmounted(() => {
  document.removeEventListener("click", handleSettingsClickOutside);
  document.removeEventListener("keydown", handleSettingsEscape);
});

function buildRequestPayload(): ReagentPrepChefPrepRequestInput {
  const payload: ReagentPrepChefPrepRequestInput = {
    chemical_formula: form.chemicalFormula,
    target_molarity: form.targetMolarity,
    vol_per_group_ml: form.volPerGroupMl,
    student_count: form.studentCount,
    students_per_group: form.studentsPerGroup,
    safety_factor: form.safetyFactor,
    source_type: form.sourceType,
    stock_molarity: null,
    solute_purity: form.solutePurity,
  };

  if (form.sourceType === "liquid_stock") {
    payload.stock_molarity = form.stockMolarity;
  }

  return payload;
}

function currentPrepPayload(): ReagentPrepChefPrepRequestInput {
  return lastPrepRequest.value ?? buildRequestPayload();
}

function resetRiskState(): void {
  riskDraft.value = null;
  riskWarnings.value = [];
  riskStateRev.value = 0;
  riskErrorMessage.value = null;
  riskInitialized.value = false;
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
  const overrides = (riskDraft.value?.risks ?? []).map<ReagentPrepChefRiskItemOverride>((risk) => {
    const override = riskOverrides[risk.id];
    return {
      id: risk.id,
      severity: override?.severity ?? null,
      likelihood: override?.likelihood ?? null,
      measures: override?.measures ?? null,
      confirmed: override?.confirmed ?? false,
    };
  });

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
      severity: item.final.severity,
      likelihood: item.final.likelihood,
      measures: [...measures],
      confirmed: item.confirmed,
    };
    riskMeasuresDraft[item.id] = measures.join("\n");
  }

  await nextTick();
  riskInitialized.value = true;
}

async function loadRiskDraft(): Promise<void> {
  if (!prep.value) {
    riskErrorMessage.value = "Beräkna först ett resultat.";
    return;
  }
  if (isRiskLoading.value) return;

  isRiskLoading.value = true;
  riskErrorMessage.value = null;

  try {
    const response = await apiPost<ReagentPrepChefRiskAssessmentResult>(`${apiPrefix.value}/risk-assessment`, {
      prep: currentPrepPayload(),
    });
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
  if (!prep.value || !riskDraft.value) return;
  if (isRiskSaving.value) return;

  isRiskSaving.value = true;
  riskErrorMessage.value = null;

  const payload: ReagentPrepChefRiskAssessmentRequest = {
    prep: currentPrepPayload(),
    expected_state_rev: riskStateRev.value,
    inputs: buildRiskInputs(),
    reset: false,
  };

  try {
    const response = await apiPost<ReagentPrepChefRiskAssessmentResult>(`${apiPrefix.value}/risk-assessment`, payload);
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
      severity: null,
      likelihood: null,
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
    const blob = await apiFetchBlob(`${apiPrefix.value}/export-risk-pdf`, {
      method: "POST",
      body: {
        prep: currentPrepPayload(),
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
    const response = await apiPost<ReagentPrepChefSavePdfResult>(`${apiPrefix.value}/save-risk-pdf`, {
      prep: currentPrepPayload(),
      expected_state_rev: riskStateRev.value,
      inputs: buildRiskInputs(),
    });
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

function openSds(): void {
  if (!riskDraft.value?.sds_ref) return;
  const url = `${apiPrefix.value}/sds/${encodeURIComponent(riskDraft.value.sds_ref)}`;
  window.open(url, "_blank", "noopener");
}

function goTo(nextStep: StepId): void {
  step.value = nextStep;
}

async function calculate(): Promise<void> {
  if (!canCalculate.value) return;
  if (isCalculating.value) return;

  isCalculating.value = true;
  actionErrorMessage.value = null;
  errorMessage.value = null;

  try {
    const payload = buildRequestPayload();
    const response = await apiPost<ReagentPrepChefPrepResult>(`${apiPrefix.value}/prep`, payload);
    prep.value = response.sheet;
    lastPrepRequest.value = payload;
    resetRiskState();
    step.value = "result";
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionErrorMessage.value = error.message;
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att beräkna just nu.";
    }
  } finally {
    isCalculating.value = false;
  }
}

async function exportPdf(): Promise<void> {
  if (!canExport.value) return;
  if (isExporting.value) return;

  isExporting.value = true;
  actionErrorMessage.value = null;

  try {
    const blob = await apiFetchBlob(`${apiPrefix.value}/export-pdf`, {
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
      actionErrorMessage.value = error.message;
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att exportera PDF just nu.";
    }
  } finally {
    isExporting.value = false;
  }
}

function defaultVaultPdfName(): string {
  const formula = prep.value?.chemistry.formula_clean?.trim() ?? form.chemicalFormula.trim();
  if (!formula) return "reagensberedning.pdf";
  return `reagensberedning-${formula}.pdf`;
}

async function savePdfToVault(): Promise<void> {
  if (!canExport.value) return;
  if (isSavingPdfToVault.value) return;

  isSavingPdfToVault.value = true;
  actionErrorMessage.value = null;

  try {
    const response = await apiPost<ReagentPrepChefSavePdfResult>(`${apiPrefix.value}/save-pdf`, {
      prep: currentPrepPayload(),
      name: defaultVaultPdfName(),
    });
    lastSavedPdfVaultRef.value = response.file.ref;
    toast.success("PDF sparad i Mina filer.");
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionErrorMessage.value = error.message;
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att spara PDF i Mina filer just nu.";
    }
  } finally {
    isSavingPdfToVault.value = false;
  }
}

function resetAll(): void {
  prep.value = null;
  lastPrepRequest.value = null;
  resetRiskState();
  selectedChemicalKey.value = "";
  chemicalQuery.value = "";
  step.value = "reagent";
  actionErrorMessage.value = null;
  lastSavedPdfVaultRef.value = null;
  lastSavedRiskPdfVaultRef.value = null;
  lastSavedDefaultsVaultRef.value = null;

  form.chemicalFormula = "";
  form.targetMolarity = "0.1";
  form.volPerGroupMl = "50";
  form.studentCount = 30;
  form.studentsPerGroup = 2;
  form.safetyFactor = "0.10";
  form.sourceType = "solid";
  form.stockMolarity = "1.0";
  form.solutePurity = "1.0";

  try {
    localStorage.removeItem(draftKey);
  } catch {
    // ignore
  }
}
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

      <div class="relative ml-auto">
        <button
          ref="settingsTriggerRef"
          type="button"
          class="btn-ghost h-[32px] px-3 py-1.5 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-navy/30 bg-white shadow-none flex items-center gap-2"
          aria-label="Inställningar"
          title="Inställningar"
          :aria-expanded="showSettings"
          aria-controls="rpc-settings-popover"
          @click.stop="toggleSettings"
        >
          <IconSettings :size="16" />
          <span>Inställningar</span>
        </button>

        <Transition name="popover">
          <div
            v-if="showSettings"
            id="rpc-settings-popover"
            ref="settingsPopoverRef"
            class="absolute right-0 mt-2 z-50 w-[min(22rem,calc(100vw-2rem))] border border-navy bg-white shadow-brutal-sm p-4 pr-10 text-sm text-navy/80"
            role="dialog"
            aria-modal="false"
            aria-label="Inställningar"
          >
            <button
              type="button"
              class="absolute top-2 right-2 h-7 w-7 grid place-items-center border border-transparent rounded-[var(--huleedu-radius-sm)] text-navy/60 hover:text-burgundy hover:border-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
              aria-label="Stäng inställningar"
              @click="closeSettings"
            >
              <IconX :size="14" />
            </button>

            <p class="font-semibold text-navy mb-2">Inställningar</p>

            <div class="space-y-2">
              <p class="text-xs text-navy/60">
                Standardinställningar sparas per användare. Du kan alltid ändra dem senare.
              </p>
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="btn-primary"
                  :disabled="isDefaultsSaving || !canCalculate"
                  @click="void saveDefaults()"
                >
                  {{ isDefaultsSaving ? "Sparar…" : "Spara som standard" }}
                </button>
                <button
                  type="button"
                  class="btn-ghost"
                  :disabled="isDefaultsLoading || !defaults?.defaults"
                  @click="loadDefaultsIntoForm"
                >
                  Ladda standard
                </button>
                <button
                  type="button"
                  class="btn-ghost"
                  :disabled="isDefaultsSaving || !defaults?.defaults"
                  @click="void clearDefaults()"
                >
                  Rensa
                </button>
              </div>
            </div>

            <div class="border-t border-navy/20 pt-3 mt-3 space-y-2">
              <p class="text-xs text-navy/60">
                Du kan också spara och ladda standardinställningar som en fil i Mina filer.
              </p>
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="btn-ghost"
                  :disabled="isSavingDefaultsToVault || !canCalculate"
                  @click="void saveDefaultsToVault()"
                >
                  {{ isSavingDefaultsToVault ? "Sparar…" : "Spara i Mina filer" }}
                </button>
                <button
                  type="button"
                  class="btn-ghost"
                  :disabled="isLoadingDefaultsFromVault"
                  @click="openDefaultsVaultPicker"
                >
                  {{ isLoadingDefaultsFromVault ? "Laddar…" : "Ladda från Mina filer" }}
                </button>
              </div>
              <p
                v-if="lastSavedDefaultsVaultRef"
                class="text-[11px] text-navy/60"
              >
                Senast sparad: <span class="font-mono">{{ lastSavedDefaultsVaultRef }}</span>
              </p>
            </div>
          </div>
        </Transition>
      </div>
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

      <section
        v-if="step === 'reagent'"
        class="border border-navy bg-white shadow-brutal-sm"
      >
        <div class="p-4 space-y-4">
          <div class="space-y-1">
            <h2 class="text-lg font-semibold text-navy">Ämne</h2>
            <p class="text-sm text-navy/60">
              Exempel: <span class="font-mono">CuSO4·5H2O</span>, <span class="font-mono">NaCl</span>, <span class="font-mono">KMnO4</span>
            </p>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-2">
              <label class="text-sm font-semibold text-navy">Ämneslista (valfritt)</label>

              <div class="relative">
                <UiSearchBar
                  v-model="chemicalQuery"
                  placeholder="Sök (minst 2 tecken)…"
                  :show-button="false"
                  variant="panel"
                />

                <Transition name="popover">
                  <div
                    v-if="chemicalSearchIsActive"
                    class="absolute left-0 right-0 mt-2 z-50 max-h-56 overflow-auto border border-navy bg-white shadow-brutal-sm"
                  >
                    <div
                      v-if="chemicalSearchResults.length === 0"
                      class="p-3 text-xs text-navy/60"
                    >
                      Inga träffar.
                    </div>
                    <ul
                      v-else
                      class="divide-y divide-navy/10"
                      role="listbox"
                    >
                      <li
                        v-for="item in chemicalSearchResults"
                        :key="item.key"
                      >
                        <button
                          type="button"
                          class="w-full text-left px-3 py-2 hover:bg-canvas transition-colors"
                          @click="selectChemicalFromSearch(item)"
                        >
                          <div class="flex items-baseline justify-between gap-2">
                            <span class="text-sm font-semibold text-navy">{{ item.display_name }}</span>
                            <span class="font-mono text-xs text-navy/60">{{ item.key }}</span>
                          </div>
                        </button>
                      </li>
                    </ul>
                  </div>
                </Transition>
              </div>

              <select
                v-model="selectedChemicalKey"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
                <option value="">— Välj i listan —</option>
                <option
                  v-for="item in chemicals"
                  :key="item.key"
                  :value="item.key"
                >
                  {{ item.display_name }} ({{ item.key }})
                </option>
              </select>
              <p class="text-xs text-navy/60">Listan fylls på över tid. Saknas ditt ämne? Skriv formeln manuellt.</p>
            </div>

            <div class="space-y-2">
              <label
                for="rpc-formula"
                class="text-sm font-semibold text-navy"
              >Kemisk formel</label>
              <input
                id="rpc-formula"
                v-model="form.chemicalFormula"
                type="text"
                placeholder="CuSO4·5H2O"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
              <p class="text-xs text-navy/60">Tips: skriv hydrat som <span class="font-mono">CuSO4·5H2O</span>.</p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2 pt-2">
            <button
              type="button"
              class="btn-primary"
              :disabled="!form.chemicalFormula.trim()"
              @click="goTo('class')"
            >
              Fortsätt →
            </button>
          </div>
        </div>
      </section>

      <section
        v-else-if="step === 'class'"
        class="border border-navy bg-white shadow-brutal-sm"
      >
        <div class="p-4 space-y-4">
          <div class="space-y-1">
            <h2 class="text-lg font-semibold text-navy">Klass</h2>
            <p class="text-sm text-navy/60">Använd kommatal (t.ex. <span class="font-mono">0,10</span>) om du vill.</p>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-2">
              <label
                for="rpc-students"
                class="text-sm font-semibold text-navy"
              >Antal elever</label>
              <input
                id="rpc-students"
                v-model.number="form.studentCount"
                type="number"
                min="1"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
            </div>

            <div class="space-y-2">
              <label
                for="rpc-per-group"
                class="text-sm font-semibold text-navy"
              >Elever per grupp</label>
              <input
                id="rpc-per-group"
                v-model.number="form.studentsPerGroup"
                type="number"
                min="1"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
            </div>

            <div class="space-y-2">
              <label
                for="rpc-vol-group"
                class="text-sm font-semibold text-navy"
              >Volym per grupp (ml)</label>
              <input
                id="rpc-vol-group"
                v-model="form.volPerGroupMl"
                inputmode="decimal"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
            </div>

            <div class="space-y-2">
              <label
                for="rpc-safety-factor"
                class="text-sm font-semibold text-navy"
              >Marginal (0–0,5)</label>
              <input
                id="rpc-safety-factor"
                v-model="form.safetyFactor"
                inputmode="decimal"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
              <p class="text-xs text-navy/60">Ex: 0,10 = 10% extra.</p>
            </div>
          </div>

          <div class="p-3 border border-navy bg-canvas shadow-none text-sm text-navy/80 space-y-1">
            <p class="font-semibold text-navy">Snabb översikt</p>
            <p v-if="derivedGroups !== null">Grupper: <span class="font-mono">{{ derivedGroups }}</span></p>
            <p v-if="derivedTotalVolumeMl !== null">
              Totalvolym (ca): <span class="font-mono">{{ derivedTotalVolumeMl.toFixed(1) }}</span> ml
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2 pt-2">
            <button
              type="button"
              class="btn-ghost"
              @click="goTo('reagent')"
            >
              ← Tillbaka
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="derivedGroups === null || derivedTotalVolumeMl === null"
              @click="goTo('source')"
            >
              Fortsätt →
            </button>
          </div>
        </div>
      </section>

      <section
        v-else-if="step === 'source'"
        class="border border-navy bg-white shadow-brutal-sm"
      >
        <div class="p-4 space-y-4">
          <div class="space-y-1">
            <h2 class="text-lg font-semibold text-navy">Källa</h2>
            <p class="text-sm text-navy/60">Välj om du väger fast ämne eller späder från en stocklösning.</p>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-2">
              <label
                for="rpc-target"
                class="text-sm font-semibold text-navy"
              >Målmolaritet (M)</label>
              <input
                id="rpc-target"
                v-model="form.targetMolarity"
                inputmode="decimal"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
            </div>

            <div class="space-y-2">
              <label
                for="rpc-source"
                class="text-sm font-semibold text-navy"
              >Källa</label>
              <select
                id="rpc-source"
                v-model="form.sourceType"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
                <option value="solid">Fast ämne</option>
                <option value="liquid_stock">Späd från stocklösning</option>
              </select>
            </div>

            <div
              v-if="form.sourceType === 'liquid_stock'"
              class="space-y-2"
            >
              <label
                for="rpc-stock"
                class="text-sm font-semibold text-navy"
              >Stockmolaritet (M)</label>
              <input
                id="rpc-stock"
                v-model="form.stockMolarity"
                inputmode="decimal"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
            </div>

            <div class="space-y-2">
              <label
                for="rpc-purity"
                class="text-sm font-semibold text-navy"
              >Renhet (0–1)</label>
              <input
                id="rpc-purity"
                v-model="form.solutePurity"
                inputmode="decimal"
                class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
              >
              <p class="text-xs text-navy/60">Ex: 0,95 om du har teknisk kvalitet.</p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2 pt-2">
            <button
              type="button"
              class="btn-ghost"
              @click="goTo('class')"
            >
              ← Tillbaka
            </button>

            <button
              type="button"
              class="btn-cta min-w-[140px]"
              :disabled="isCalculating || !canCalculate"
              @click="calculate"
            >
              {{ isCalculating ? "Beräknar…" : "Beräkna" }}
            </button>

            <button
              type="button"
              class="btn-ghost"
              :disabled="isCalculating || isExporting"
              @click="resetAll"
            >
              Nollställ
            </button>
          </div>

          <p
            v-if="actionErrorMessage"
            class="text-sm text-burgundy whitespace-pre-wrap"
          >
            {{ actionErrorMessage }}
          </p>
        </div>
      </section>

      <section
        v-else-if="step === 'result' && prep"
        class="border border-navy bg-white shadow-brutal-sm"
      >
        <div class="p-4 space-y-4">
          <h2 class="text-lg font-semibold text-navy">Resultat</h2>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1 text-sm">
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Formel</span>
                <span class="font-mono text-navy">{{ prep.chemistry.formula_clean }}</span>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Molmassa</span>
                <span class="text-navy">{{ prep.chemistry.molar_mass_g_mol }} g/mol</span>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Totalvolym</span>
                <span class="text-navy">{{ prep.logistics.total_volume_ml }} ml</span>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Grupper</span>
                <span class="text-navy">{{ prep.logistics.total_groups }}</span>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Mängd substans</span>
                <span class="text-navy">{{ prep.chemistry.moles_required }} mol</span>
              </div>
              <div
                v-if="prep.chemistry.mass_g"
                class="flex items-baseline justify-between gap-3"
              >
                <span class="text-navy/60">Massa</span>
                <span class="text-navy">{{ prep.chemistry.mass_g }} g</span>
              </div>
              <template v-if="prep.chemistry.stock_volume_ml">
                <div class="flex items-baseline justify-between gap-3">
                  <span class="text-navy/60">Stockvolym</span>
                  <span class="text-navy">{{ prep.chemistry.stock_volume_ml }} ml</span>
                </div>
                <div class="flex items-baseline justify-between gap-3">
                  <span class="text-navy/60">Spädningsvatten</span>
                  <span class="text-navy">{{ prep.chemistry.diluent_volume_ml }} ml</span>
                </div>
              </template>
            </div>

            <div class="space-y-3 text-sm">
              <div
                v-if="instructions.length > 0"
                class="space-y-2"
              >
                <p class="font-semibold text-navy">Steg</p>
                <ol class="list-decimal pl-5 space-y-1">
                  <li
                    v-for="(item, index) in instructions"
                    :key="index"
                    class="text-navy"
                  >
                    {{ item }}
                  </li>
                </ol>
              </div>

              <div
                v-if="warnings.length > 0"
                class="p-3 border border-burgundy bg-canvas shadow-none space-y-1"
              >
                <p class="font-semibold text-burgundy">Varningar</p>
                <ul class="list-disc pl-5 space-y-1 text-burgundy">
                  <li
                    v-for="(warning, index) in warnings"
                    :key="index"
                  >
                    {{ warning }}
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div
            v-if="safety"
            class="p-3 border border-navy bg-canvas shadow-none space-y-2 text-sm"
          >
            <p class="font-semibold text-navy">Säkerhet</p>
            <p
              v-if="safety.level === 'unknown'"
              class="text-burgundy"
            >
              {{ safety.message ?? "Okänt ämne: konsultera SDS innan användning." }}
            </p>
            <div
              v-else
              class="space-y-1"
            >
              <p
                v-if="safety.display_name"
                class="text-navy"
              >
                {{ safety.display_name }}
              </p>
              <p
                v-if="safetyPpe.length > 0"
                class="text-navy/80"
              >
                PPE: {{ safetyPpe.join(", ") }}
              </p>
              <p
                v-if="safety.disposal"
                class="text-navy/80"
              >
                Avfall: {{ safety.disposal }}
              </p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2 pt-2">
            <button
              type="button"
              class="btn-ghost"
              @click="goTo('source')"
            >
              ← Ändra indata
            </button>

            <button
              type="button"
              class="btn-primary"
              :disabled="isExporting || !canExport"
              @click="exportPdf"
            >
              {{ isExporting ? "Exporterar…" : "Exportera PDF" }}
            </button>

            <button
              type="button"
              class="btn-ghost"
              :disabled="isSavingPdfToVault || !canExport"
              @click="void savePdfToVault()"
            >
              {{ isSavingPdfToVault ? "Sparar…" : "Spara i Mina filer" }}
            </button>

            <button
              type="button"
              class="btn-ghost"
              :disabled="isExporting || isSavingPdfToVault"
              @click="resetAll"
            >
              Nollställ
            </button>
          </div>

          <p
            v-if="lastSavedPdfVaultRef"
            class="text-xs text-navy/60"
          >
            Sparad i Mina filer.
            <RouterLink
              to="/vault"
              class="underline hover:text-burgundy"
            >
              Öppna Mina filer
            </RouterLink>
          </p>

          <p
            v-if="actionErrorMessage"
            class="text-sm text-burgundy whitespace-pre-wrap"
          >
            {{ actionErrorMessage }}
          </p>
        </div>
      </section>

      <section
        v-else-if="step === 'risk'"
        class="border border-navy bg-white shadow-brutal-sm"
      >
        <div class="p-4 space-y-4">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="space-y-1">
              <h2 class="text-lg font-semibold text-navy">Riskbedömning</h2>
              <p class="text-sm text-navy/60">
                Utkastet bygger på beräkningen och kuraterad SDS-data. Bekräfta varje risk innan export.
              </p>
            </div>
            <button
              type="button"
              class="btn-ghost"
              :disabled="isRiskLoading"
              @click="void loadRiskDraft()"
            >
              {{ isRiskLoading ? "Uppdaterar…" : "Uppdatera" }}
            </button>
          </div>

          <p
            v-if="isRiskSaving"
            class="text-xs text-navy/60"
          >
            Sparar utkast…
          </p>

          <div
            v-if="isRiskLoading"
            class="p-3 border border-navy bg-canvas shadow-none text-sm text-navy/70"
          >
            Laddar riskutkast…
          </div>

          <div
            v-else-if="riskErrorMessage"
            class="p-3 border border-error bg-white shadow-brutal-sm text-error text-sm"
          >
            {{ riskErrorMessage }}
          </div>

          <template v-else-if="riskDraft">
            <div
              v-if="riskWarnings.length > 0"
              class="p-3 border border-burgundy bg-canvas shadow-none space-y-1"
            >
              <p class="font-semibold text-burgundy">Varningar</p>
              <ul class="list-disc pl-5 space-y-1 text-burgundy text-sm">
                <li
                  v-for="warning in riskWarnings"
                  :key="warning"
                >
                  {{ warning }}
                </li>
              </ul>
            </div>

            <div class="flex flex-wrap items-center gap-2 text-xs text-navy/70">
              <button
                v-if="riskDraft.sds_ref"
                type="button"
                class="btn-ghost"
                @click="openSds"
              >
                Öppna SDS
              </button>
              <span v-else>Ingen SDS kopplad.</span>
            </div>

            <div class="grid gap-4 lg:grid-cols-2">
              <div class="space-y-3">
                <h3 class="text-sm font-semibold text-navy">Lokal kontext</h3>
                <div class="grid gap-3">
                  <div class="space-y-1">
                    <label class="text-xs font-semibold text-navy">Omfattning</label>
                    <textarea
                      v-model="riskContext.scope"
                      rows="3"
                      class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                    />
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs font-semibold text-navy">Plats</label>
                    <input
                      v-model="riskContext.location"
                      type="text"
                      class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                    >
                  </div>
                  <div class="grid gap-3 sm:grid-cols-2">
                    <div class="space-y-1">
                      <label class="text-xs font-semibold text-navy">Deltagare</label>
                      <input
                        v-model="riskContext.participants"
                        type="text"
                        class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                      >
                    </div>
                    <div class="space-y-1">
                      <label class="text-xs font-semibold text-navy">Ansvarig/Approver</label>
                      <input
                        v-model="riskContext.approver"
                        type="text"
                        class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                      >
                    </div>
                  </div>
                  <div class="grid gap-3 sm:grid-cols-2">
                    <div class="space-y-1">
                      <label class="text-xs font-semibold text-navy">Datum</label>
                      <input
                        v-model="riskContext.assessment_date"
                        type="date"
                        class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                      >
                    </div>
                    <div class="space-y-1">
                      <label class="text-xs font-semibold text-navy">Nästa översyn</label>
                      <input
                        v-model="riskContext.next_review_date"
                        type="date"
                        class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                      >
                    </div>
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs font-semibold text-navy">Lokala rutiner</label>
                    <textarea
                      v-model="riskContext.local_routines"
                      rows="2"
                      class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                    />
                  </div>
                </div>
              </div>

              <div class="space-y-3">
                <h3 class="text-sm font-semibold text-navy">CLP & heuristik</h3>
                <div class="p-3 border border-navy bg-canvas shadow-none space-y-1 text-xs text-navy/80">
                  <p>H-koder: {{ riskDraft.clp.hazard_codes?.join(", ") || "—" }}</p>
                  <p>Piktogram: {{ riskDraft.clp.pictograms?.join(", ") || "—" }}</p>
                  <p>Signalord: {{ riskDraft.clp.signal_word || "—" }}</p>
                  <p v-if="riskDraft.clp.notes?.length">Noteringar: {{ riskDraft.clp.notes.join(", ") }}</p>
                </div>
                <div class="p-3 border border-navy bg-canvas shadow-none space-y-1 text-xs text-navy/80">
                  <p>Inkompatibiliteter: {{ riskDraft.heuristics.incompatibilities?.join(", ") || "—" }}</p>
                  <p>Exotermitet: {{ riskDraft.heuristics.exothermicity || "—" }}</p>
                  <p v-if="riskDraft.heuristics.reaction_notes?.length">
                    Noteringar: {{ riskDraft.heuristics.reaction_notes.join(", ") }}
                  </p>
                </div>
              </div>
            </div>

            <div class="space-y-3">
              <div class="flex items-center justify-between gap-2">
                <h3 class="text-sm font-semibold text-navy">Risker</h3>
                <span
                  v-if="riskDraft.requires_confirmation"
                  class="text-xs text-burgundy"
                >
                  Bekräfta alla risker innan export.
                </span>
              </div>

              <div
                v-for="risk in riskDraft.risks"
                :key="risk.id"
                class="border border-navy/20 bg-white p-3 shadow-none space-y-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="space-y-1">
                    <p class="font-semibold text-navy">{{ risk.title }}</p>
                    <p
                      v-if="risk.description"
                      class="text-xs text-navy/60"
                    >
                      {{ risk.description }}
                    </p>
                  </div>
                  <span class="text-xs text-navy/60 uppercase">{{ risk.final.level }}</span>
                </div>

                <p
                  v-if="risk.hazard_codes?.length"
                  class="text-xs text-navy/60"
                >
                  H-koder: {{ risk.hazard_codes.join(", ") }}
                </p>

                <div class="grid gap-3 sm:grid-cols-3 text-sm">
                  <div class="space-y-1">
                    <label class="text-xs font-semibold text-navy">Allvar (1–5)</label>
                    <select
                      v-model.number="riskOverrides[risk.id].severity"
                      class="w-full border border-navy bg-white px-2 py-1 text-navy"
                    >
                      <option
                        v-for="value in [1, 2, 3, 4, 5]"
                        :key="value"
                        :value="value"
                      >
                        {{ value }}
                      </option>
                    </select>
                  </div>
                  <div class="space-y-1">
                    <label class="text-xs font-semibold text-navy">Sannolikhet (1–5)</label>
                    <select
                      v-model.number="riskOverrides[risk.id].likelihood"
                      class="w-full border border-navy bg-white px-2 py-1 text-navy"
                    >
                      <option
                        v-for="value in [1, 2, 3, 4, 5]"
                        :key="value"
                        :value="value"
                      >
                        {{ value }}
                      </option>
                    </select>
                  </div>
                  <div class="space-y-1 text-xs text-navy/70">
                    <p>Poäng: <span class="font-mono">{{ risk.final.score }}</span></p>
                    <p>Nivå: <span class="font-mono">{{ risk.final.level }}</span></p>
                    <label class="flex items-center gap-2 pt-1">
                      <input
                        v-model="riskOverrides[risk.id].confirmed"
                        type="checkbox"
                        class="h-4 w-4 border border-navy"
                      >
                      Bekräfta
                    </label>
                  </div>
                </div>

                <div class="space-y-1">
                  <label class="text-xs font-semibold text-navy">Åtgärder (en per rad)</label>
                  <textarea
                    v-model="riskMeasuresDraft[risk.id]"
                    rows="3"
                    class="w-full border border-navy bg-white px-2 py-2 text-navy"
                    @input="updateRiskMeasures(risk.id)"
                  />
                </div>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2 pt-2">
              <button
                type="button"
                class="btn-ghost"
                @click="goTo('result')"
              >
                ← Tillbaka
              </button>
              <button
                type="button"
                class="btn-primary"
                :disabled="isRiskExporting || !canExportRisk"
                @click="exportRiskPdf"
              >
                {{ isRiskExporting ? "Exporterar…" : "Exportera risk-PDF" }}
              </button>
              <button
                type="button"
                class="btn-ghost"
                :disabled="isSavingRiskPdfToVault || !canExportRisk"
                @click="void saveRiskPdfToVault()"
              >
                {{ isSavingRiskPdfToVault ? "Sparar…" : "Spara i Mina filer" }}
              </button>
            </div>

            <p
              v-if="!riskContextIsComplete"
              class="text-xs text-burgundy"
            >
              Fyll i omfattning, deltagare, ansvarig, datum och nästa översyn innan export.
            </p>

            <p
              v-if="lastSavedRiskPdfVaultRef"
              class="text-xs text-navy/60"
            >
              Sparad i Mina filer.
              <RouterLink
                to="/vault"
                class="underline hover:text-burgundy"
              >
                Öppna Mina filer
              </RouterLink>
            </p>
          </template>
        </div>
      </section>
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
  </div>
</template>

<style scoped>
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
