/**
 * Planner Smart settings drawer lifecycle tests.
 *
 * These tests lock the PR-0287 panel contract: internal Smart settings remain
 * editable in place, while explicit close, backdrop, Escape, and navigation
 * paths close the panel.
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
      use_history: false,
      grouping_seating_distance_enabled: false,
    },
    isWorkspaceBusy: false,
    setDraftUseHistoryEnabled: vi.fn(),
    setDraftGroupingSeatingDistanceEnabled: vi.fn(),
  },
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("Planner Smart settings drawers", () => {
  beforeEach(() => {
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "grouping",
      use_history: false,
      grouping_seating_distance_enabled: false,
    };
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.setDraftUseHistoryEnabled.mockReset();
    stateMocks.plannerState.setDraftGroupingSeatingDistanceEnabled.mockReset();
  });

  it("keeps seating settings open for internal history changes and closes on Escape", async () => {
    const wrapper = mount(PlannerSeatingSettingsDrawer, {
      props: {
        open: true,
      },
    });

    expect(wrapper.get('[data-test="seating-settings-drawer"]').attributes("role")).toBe("dialog");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').attributes("aria-modal")).toBe("true");

    await wrapper.get('[data-test="seating-settings-history-toggle"]').trigger("click");

    expect(stateMocks.plannerState.setDraftUseHistoryEnabled).toHaveBeenCalledWith(true);
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

  it("keeps grouping settings open for internal toggles and closes on Rules navigation", async () => {
    const wrapper = mount(PlannerGroupingSettingsDrawer, {
      props: {
        open: true,
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        selectedTemplateId: "template-1",
      },
    });

    expect(wrapper.get('[data-test="grouping-settings-drawer"]').attributes("role")).toBe("dialog");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').attributes("aria-modal")).toBe("true");

    await wrapper.get('[data-test="grouping-settings-history-toggle"]').trigger("click");
    await wrapper.get('[data-test="grouping-settings-seating-toggle"]').trigger("click");

    expect(stateMocks.plannerState.setDraftUseHistoryEnabled).toHaveBeenCalledWith(true);
    expect(stateMocks.plannerState.setDraftGroupingSeatingDistanceEnabled)
      .toHaveBeenCalledWith(true);
    expect(wrapper.emitted("close")).toBeUndefined();

    await wrapper.get('[data-test="grouping-settings-open-rules"]').trigger("click");

    expect(wrapper.emitted("open-rules")).toEqual([[]]);
    expect(wrapper.emitted("close")).toEqual([[]]);
  });
});
