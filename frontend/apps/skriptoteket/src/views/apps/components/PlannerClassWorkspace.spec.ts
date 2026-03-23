/**
 * Planner class-workspace component tests.
 *
 * These tests verify that the class workspace stays neutral on entry, uses the
 * top segmented toggle as the only mode switch, and keeps the overview free of
 * workspace-local history controls.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerClassWorkspace from "./PlannerClassWorkspace.vue";

function buildWorkspaceSummary() {
  return {
    roster: { id: "roster-1", name: "SA24D", student_count: 28 },
    task_entry_options: [
      { draft_kind: "grouping" as const, classroom_selection_mode: "optional" as const },
      { draft_kind: "seating" as const, classroom_selection_mode: "optional" as const },
    ],
    active_grouping_draft: null,
    active_seating_draft: null,
    grouping_history: [],
    seating_history: [],
  };
}

describe("PlannerClassWorkspace", () => {
  it("opens in a neutral overview instead of expanding both task surfaces", () => {
    const wrapper = mount(PlannerClassWorkspace, {
      props: {
        isLoadingWorkspace: false,
        workspaceSummary: buildWorkspaceSummary(),
      },
    });

    expect(wrapper.text()).toContain("Klassöversikt");
    expect(wrapper.text()).toContain("28 elever");
    expect(wrapper.text()).not.toContain("Grupparbete för SA24D");
    expect(wrapper.text()).not.toContain("Sittplacering för SA24D");
  });

  it("keeps only class editing in the overview cards", async () => {
    const wrapper = mount(PlannerClassWorkspace, {
      props: {
        isLoadingWorkspace: false,
        workspaceSummary: buildWorkspaceSummary(),
      },
    });

    const buttons = wrapper.findAll("button");
    const editRosterButton = buttons.find((button) => button.text() === "Redigera klass");

    expect(editRosterButton).toBeDefined();
    expect(wrapper.text()).not.toContain("Öppna grupper");
    expect(wrapper.text()).not.toContain("Öppna sittplatser");
    expect(wrapper.text()).not.toContain("Visa grupphistorik");
    expect(wrapper.text()).not.toContain("Visa sittplatshistorik");

    if (!editRosterButton) {
      throw new Error("Expected the overview to expose class editing only.");
    }

    await editRosterButton.trigger("click");
    expect(wrapper.emitted("edit-roster")).toEqual([[]]);
  });

  it("uses the top selector as direct task entry instead of a second confirm step", async () => {
    const wrapper = mount(PlannerClassWorkspace, {
      props: {
        isLoadingWorkspace: false,
        workspaceSummary: buildWorkspaceSummary(),
      },
    });

    const groupingToggle = wrapper.findAll('[data-ui="segmented-toggle"] button').find(
      (button) => button.text() === "Grupper",
    );
    if (!groupingToggle) {
      throw new Error("Expected the segmented toggle to expose Grupper.");
    }
    await groupingToggle.trigger("click");
    expect(wrapper.emitted("open-grouping")).toEqual([[{ templateId: null }]]);

    const seatingToggle = wrapper.findAll('[data-ui="segmented-toggle"] button').find(
      (button) => button.text() === "Sittplatser",
    );
    if (!seatingToggle) {
      throw new Error("Expected the segmented toggle to expose Sittplatser.");
    }
    await seatingToggle.trigger("click");
    expect(wrapper.emitted("open-seating")).toEqual([[{ templateId: null }]]);
  });

  it("does not expose grouping history controls directly in overview", () => {
    const wrapper = mount(PlannerClassWorkspace, {
      props: {
        isLoadingWorkspace: false,
        workspaceSummary: {
          ...buildWorkspaceSummary(),
          grouping_history: [
            {
              id: "grouping-history-1",
              draft_kind: "grouping",
              template_id: null,
              template_name: null,
              status: "superseded",
              revision: 2,
              last_opened_at: "2026-03-21T09:00:00Z",
              updated_at: "2026-03-21T09:15:00Z",
            },
          ],
        },
      },
    });

    expect(wrapper.text()).not.toContain("Ingen grupphistorik ännu.");
    expect(wrapper.text()).not.toContain("Visa grupphistorik");
    expect(wrapper.text()).not.toContain("Historik");
    expect(wrapper.text()).not.toContain("Revision 2");
  });
});
