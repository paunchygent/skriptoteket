import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";

import { useReagentPrepChefForm } from "./useReagentPrepChefForm";
import { useReagentPrepChefPrep } from "./useReagentPrepChefPrep";

const api = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("../../api/client", () => ({
  apiPost: api.post,
  apiFetchBlob: vi.fn(),
  isApiError: () => false,
}));
vi.mock("../useToast", () => ({ useToast: () => ({ success: vi.fn() }) }));

describe("Reagent Prep Chef decimal submission", () => {
  beforeEach(() => {
    localStorage.clear();
    api.post.mockReset();
    api.post.mockResolvedValue({ sheet: null });
  });

  it.each(["comma", "point"])("sends all five %s decimals as backend-readable values", async (separator) => {
    const scope = effectScope();
    const state = scope.run(() => useReagentPrepChefForm(ref([])))!;
    const decimal = (value: string) => separator === "comma" ? value.replace(".", ",") : value;
    Object.assign(state.form, {
      chemicalFormula: "NaCl",
      targetMolarity: decimal(" 0.125 "),
      volPerGroupMl: decimal(" 25.5 "),
      safetyFactor: decimal(" 0.15 "),
      solutePurity: decimal(" 0.98 "),
      sourceType: "liquid_stock",
      stockMolarity: decimal(" 2.5 "),
    });
    const prep = useReagentPrepChefPrep({
      apiPrefix: ref("/api/reagent"),
      form: state.form,
      canCalculate: state.canCalculate,
      buildRequestPayload: state.buildRequestPayload,
      actionErrorMessage: ref(null),
    });
    try {
      expect(state.canCalculate.value).toBe(true);
      expect(await prep.calculate()).toBe(true);
      expect(api.post).toHaveBeenCalledTimes(1);
      const [url, payload] = api.post.mock.calls[0]!;
      expect(url).toBe("/api/reagent/prep");
      for (const [field, expected] of Object.entries({
        target_molarity: 0.125,
        vol_per_group_ml: 25.5,
        safety_factor: 0.15,
        solute_purity: 0.98,
        stock_molarity: 2.5,
      })) {
        expect(String(payload[field]), field).not.toContain(",");
        expect(Number(payload[field]), field).toBe(expected);
      }
      expect(payload.chemical_formula).toBe("NaCl");
      expect(payload.student_count).toBe(30);
    } finally {
      scope.stop();
    }
  });

  it.each([
    ["targetMolarity", "target_molarity"],
    ["volPerGroupMl", "vol_per_group_ml"],
    ["safetyFactor", "safety_factor"],
    ["solutePurity", "solute_purity"],
    ["stockMolarity", "stock_molarity"],
  ] as const)("preserves every decimal digit in %s without a Number round trip", (formField, payloadField) => {
    const scope = effectScope();
    const state = scope.run(() => useReagentPrepChefForm(ref([])))!;
    try {
      Object.assign(state.form, {
        chemicalFormula: "NaCl",
        sourceType: "liquid_stock",
        [formField]: " 0,12345678901234567890123456789 ",
      });
      expect(state.canCalculate.value).toBe(true);
      expect(state.buildRequestPayload()[payloadField]).toBe("0.12345678901234567890123456789");
    } finally {
      scope.stop();
    }
  });

  it.each(["0x10", "0b10", "0o10", "1,2.3", "0,1,2", "12 mL", "", " ", "NaN", "Infinity"])(
    "rejects non-decimal target input %j before sending a request",
    async (input) => {
      const scope = effectScope();
      const state = scope.run(() => useReagentPrepChefForm(ref([])))!;
      try {
        Object.assign(state.form, { chemicalFormula: "NaCl", targetMolarity: input });
        const prep = useReagentPrepChefPrep({
          apiPrefix: ref("/api/reagent"),
          form: state.form,
          canCalculate: state.canCalculate,
          buildRequestPayload: state.buildRequestPayload,
          actionErrorMessage: ref(null),
        });
        expect(state.canCalculate.value).toBe(false);
        expect(await prep.calculate()).toBe(false);
        expect(api.post).not.toHaveBeenCalled();
        expect(() => state.buildRequestPayload()).toThrow();
      } finally {
        scope.stop();
      }
    },
  );

  it("preserves decimal precision and excludes unused solid stock", () => {
    const scope = effectScope();
    const state = scope.run(() => useReagentPrepChefForm(ref([])))!;
    try {
      state.form.chemicalFormula = "NaCl";
      state.form.targetMolarity = " 0,12345678901234567890123456789 ";
      state.form.stockMolarity = "unused";
      expect(state.canCalculate.value).toBe(true);
      expect(state.buildRequestPayload().target_molarity).toBe("0.12345678901234567890123456789");
      expect(state.buildRequestPayload().stock_molarity).toBeNull();
    } finally { scope.stop(); }
  });

  it.each(["targetMolarity", "volPerGroupMl", "safetyFactor", "solutePurity", "stockMolarity"])("does not submit malformed %s", async (field) => {
    const scope = effectScope();
    const state = scope.run(() => useReagentPrepChefForm(ref([])))!;
    try {
      Object.assign(state.form, { chemicalFormula: "NaCl", sourceType: "liquid_stock", [field]: "0,1,2" });
      const prep = useReagentPrepChefPrep({
        apiPrefix: ref("/api/reagent"), form: state.form, canCalculate: state.canCalculate,
        buildRequestPayload: state.buildRequestPayload, actionErrorMessage: ref(null),
      });
      expect(state.canCalculate.value).toBe(false);
      expect(await prep.calculate()).toBe(false);
      expect(api.post).not.toHaveBeenCalled();
      expect(() => state.buildRequestPayload()).toThrow();
    } finally { scope.stop(); }
  });

  it("does not send an invalid decimal and leaves unused solid stock out of the payload", async () => {
    const scope = effectScope();
    const state = scope.run(() => useReagentPrepChefForm(ref([])))!;
    state.form.chemicalFormula = "NaCl";
    state.form.stockMolarity = "unused";
    try {
      expect(state.canCalculate.value).toBe(true);
      expect(state.buildRequestPayload().stock_molarity).toBeNull();
      state.form.targetMolarity = "0,1,2";
      const prep = useReagentPrepChefPrep({
        apiPrefix: ref("/api/reagent"),
        form: state.form,
        canCalculate: state.canCalculate,
        buildRequestPayload: state.buildRequestPayload,
        actionErrorMessage: ref(null),
      });
      expect(state.canCalculate.value).toBe(false);
      expect(await prep.calculate()).toBe(false);
      expect(api.post).not.toHaveBeenCalled();
    } finally {
      scope.stop();
    }
  });
});
