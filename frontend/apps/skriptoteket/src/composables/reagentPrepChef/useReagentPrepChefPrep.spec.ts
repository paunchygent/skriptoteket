import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { ApiError } from "../../api/client";
import { useReagentPrepChefPrep } from "./useReagentPrepChefPrep";

const api = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("../../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../../api/client")>(),
  apiPost: api.post,
}));
vi.mock("../useToast", () => ({ useToast: () => ({ success: vi.fn() }) }));

function createPrep() {
  const actionErrorMessage = ref<string | null>(null);
  const payload = {
    chemical_formula: "NaCl", target_molarity: "0.1", vol_per_group_ml: "50",
    student_count: 30, students_per_group: 2, safety_factor: "0.1",
    source_type: "solid" as const, stock_molarity: null, solute_purity: "1",
  };
  const prep = useReagentPrepChefPrep({
    apiPrefix: ref("/api/reagent"),
    form: { chemicalFormula: "NaCl", targetMolarity: "0.1", volPerGroupMl: "50", studentCount: 30,
      studentsPerGroup: 2, safetyFactor: "0.1", sourceType: "solid", stockMolarity: "1", solutePurity: "1" },
    canCalculate: ref(true), buildRequestPayload: () => payload, actionErrorMessage,
  });
  return { ...prep, actionErrorMessage };
}

describe("Reagent Prep Chef teacher-facing failures", () => {
  beforeEach(() => { api.post.mockReset(); });

  it.each([
    ["safety_factor", /marginal/i],
    ["target_molarity", /målmolaritet/i],
    ["vol_per_group_ml", /volym per grupp/i],
    ["chemical_formula", /kemisk formel/i],
    ["student_count", /antal elever/i],
    ["students_per_group", /elever per grupp/i],
    ["source_type", /källa/i],
    ["solute_purity", /renhet/i],
    ["stock_molarity", /stockmolaritet/i],
  ])("identifies rejected %s in Swedish without leaking backend prose", async (field, label) => {
    api.post.mockRejectedValue(new ApiError({
      status: 422, code: "VALIDATION_ERROR", message: "Validation error",
      details: [{ loc: ["body", field], msg: "Input should be a valid decimal", type: "decimal_parsing", input: "0,1" }],
    }));
    const prep = createPrep();
    expect(await prep.calculate()).toBe(false);
    expect(prep.actionErrorMessage.value).toMatch(label);
    expect(prep.actionErrorMessage.value).not.toMatch(/Validation error|Input should/);
    expect(prep.isCalculating.value).toBe(false);
  });

  it("reports every rejected field together, once per field, without leaking unknown issues", async () => {
    api.post.mockRejectedValue(new ApiError({
      status: 422, code: "VALIDATION_ERROR", message: "Validation error",
      details: [
        { loc: ["body", "safety_factor"], msg: "Input should be a valid decimal" },
        { loc: ["body", "stock_molarity"], msg: "Invalid stock" },
        { loc: ["body", "student_count"], msg: "Invalid integer" },
        { loc: ["body", "safety_factor"], msg: "Duplicate issue" },
        { loc: ["body", "unknown_field"], msg: "Private server details" },
      ],
    }));
    const prep = createPrep();
    expect(await prep.calculate()).toBe(false);
    const message = prep.actionErrorMessage.value ?? "";
    expect(message).toMatch(/marginal/i);
    expect(message).toMatch(/stockmolaritet/i);
    expect(message).toMatch(/antal elever/i);
    expect(message.match(/marginal/gi)).toHaveLength(1);
    expect(message).not.toMatch(/Validation error|Invalid|Duplicate|Private server/);
  });

  it.each([
    [{ loc: ["body", "unknown_field"], msg: "Private server details" }],
    [{ loc: ["query", "safety_factor"], msg: "Private server details" }],
    [null],
  ])("uses Swedish fallback for unrecognised validation details %j", async (issue) => {
    api.post.mockRejectedValue(new ApiError({
      status: 422, code: "VALIDATION_ERROR", message: "Validation error",
      details: [issue],
    }));
    const prep = createPrep();
    expect(await prep.calculate()).toBe(false);
    expect(prep.actionErrorMessage.value).toMatch(/beräkna|försök/i);
    expect(prep.actionErrorMessage.value).not.toMatch(/Validation error|Private server|marginal/i);
  });

  it("does not present arbitrary English transport errors to teachers", async () => {
    api.post.mockRejectedValue(new Error("Failed to fetch"));
    const prep = createPrep();
    expect(await prep.calculate()).toBe(false);
    expect(prep.actionErrorMessage.value).toMatch(/beräkna|försök/i);
    expect(prep.actionErrorMessage.value).not.toContain("Failed to fetch");
  });
});
