import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { defineComponent, h, ref } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch, apiGet } from "../../../api/client";
import ReagentPrepChefView from "../ReagentPrepChefView.vue";

import { useReagentPrepChefForm } from "../../../composables/reagentPrepChef/useReagentPrepChefForm";
import ReagentPrepChefStepClass from "./ReagentPrepChefStepClass.vue";
import ReagentPrepChefStepSource from "./ReagentPrepChefStepSource.vue";

const cases = [
  { step: "class", id: "rpc-students", invalid: "", valid: "30" },
  { step: "class", id: "rpc-per-group", invalid: "", valid: "2" },
  { step: "class", id: "rpc-vol-group", invalid: "fel", valid: "25,5" },
  { step: "class", id: "rpc-safety-factor", invalid: "-0,1", valid: "0" },
  { step: "source", id: "rpc-target", invalid: "fel", valid: "0,2" },
  { step: "source", id: "rpc-purity", invalid: "", valid: "1" },
  { step: "source", id: "rpc-purity", invalid: "1,00000000000000000001", valid: "0,99999999999999999999" },
  { step: "class", id: "rpc-safety-factor", invalid: "0,50000000000000000001", valid: "0,49999999999999999999" },
  { step: "class", id: "rpc-students", invalid: "0", valid: "30" },
  { step: "class", id: "rpc-students", invalid: "1.5", valid: "30" },
  { step: "class", id: "rpc-per-group", invalid: "-1", valid: "2" },
  { step: "class", id: "rpc-per-group", invalid: "1.5", valid: "2" },
  { step: "class", id: "rpc-vol-group", invalid: "0", valid: "25,5" },
  { step: "class", id: "rpc-vol-group", invalid: "-1", valid: "25,5" },
  { step: "class", id: "rpc-safety-factor", invalid: "0,9", valid: "0,5" },
  { step: "source", id: "rpc-target", invalid: "0", valid: "0,2" },
  { step: "source", id: "rpc-target", invalid: "-0,1", valid: "0,2" },
  { step: "source", id: "rpc-purity", invalid: "0", valid: "1" },
  { step: "source", id: "rpc-purity", invalid: "1,1", valid: "0,95" },
  { step: "source", id: "rpc-stock", invalid: "0,1", valid: "2" },
  { step: "source", id: "rpc-stock", invalid: "0,05", valid: "2" },
  { step: "source", id: "rpc-stock", invalid: "", valid: "2" },
];

vi.mock("../../../api/client", () => ({
  apiGet: vi.fn(), apiFetch: vi.fn(), apiPost: vi.fn(), apiFetchBlob: vi.fn(),
  isApiError: () => false,
}));

vi.mock("../../../composables/useToast", () => ({
  useToast: () => ({ info: vi.fn(), success: vi.fn(), error: vi.fn() }),
}));

afterEach(() => { localStorage.clear(); vi.clearAllMocks(); });

