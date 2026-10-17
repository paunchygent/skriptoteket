import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch, apiGet, apiPost } from "../../api/client";
import ReagentPrepChefView from "./ReagentPrepChefView.vue";

import type {
  AppDetailResponse,
  ReagentPrepChefChemicalsResult,
  ReagentPrepChefDefaultsResult,
  ReagentPrepChefPrepResult,
  ReagentPrepChefRiskAssessmentResult,
} from "./reagent-prep-chef/types";

const appDetail = {
  app_id: "chemistry.reagent_prep_chef",
  tool_id: "ce0e6f64-fba3-5819-b67e-28a743855648",
  title: "Reagensberedning",
  summary: null,
  min_role: "user",
  ui_mode: "bespoke_required",
} satisfies AppDetailResponse;

const prepResult = {
  sheet: {
    chemistry: {
      formula_clean: "NaCl",
      molar_mass_g_mol: "58.44",
      moles_required: "0.0825",
      mass_g: "4.8213",
      solute_purity: "1.0",
      source_type: "solid",
      target_molarity: "0.1",
    },
    logistics: {
      base_total_volume_ml: "750",
      safety_factor_pct: "10",
      total_groups: 15,
      total_volume_ml: "825",
    },
    meta: { app_version: "app:0.1.0", generated_at: "2026-10-17T12:00:00Z" },
    safety: { level: "curated", display_name: "Natriumklorid", hazard_codes: [], ppe: [] },
    instructions: ["Väg upp 4,8213 g NaCl och späd till 825 ml."],
    warnings: [],
  },
} satisfies ReagentPrepChefPrepResult;

const riskResult = {
  draft: {
    sheet: prepResult.sheet,
    context: { scope: "Beredning av NaCl-lösning", location: "Kemisal" },
    risks: [],
    requires_confirmation: false,
    missing_confirmations: [],
    export_gate: {
      ready: false,
      missing_context_fields: ["participants", "approver", "assessment_date"],
      missing_confirmations: [],
    },
    sds: { sds_ref: "NaCl", markdown_available: false, pdf_available: false },
  },
  state_rev: 1,
  warnings: [],
} satisfies ReagentPrepChefRiskAssessmentResult;

vi.mock("../../api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiFetch: vi.fn(),
  apiFetchBlob: vi.fn(),
  isApiError: () => false,
}));

vi.mock("../../composables/useToast", () => ({
  useToast: () => ({ info: vi.fn(), success: vi.fn(), error: vi.fn() }),
}));

const wrappers: ReturnType<typeof mount>[] = [];

afterEach(() => {
  wrappers.forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
  localStorage.clear();
});

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.mocked(apiGet).mockImplementation(async (url) => {
    if (url === `/api/v1/apps/${appDetail.app_id}/chemicals`) {
      return { chemicals: [] } satisfies ReagentPrepChefChemicalsResult;
    }
    if (url === `/api/v1/apps/${appDetail.app_id}`) return appDetail;
    throw new Error(`Unexpected GET: ${url}`);
  });
  vi.mocked(apiFetch).mockResolvedValue({
    defaults: null,
    state_rev: 0,
  } satisfies ReagentPrepChefDefaultsResult);
});

describe("ReagentPrepChefView step actions", () => {
  it("announces app load failures assertively while loading remains a status", async () => {
    vi.mocked(apiGet).mockRejectedValueOnce(new Error("Det gick inte att ladda appen."));
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/apps/:appId", component: ReagentPrepChefView },
        { path: "/browse", component: { template: "<div />" } },
      ],
    });
    await router.push(`/apps/${appDetail.app_id}`);
    await router.isReady();
    const wrapper = mount(ReagentPrepChefView, {
      global: { plugins: [router], stubs: { VaultPickerModal: true, ReagentPrepChefSdsModal: true } },
    });
    wrappers.push(wrapper);

    expect(wrapper.get('[role="status"]').text()).toContain("Laddar");
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    await flushPromises();
    const alert = wrapper.get('[role="alert"]');
    expect(alert.text()).toBe("Det gick inte att ladda appen.");
    expect(alert.attributes("aria-live")).toBe("assertive");
    expect(alert.attributes("aria-atomic")).toBe("true");
  });

  it("keeps result and risk disabled until a successful calculation and updates the selected step", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/apps/:appId", component: ReagentPrepChefView },
        { path: "/browse", component: { template: "<div />" } },
      ],
    });
    await router.push(`/apps/${appDetail.app_id}`);
    await router.isReady();
    const wrapper = mount(ReagentPrepChefView, {
      attachTo: document.body,
      global: {
        plugins: [router],
        stubs: {
          VaultPickerModal: true,
          ReagentPrepChefSdsModal: true,
          ReagentPrepChefStepResult: true,
          ReagentPrepChefStepRisk: true,
        },
      },
    });
    wrappers.push(wrapper);
    await flushPromises();

    const steps = wrapper.get("nav").findAll("button");
    const result = steps.find((button) => button.text() === "4. Resultat")!;
    const risk = steps.find((button) => button.text() === "5. Riskbedömning")!;
    expect(result.element.disabled).toBe(true);
    expect(risk.element.disabled).toBe(true);
    await result.trigger("click");
    await risk.trigger("click");
    expect(wrapper.find("#rpc-formula").exists()).toBe(true);

    await wrapper.get("#rpc-formula").setValue("NaCl");
    await steps.find((button) => button.text() === "3. Källa")!.trigger("click");
    expect(wrapper.find("#rpc-source").exists()).toBe(true);
    const calculate = wrapper.findAll("button").find((button) => button.text() === "Beräkna")!;

    vi.mocked(apiPost).mockRejectedValueOnce(new Error("Beräkning misslyckades"));
    await calculate.trigger("click");
    await flushPromises();
    expect(result.element.disabled).toBe(true);
    expect(risk.element.disabled).toBe(true);
    expect(wrapper.find("#rpc-source").exists()).toBe(true);

    vi.mocked(apiPost).mockResolvedValueOnce(prepResult);
    await calculate.trigger("click");
    await flushPromises();
    expect(result.element.disabled).toBe(false);
    expect(risk.element.disabled).toBe(false);
    expect(result.attributes("aria-current")).toBe("step");
    expect(wrapper.findComponent({ name: "ReagentPrepChefStepResult" }).exists()).toBe(true);

    vi.mocked(apiPost).mockResolvedValueOnce(riskResult);
    await risk.trigger("click");
    await flushPromises();
    expect(risk.attributes("aria-current")).toBe("step");
    expect(result.attributes("aria-current")).toBeUndefined();
    const riskStep = wrapper.getComponent({ name: "ReagentPrepChefStepRisk" });
    expect(riskStep.props("riskErrorMessage")).toBeNull();
    expect(riskStep.props("isRiskLoading")).toBe(false);
    expect(riskStep.props("riskDraft")).toEqual(riskResult.draft);
    expect(riskStep.props("riskContext")).toMatchObject(riskResult.draft.context);
  });
});
