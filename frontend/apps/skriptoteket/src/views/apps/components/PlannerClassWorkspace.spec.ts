/**
 * Planner class-workspace component tests.
 *
 * These tests verify that the class-first workspace renders task-separated
 * grouping and seating cards while keeping the seating entry dependent on a
 * classroom selection.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerClassWorkspace from "./PlannerClassWorkspace.vue";

describe("PlannerClassWorkspace", () => {
  it("renders task-separated workspace cards for the selected class", () => {
    const wrapper = mount(PlannerClassWorkspace, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [{ id: "seat-1", x: 0, y: 0 }], fixtures: [] }],
        selectedTemplateId: null,
        isLoadingWorkspace: false,
        workspaceSummary: {
          roster: { id: "roster-1", name: "SA24D", student_count: 28 },
          task_entry_options: [
            { draft_kind: "grouping", classroom_selection_mode: "optional" },
            { draft_kind: "seating", classroom_selection_mode: "required" },
          ],
          active_grouping_draft: {
            id: "grouping-1",
            draft_kind: "grouping",
            status: "active",
            revision: 2,
            last_opened_at: "2026-03-21T10:00:00Z",
            updated_at: "2026-03-21T10:05:00Z",
          },
          active_seating_draft: null,
          grouping_history: [],
          seating_history: [],
        },
      },
    });

    expect(wrapper.text()).toContain("Klassarbetsyta");
    expect(wrapper.text()).toContain("SA24D");
    expect(wrapper.text()).toContain("Fortsätt grupper");
    expect(wrapper.text()).toContain("Öppna sittplatser");
  });

  it("keeps seating launch disabled until a classroom is selected when no active seating draft exists", () => {
    const wrapper = mount(PlannerClassWorkspace, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [{ id: "seat-1", x: 0, y: 0 }], fixtures: [] }],
        selectedTemplateId: null,
        isLoadingWorkspace: false,
        workspaceSummary: {
          roster: { id: "roster-1", name: "SA24D", student_count: 28 },
          task_entry_options: [
            { draft_kind: "grouping", classroom_selection_mode: "optional" },
            { draft_kind: "seating", classroom_selection_mode: "required" },
          ],
          active_grouping_draft: null,
          active_seating_draft: null,
          grouping_history: [],
          seating_history: [],
        },
      },
    });

    const openSeatingButton = wrapper.findAll("button.btn-cta")[1];
    expect(openSeatingButton.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("Välj klassrum för att öppna sittplatser");
  });
});