describe("Reagent Prep Chef numeric entry constraints", () => {
  it("shows off-step blockers and revalidates stock when the target changes in the actual view", async () => {
    vi.mocked(apiGet).mockImplementation(async (url) => url.endsWith("/chemicals")
      ? { chemicals: [] }
      : { app_id: "chemistry.reagent_prep_chef", title: "Reagensberedning" });
    vi.mocked(apiFetch).mockResolvedValue({ defaults: null, state_rev: 0 });
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/apps/:appId", component: ReagentPrepChefView },
        { path: "/browse", component: { template: "<div />" } },
      ],
    });
    await router.push("/apps/chemistry.reagent_prep_chef");
    const wrapper = mount(ReagentPrepChefView, {
      global: { plugins: [router], stubs: { VaultPickerModal: true, ReagentPrepChefSdsModal: true } },
    });
    try {
      await flushPromises();
      const step = (name: string) => wrapper.get("nav").findAll("button").find((button) => button.text().includes(name))!;
      await step("Källa").trigger("click");
      const calculate = () => wrapper.findAll("button").find((button) => button.text() === "Beräkna")!;
      expect(calculate().attributes("disabled")).toBeDefined();
      expect(wrapper.text()).toMatch(/kemisk formel/i);
      await step("Ämne").trigger("click");
      await wrapper.get("#rpc-formula").setValue("NaCl");
      await step("Klass").trigger("click");
      await wrapper.get("#rpc-students").setValue("1.5");
      expect(wrapper.get("#rpc-students").attributes("aria-invalid")).toBe("true");
      await step("Källa").trigger("click");
      expect(calculate().attributes("disabled")).toBeDefined();
      expect(wrapper.text()).toMatch(/Antal elever.*heltal/);
      await step("Klass").trigger("click");
      await wrapper.get("#rpc-students").setValue("30");
      await step("Källa").trigger("click");
      expect(calculate().attributes("disabled")).toBeUndefined();
      await wrapper.get("#rpc-source").setValue("liquid_stock");
      await wrapper.get("#rpc-stock").setValue("0,2");
      await wrapper.get("#rpc-target").setValue("0,2");
      expect(wrapper.get("#rpc-stock").attributes("aria-invalid")).toBe("true");
      expect(calculate().attributes("disabled")).toBeDefined();
      await wrapper.get("#rpc-stock").setValue("0,200000000000000000001");
      expect(wrapper.get("#rpc-stock").attributes("aria-invalid")).not.toBe("true");
      expect(calculate().attributes("disabled")).toBeUndefined();
      await wrapper.get("#rpc-source").setValue("solid");
      expect(wrapper.find("#rpc-stock").exists()).toBe(false);
      expect(calculate().attributes("disabled")).toBeUndefined();
    } finally { wrapper.unmount(); }
  });
  it.each(cases)("explains and blocks $id=$invalid where entered, then recovers", async ({ step, id, invalid, valid }) => {
    let isCalculationAllowed = () => true;
    const wrapper = mount(defineComponent({
      setup() {
        const state = useReagentPrepChefForm(ref([]));
        isCalculationAllowed = () => state.canCalculate.value;
        Object.assign(state.form, { chemicalFormula: "NaCl", sourceType: "liquid_stock" });
        return () => step === "class" ? h(ReagentPrepChefStepClass, {
          form: state.form, derivedGroups: state.derivedGroups.value,
          derivedTotalVolumeMl: state.derivedTotalVolumeMl.value,
          fieldErrors: state.fieldErrors.value,
        }) : h(ReagentPrepChefStepSource, {
          form: state.form, canCalculate: state.canCalculate.value,
          isCalculating: false, isExporting: false, actionErrorMessage: null,
          fieldErrors: state.fieldErrors.value,
          prerequisiteErrors: [],
        });
      },
    }));
    try {
      const input = wrapper.get<HTMLInputElement>(`#${id}`);
      const action = wrapper.findAll("button").find((button) => /Fortsätt|Beräkna/.test(button.text()))!;
      await input.setValue(invalid);
      expect(input.attributes("aria-invalid")).toBe("true");
      const ids = (input.attributes("aria-describedby") ?? "").split(/\s+/).filter(Boolean);
      expect(ids.length).toBeGreaterThan(0);
      const label = wrapper.get(`label[for="${id}"]`).text().replace(/\s*\(.*/, "");
      expect(ids.some((descriptionId) => wrapper.findAll("[id]").some((node) =>
        node.attributes("id") === descriptionId && node.text().toLowerCase().includes(label.toLowerCase()),
      ))).toBe(true);
      expect(action.attributes("disabled")).toBeDefined();
      expect(isCalculationAllowed()).toBe(false);
      await input.setValue(valid);
      expect(input.attributes("aria-invalid")).not.toBe("true");
      expect(action.attributes("disabled")).toBeUndefined();
      expect(isCalculationAllowed()).toBe(true);
    } finally { wrapper.unmount(); }
  });
});
