/**
 * Planner history drawer tests.
 *
 * These tests verify that grouping history stays secondary in the overlay
 * drawer while still exposing explicit open/delete actions for historic drafts.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerHistoryDrawer from "./PlannerHistoryDrawer.vue";

const historySummary = {
  id: "grouping-history-1",
  draft_kind: "grouping" as const,
  template_id: null,
  template_name: null,
  status: "superseded" as const,
  revision: 2,
  last_opened_at: "2026-03-21T09:00:00Z",
  updated_at: "2026-03-21T09:15:00Z",
};

describe("PlannerHistoryDrawer", () => {
  it("shows the active grouping draft separately from older drafts", () => {
    const wrapper = mount(PlannerHistoryDrawer, {
      props: {
        open: true,
        title: "Grupper",
        activeSummary: {
          ...historySummary,
          id: "active-grouping",
          status: "active",
          revision: 5,
        },
        summaries: [historySummary],
        emptyLabel: "Ingen grupphistorik ännu.",
        activeLabel: "Aktuellt grupputkast",
        historyLabel: "Tidigare grupputkast",
      },
    });

    expect(wrapper.text()).toContain("Aktuellt grupputkast");
    expect(wrapper.text()).toContain("Tidigare grupputkast");
    expect(wrapper.text()).toContain("Aktivt nu");
  });

  it("emits open and confirmed delete for historic grouping drafts only", async () => {
    const wrapper = mount(PlannerHistoryDrawer, {
      props: {
        open: true,
        title: "Grupper",
        summaries: [historySummary],
        emptyLabel: "Ingen grupphistorik ännu.",
        canOpenSummaries: true,
        canDeleteSummaries: true,
      },
    });

    const openButton = wrapper.findAll("button").find((button) => button.text().includes("Revision 2"));
    if (!openButton) {
      throw new Error("Expected the historic summary to render as an openable button.");
    }
    await openButton.trigger("click");

    const deleteButton = wrapper.find('[aria-label="Ta bort historiskt utkast"]');
    await deleteButton.trigger("click");
    expect(wrapper.text()).toContain("Ta bort utkast?");

    const confirmButton = wrapper.findAll("button").find((button) => button.text() === "Ta bort");
    if (!confirmButton) {
      throw new Error("Expected the drawer to render a delete confirmation button.");
    }
    await confirmButton.trigger("click");

    expect(wrapper.emitted("open-summary")).toEqual([["grouping-history-1"]]);
    expect(wrapper.emitted("delete-summary")).toEqual([["grouping-history-1"]]);
  });
});
