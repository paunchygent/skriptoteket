/**
 * Planner Smart settings drawer lifecycle tests.
 *
 * These tests lock the Smart settings drawer contract: internal settings remain
 * editable in place, copy stays teacher-facing, and explicit close/backdrop/
 * Escape/navigation paths close the panel.
 */

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerGroupingSettingsDrawer from "./PlannerGroupingSettingsDrawer.vue";
import PlannerSeatingSettingsDrawer from "./PlannerSeatingSettingsDrawer.vue";

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    draft: {
      id: "draft-1",
      draft_kind: "grouping",
    },
    isWorkspaceBusy: false,
    setDraftSmartEnabled: vi.fn(),
    setDraftUseHistoryEnabled: vi.fn(),
    setDraftGroupingSeatingDistanceEnabled: vi.fn(),
  },
}));
const toastMocks = vi.hoisted(() => ({
  warning: vi.fn(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

vi.mock("../../../composables/useToast", () => ({
  useToast: () => toastMocks,
}));

describe("Planner Smart settings drawers", () => {
  beforeEach(() => {
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "grouping",
    };
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.setDraftSmartEnabled.mockReset();
    stateMocks.plannerState.setDraftUseHistoryEnabled.mockReset();
    stateMocks.plannerState.setDraftGroupingSeatingDistanceEnabled.mockReset();
    toastMocks.warning.mockReset();
  });

  it("renders locked seating copy, keeps internal changes open, and closes on Escape", async () => {
    const wrapper = mount(PlannerSeatingSettingsDrawer, {
      props: {
        open: true,
      },
    });

    expect(wrapper.get('[data-test="seating-settings-drawer"]').attributes("role")).toBe("dialog");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').attributes("aria-modal")).toBe("true");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Avancerade inställningar",
    );
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).not.toContain(
      "Smart-inställningar",
    );
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Smart placering",
    );
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Tar hänsyn till dina regler när du skapar en ny placering, till exempel fasta platser eller elever som inte bör sitta nära varandra.",
    );
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Försöker undvika att elever får samma plats eller samma bordsgrannar som tidigare. Stäng av om du vill börja utan historik.",
    );
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Lägg till och ändra regler för placeringar.",
    );

    await wrapper.get('[data-test="seating-settings-history-toggle"]').trigger("click");

    expect(stateMocks.plannerState.setDraftUseHistoryEnabled).toHaveBeenCalledWith(false);
    expect(wrapper.emitted("close")).toBeUndefined();

    await wrapper.get('[data-test="seating-settings-smart-toggle"]').trigger("click");

    expect(stateMocks.plannerState.setDraftSmartEnabled).toHaveBeenCalledWith(false);
    expect(toastMocks.warning).toHaveBeenCalledWith(
      "Smart är avstängt. När du slumpar tas ingen hänsyn till regler, fasta platser, nära läraren eller ihop/isär.",
    );
    expect(wrapper.emitted("close")).toBeUndefined();

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await nextTick();

    expect(wrapper.emitted("close")).toEqual([[]]);
  });

  it("closes seating settings on backdrop click", async () => {
    const wrapper = mount(PlannerSeatingSettingsDrawer, {
      props: {
        open: true,
      },
    });

    await wrapper.get('[data-test="seating-settings-backdrop"]').trigger("click");

    expect(wrapper.emitted("close")).toEqual([[]]);
  });

  it("renders locked grouping copy, keeps internal toggles open, and closes on Rules navigation", async () => {
    const wrapper = mount(PlannerGroupingSettingsDrawer, {
      props: {
        open: true,
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        selectedTemplateId: "template-1",
      },
    });

    expect(wrapper.get('[data-test="grouping-settings-drawer"]').attributes("role")).toBe("dialog");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').attributes("aria-modal")).toBe("true");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Avancerade inställningar",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).not.toContain(
      "Smart-inställningar",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Smart placering",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Tar hänsyn till dina regler när du skapar en ny placering, till exempel fasta platser eller elever som inte bör sitta nära varandra.",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Försöker undvika att elever får samma plats eller samma bordsgrannar som tidigare. Stäng av om du vill börja utan historik.",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Välj vilket klassrum gruppindelningen hör till. Det avgör vilket sittschema Smart kan använda när Tillämpa sittschema är på.",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Försöker lägga elever som redan sitter nära varandra i samma grupp. Det kan göra gruppstarten lugnare när eleverna ska arbeta från sina platser.",
    );

    await wrapper.get('[data-test="grouping-settings-history-toggle"]').trigger("click");
    await wrapper.get('[data-test="grouping-settings-smart-toggle"]').trigger("click");
    await wrapper.get('[data-test="grouping-settings-seating-toggle"]').trigger("click");

    expect(stateMocks.plannerState.setDraftUseHistoryEnabled).toHaveBeenCalledWith(false);
    expect(stateMocks.plannerState.setDraftSmartEnabled).toHaveBeenCalledWith(false);
    expect(stateMocks.plannerState.setDraftGroupingSeatingDistanceEnabled)
      .toHaveBeenCalledWith(true);
    expect(wrapper.emitted("close")).toBeUndefined();

    await wrapper.get('[data-test="grouping-settings-open-rules"]').trigger("click");

    expect(wrapper.emitted("open-rules")).toEqual([[]]);
    expect(wrapper.emitted("close")).toEqual([[]]);
  });

  it("keeps grouping seating influence off when no explicit draft flag exists", () => {
    const wrapper = mount(PlannerGroupingSettingsDrawer, {
      props: {
        open: true,
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        selectedTemplateId: "template-1",
      },
    });

    expect(wrapper.get('[data-test="grouping-settings-seating-toggle"]').attributes("aria-checked")).toBe(
      "false",
    );
  });

  it("explains missing classroom before seating influence can apply", () => {
    const wrapper = mount(PlannerGroupingSettingsDrawer, {
      props: {
        open: true,
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        selectedTemplateId: null,
      },
    });

    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Välj först ett klassrum så Smart vet vilket sittschema som kan användas.",
    );
    expect(wrapper.get('[data-test="grouping-settings-seating-toggle"]').attributes("disabled")).toBe("");
  });

  it("omits account-backed history when public guest settings pass disables it", () => {
    const wrapper = mount(PlannerSeatingSettingsDrawer, {
      props: {
        open: true,
        showHistorySetting: false,
      },
    });

    expect(wrapper.find('[data-test="seating-settings-history-toggle"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).not.toContain("Historik");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Smart placering",
    );
  });
});
