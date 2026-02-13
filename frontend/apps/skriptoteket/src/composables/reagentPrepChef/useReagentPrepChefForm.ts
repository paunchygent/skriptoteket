import { computed, reactive, ref, watch } from "vue";

import type { Ref } from "vue";

import type {
  ReagentPrepChefChemicalOption,
  ReagentPrepChefFormState,
  ReagentPrepChefPrepRequestInput,
  ReagentPrepChefPrepRequestOutput,
} from "../../views/apps/reagent-prep-chef/types";

const chemicalSearchMinChars = 2;
const draftKey = "skriptoteket.reagent-prep-chef.draft.v1";

const defaultFormState: ReagentPrepChefFormState = {
  chemicalFormula: "",
  targetMolarity: "0.1",
  volPerGroupMl: "50",
  studentCount: 30,
  studentsPerGroup: 2,
  safetyFactor: "0.10",
  sourceType: "solid",
  stockMolarity: "1.0",
  solutePurity: "1.0",
};

export function useReagentPrepChefForm(
  chemicals: Ref<ReagentPrepChefChemicalOption[]>,
) {
  const form = reactive<ReagentPrepChefFormState>({ ...defaultFormState });
  const selectedChemicalKey = ref("");
  const chemicalQuery = ref("");

  const chemicalSearchIsActive = computed(
    () => chemicalQuery.value.trim().length >= chemicalSearchMinChars,
  );

  const chemicalSearchResults = computed(() => {
    const query = chemicalQuery.value.trim().toLowerCase();
    if (query.length < chemicalSearchMinChars) {
      return [];
    }
    return chemicals.value.filter((item) => {
      const haystack =
        `${item.display_name} ${item.key} ${(item.aliases ?? []).join(" ")}`.toLowerCase();
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

    if (form.sourceType === "liquid_stock" && parseDecimal(form.stockMolarity) === null) {
      return false;
    }
    return true;
  });

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

  function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
  }

  function loadDraft(): void {
    try {
      const raw = localStorage.getItem(draftKey);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (!isRecord(parsed)) return;

      const chemicalFormula = parsed.chemicalFormula;
      const targetMolarity = parsed.targetMolarity;
      const volPerGroupMl = parsed.volPerGroupMl;
      const studentCount = parsed.studentCount;
      const studentsPerGroup = parsed.studentsPerGroup;
      const safetyFactor = parsed.safetyFactor;
      const sourceType = parsed.sourceType;
      const stockMolarity = parsed.stockMolarity;
      const solutePurity = parsed.solutePurity;
      const storedSelectedKey = parsed.selectedChemicalKey;

      if (typeof chemicalFormula === "string") form.chemicalFormula = chemicalFormula;
      if (typeof targetMolarity === "string") form.targetMolarity = targetMolarity;
      if (typeof volPerGroupMl === "string") form.volPerGroupMl = volPerGroupMl;
      if (typeof studentCount === "number") form.studentCount = studentCount;
      if (typeof studentsPerGroup === "number") form.studentsPerGroup = studentsPerGroup;
      if (typeof safetyFactor === "string") form.safetyFactor = safetyFactor;
      if (sourceType === "solid" || sourceType === "liquid_stock") {
        form.sourceType = sourceType;
      }
      if (typeof stockMolarity === "string") form.stockMolarity = stockMolarity;
      if (typeof solutePurity === "string") form.solutePurity = solutePurity;
      if (typeof storedSelectedKey === "string") {
        selectedChemicalKey.value = storedSelectedKey;
      }
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

  function clearDraft(): void {
    try {
      localStorage.removeItem(draftKey);
    } catch {
      // ignore
    }
  }

  function resetForm(): void {
    Object.assign(form, defaultFormState);
  }

  function resetSelection(): void {
    selectedChemicalKey.value = "";
    chemicalQuery.value = "";
  }

  function selectChemicalFromSearch(item: ReagentPrepChefChemicalOption): void {
    selectedChemicalKey.value = item.key;
    form.chemicalFormula = item.key;
    chemicalQuery.value = "";
  }

  watch(form, saveDraft, { deep: true });
  watch(selectedChemicalKey, saveDraft);
  watch(selectedChemicalKey, (value) => {
    const match = chemicals.value.find((item) => item.key === value);
    if (!match) return;
    form.chemicalFormula = match.key;
    if (value) {
      chemicalQuery.value = "";
    }
  });

  return {
    form,
    selectedChemicalKey,
    chemicalQuery,
    chemicalSearchIsActive,
    chemicalSearchResults,
    derivedGroups,
    derivedTotalVolumeMl,
    canCalculate,
    parseDecimal,
    applyDefaults,
    buildRequestPayload,
    loadDraft,
    saveDraft,
    clearDraft,
    resetForm,
    resetSelection,
    selectChemicalFromSearch,
  };
}
