import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerSelectionGate from "./PlannerSelectionGate.vue";

describe("PlannerSelectionGate", () => {
  it("shows the planner launch CTA when class and classroom are selected", () => {
    const wrapper = mount(PlannerSelectionGate, {
      props: {
        availableRosters: [{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }],
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [{ id: "seat-1", x: 0, y: 0 }], fixtures: [] }],
        selectedRosterId: "roster-1",
        selectedTemplateId: "template-1",
        resumableDraft: null,
        isLoadingCatalog: false,
        canStartPlanning: true,
      },
    });

    expect(wrapper.text()).toContain("Öppna planeringen");
    expect(wrapper.text()).not.toContain("Lektionsläge");
  });

  it("renders an explicit resume CTA when a resumable draft exists", () => {
    const wrapper = mount(PlannerSelectionGate, {
      props: {
        availableRosters: [],
        availableTemplates: [],
        selectedRosterId: null,
        selectedTemplateId: null,
        resumableDraft: {
          draft: {
            id: "draft-1",
            roster_id: "roster-1",
            draft_kind: "seating",
            template_id: "template-1",
            status: "active",
            revision: 2,
            last_opened_at: "2026-03-21T10:00:00Z",
          },
          roster_name: "SA24D",
          template_name: "Sal 101",
        },
        isLoadingCatalog: false,
        canStartPlanning: false,
      },
    });

    expect(wrapper.text()).toContain("Fortsätt senaste utkastet");
    expect(wrapper.text()).toContain("SA24D");
    expect(wrapper.text()).toContain("Sal 101");
    expect(wrapper.text()).toContain("Avsluta utkast");
  });
});
