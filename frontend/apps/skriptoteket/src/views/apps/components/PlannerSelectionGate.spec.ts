/**
 * Landing-gate component tests.
 *
 * These tests verify that the landing surface stays class-first while keeping
 * the top-level resumable-draft CTA visible before class selection.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerSelectionGate from "./PlannerSelectionGate.vue";

describe("PlannerSelectionGate", () => {
  it("renders a class-first landing flow instead of a class-and-classroom launch gate", () => {
    const wrapper = mount(PlannerSelectionGate, {
      props: {
        availableRosters: [{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }],
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [{ id: "seat-1", x: 0, y: 0 }], fixtures: [] }],
        selectedRosterId: "roster-1",
        resumableDraft: null,
        isLoadingCatalog: false,
      },
    });

    expect(wrapper.text()).toContain("Välj klass först");
    expect(wrapper.text()).toContain("Öppna en klass");
    expect(wrapper.text()).toContain("Hantera rumsmallar");
    expect(wrapper.text()).not.toContain("Öppna planeringen");
  });

  it("renders an explicit resume CTA when a resumable draft exists", () => {
    const wrapper = mount(PlannerSelectionGate, {
      props: {
        availableRosters: [],
        availableTemplates: [],
        selectedRosterId: null,
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
      },
    });

    expect(wrapper.text()).toContain("Fortsätt senaste utkastet");
    expect(wrapper.text()).toContain("SA24D");
    expect(wrapper.text()).toContain("Sal 101");
    expect(wrapper.text()).toContain("Stäng");
  });

  it("emits a dismiss event for the landing resumable CTA without exposing draft deletion wording", async () => {
    const wrapper = mount(PlannerSelectionGate, {
      props: {
        availableRosters: [],
        availableTemplates: [],
        selectedRosterId: null,
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
      },
    });

    await wrapper.get('button[aria-label="Stäng senaste utkastet"]').trigger("click");

    expect(wrapper.emitted("dismiss-resumable-draft")).toHaveLength(1);
    expect(wrapper.text()).not.toContain("Avsluta utkast");
  });
});
