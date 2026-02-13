import type { components } from "../../../api/openapi";

export type AppDetailResponse = components["schemas"]["AppDetailResponse"];
export type SourceType = "solid" | "liquid_stock";
export type StepId = "reagent" | "class" | "source" | "result" | "risk";

export type ReagentPrepChefPrepRequestInput =
  components["schemas"]["ReagentPrepChefPrepRequest-Input"];
export type ReagentPrepChefPrepRequestOutput =
  components["schemas"]["ReagentPrepChefPrepRequest-Output"];
export type ReagentPrepChefPrepResult = components["schemas"]["ReagentPrepChefPrepResult"];
export type ReagentPrepChefChemicalsResult =
  components["schemas"]["ReagentPrepChefChemicalsResult"];
export type ReagentPrepChefChemicalOption =
  components["schemas"]["ReagentPrepChefChemicalOption"];
export type ReagentPrepChefDefaultsResult =
  components["schemas"]["ReagentPrepChefDefaultsResult"];
export type ReagentPrepChefUpdateDefaultsRequest =
  components["schemas"]["ReagentPrepChefUpdateDefaultsRequest"];
export type ReagentPrepChefSavePdfResult =
  components["schemas"]["ReagentPrepChefSavePdfResult"];
export type ReagentPrepChefSaveDefaultsResult =
  components["schemas"]["ReagentPrepChefSaveDefaultsResult"];
export type ReagentPrepChefLoadDefaultsRequest =
  components["schemas"]["ReagentPrepChefLoadDefaultsRequest"];
export type ReagentPrepChefPrepSheet = ReagentPrepChefPrepResult["sheet"];
export type ReagentPrepChefRiskAssessmentRequest =
  components["schemas"]["ReagentPrepChefRiskAssessmentRequest"];
export type ReagentPrepChefRiskAssessmentResult =
  components["schemas"]["ReagentPrepChefRiskAssessmentResult"];
export type ReagentPrepChefRiskAssessmentInputs =
  components["schemas"]["ReagentPrepChefRiskAssessmentInputs"];
export type ReagentPrepChefRiskContext =
  components["schemas"]["ReagentPrepChefRiskContext"];
export type ReagentPrepChefRiskItemOverride =
  components["schemas"]["ReagentPrepChefRiskItemOverride"];

export type ReagentPrepChefFormState = {
  chemicalFormula: string;
  targetMolarity: string;
  volPerGroupMl: string;
  studentCount: number;
  studentsPerGroup: number;
  safetyFactor: string;
  sourceType: SourceType;
  stockMolarity: string;
  solutePurity: string;
};

export type RiskOverrideDraft = {
  id: string;
  severity: number | null;
  likelihood: number | null;
  measures: string[] | null;
  confirmed: boolean;
};
