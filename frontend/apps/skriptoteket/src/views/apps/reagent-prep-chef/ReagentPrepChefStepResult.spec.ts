import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ReagentPrepChefStepResult from "./ReagentPrepChefStepResult.vue";
import ReagentPrepChefStepRisk from "./ReagentPrepChefStepRisk.vue";
import ReagentPrepChefStepSource from "./ReagentPrepChefStepSource.vue";
import type { ReagentPrepChefPrepSheet } from "./types";

const sheet = {
  chemistry: {
    formula_clean: "NaCl", molar_mass_g_mol: "58.44", moles_required: "0.1",
    mass_g: "5.844", solute_purity: "1", source_type: "solid", target_molarity: "0.1",
  },
  logistics: {
    base_total_volume_ml: "1000", safety_factor_pct: "0", total_groups: 10,
    total_volume_ml: "1000",
  },
  meta: { app_version: "app:0.1.0", generated_at: "2026-10-17T12:00:00Z" },
  safety: { level: "curated", display_name: "Natriumklorid", hazard_codes: [], ppe: [] },
  instructions: [], warnings: [],
} satisfies ReagentPrepChefPrepSheet;

const sites = [
  {
    name: "source calculation", errorProp: "actionErrorMessage",
    mount: () => mount(ReagentPrepChefStepSource, { props: {
      form: {
        chemicalFormula: "NaCl", targetMolarity: "0.1", volPerGroupMl: "100",
        studentCount: 20, studentsPerGroup: 2, safetyFactor: "0", sourceType: "solid",
        stockMolarity: "1", solutePurity: "1",
      },
      isCalculating: false, isExporting: false, canCalculate: true, actionErrorMessage: null,
    } }),
  },
  {
    name: "result export/save", errorProp: "actionErrorMessage",
    mount: () => mount(ReagentPrepChefStepResult, { global: { stubs: { RouterLink: true } }, props: {
      prep: sheet, instructions: [], warnings: ["Kontrollera mängden."], safety: null,
      safetyPpe: [], isExporting: false, isSavingPdfToVault: false, canExport: true,
      lastSavedPdfVaultRef: null, actionErrorMessage: null,
    } }),
  },
  {
    name: "risk draft", errorProp: "riskErrorMessage",
    mount: () => mount(ReagentPrepChefStepRisk, { global: { stubs: { RouterLink: true } }, props: {
      riskDraft: null, riskWarnings: [], isRiskLoading: false, isRiskSaving: false,
      isRiskExporting: false, isSavingRiskPdfToVault: false, lastSavedRiskPdfVaultRef: null,
      riskErrorMessage: null, missingRiskContextMessage: null, canExportRisk: false,
      riskContext: {}, riskOverrides: {}, riskMeasuresDraft: {},
    } }),
  },
];

describe("Reagent Prep Chef failure announcements", () => {
  it.each(sites)("announces $name failures and clears the alert on recovery", async (site) => {
    const wrapper = site.mount();
    try {
      expect(wrapper.find('[role="alert"]').exists()).toBe(false);
      await wrapper.setProps({ [site.errorProp]: "Åtgärden misslyckades." });
      const alert = wrapper.get('[role="alert"]');
      expect(alert.text()).toBe("Åtgärden misslyckades.");
      expect(alert.attributes("aria-live")).toBe("assertive");
      expect(alert.attributes("aria-atomic")).toBe("true");
      await wrapper.setProps({ [site.errorProp]: null });
      expect(wrapper.find('[role="alert"]').exists()).toBe(false);
      expect(wrapper.text()).not.toContain("Åtgärden misslyckades.");
    } finally {
      wrapper.unmount();
    }
  });

  it("keeps risk loading informational rather than assertive", () => {
    const wrapper = mount(ReagentPrepChefStepRisk, { global: { stubs: { RouterLink: true } }, props: {
      riskDraft: null, riskWarnings: [], isRiskLoading: true, isRiskSaving: false,
      isRiskExporting: false, isSavingRiskPdfToVault: false, lastSavedRiskPdfVaultRef: null,
      riskErrorMessage: null, missingRiskContextMessage: null, canExportRisk: false,
      riskContext: {}, riskOverrides: {}, riskMeasuresDraft: {},
    } });
    try {
      expect(wrapper.get('[role="status"]').text()).toContain("Laddar riskutkast");
      expect(wrapper.find('[role="alert"]').exists()).toBe(false);
      expect(wrapper.find('[aria-live="assertive"]').exists()).toBe(false);
    } finally {
      wrapper.unmount();
    }
  });
});
