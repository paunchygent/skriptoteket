/**
 * Planner class-workspace overview tests.
 *
 * These tests verify that the class workspace stays neutral on entry, keeps
 * compact management actions, and keeps the overview free of workspace-local
 * history controls.
 */

import { afterEach, describe, expect, it } from "vitest";

import { buildWorkspaceSummary, buildRosters, buildTemplates, mountWorkspace } from "./PlannerClassWorkspace.specSupport";

describe("PlannerClassWorkspace overview", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("opens in a neutral overview instead of expanding both task surfaces", () => {
    const wrapper = mountWorkspace();

    expect(wrapper.text()).toContain("Klassrum: Sal 101");
    expect(wrapper.text()).toContain("Sal 101");
    expect(wrapper.text()).toContain("28 elever");
    expect(wrapper.text()).toContain("1 platser");
    expect(wrapper.text()).not.toContain("Här hanterar du klass och klassrum i ett kompakt arbetsflöde.");
    expect(wrapper.text()).not.toContain("Redigera klassen här eller öppna en arbetsyta i väljaren ovan.");
    expect(wrapper.text()).not.toContain("Välj Grupper eller Sittplatser i väljaren ovan när du vill fortsätta arbetet.");
    expect(wrapper.text()).not.toContain("Grupparbete för SA24D");
    expect(wrapper.text()).not.toContain("Sittplacering för SA24D");
  });

  it("exposes compact class and classroom management actions from overview", async () => {
    const wrapper = mountWorkspace();

    await wrapper.get("[data-test='overview-roster-select']").setValue("roster-2");
    expect(wrapper.emitted("select-roster")).toEqual([["roster-2"]]);

    await wrapper.get("[data-test='overview-template-select']").setValue("template-2");
    expect(wrapper.emitted("select-template")).toEqual([["template-2"]]);

    const editRosterButton = wrapper.get("[data-test='overview-edit-roster']");
    await editRosterButton.trigger("click");
    expect(wrapper.emitted("edit-roster")).toEqual([[]]);

    const createRosterButton = wrapper.get("[data-test='overview-create-roster']");
    await createRosterButton.trigger("click");
    expect(wrapper.emitted("create-roster")).toEqual([[]]);

    const editTemplateButton = wrapper.get("[data-test='overview-edit-template']");
    await editTemplateButton.trigger("click");
    expect(wrapper.emitted("edit-current-template")).toEqual([[buildTemplates()[0]]]);

    const deleteRosterButton = wrapper.get("[data-test='overview-delete-roster']");
    await deleteRosterButton.trigger("click");
    expect(wrapper.emitted("delete-current-roster")).toEqual([[]]);

    const deleteTemplateButton = wrapper.get("[data-test='overview-delete-template']");
    await deleteTemplateButton.trigger("click");
    expect(wrapper.emitted("delete-current-template")).toEqual([[]]);
  });

  it("renders the phone overview as compact rows with subordinate management actions", async () => {
    const wrapper = mountWorkspace();

    const phoneDashboard = wrapper.get('[data-test="planner-phone-overview-dashboard"]');
    expect(phoneDashboard.text()).toContain("Klasslista");
    expect(phoneDashboard.text()).toContain("Klassrum");
    expect(phoneDashboard.text()).toContain("Dela");
    expect(wrapper.get('[data-test="phone-overview-share-export-row"]').text()).toContain("Dela och exportera");
    expect(wrapper.find('[data-test="phone-overview-share-export-panel"]').exists()).toBe(true);

    await wrapper.get("[data-test='phone-overview-roster-select']").setValue("roster-2");
    await wrapper.get("[data-test='phone-overview-template-select']").setValue("template-2");
    await wrapper.get("[data-test='phone-overview-edit-roster']").trigger("click");
    await wrapper.get("[data-test='phone-overview-create-roster']").trigger("click");
    await wrapper.get("[data-test='phone-overview-delete-roster']").trigger("click");
    expect(wrapper.get("[data-test='phone-overview-edit-roster']").text()).toBe("");
    expect(wrapper.get("[data-test='phone-overview-edit-roster']").attributes("aria-label")).toBe("Ändra klasslistan");
    expect(wrapper.get("[data-test='phone-overview-edit-roster']").find("svg").exists()).toBe(true);
    expect(wrapper.get("[data-test='phone-overview-create-roster']").find("svg").exists()).toBe(true);
    expect(wrapper.get("[data-test='phone-overview-delete-roster']").find("svg").exists()).toBe(true);
    expect(wrapper.get("[data-test='phone-overview-edit-template']").text()).toBe("");
    expect(wrapper.get("[data-test='phone-overview-edit-template']").attributes("aria-label")).toBe("Ändra klassrummet");
    expect(wrapper.get("[data-test='phone-overview-edit-template']").find("svg").exists()).toBe(true);
    expect(wrapper.get("[data-test='phone-overview-create-template']").find("svg").exists()).toBe(true);
    expect(wrapper.get("[data-test='phone-overview-delete-template']").find("svg").exists()).toBe(true);

    expect(wrapper.find("[data-test='phone-overview-template-row']").exists()).toBe(false);

    await wrapper.get("[data-test='phone-overview-edit-template']").trigger("click");
    await wrapper.get("[data-test='phone-overview-create-template']").trigger("click");
    await wrapper.get("[data-test='phone-overview-delete-template']").trigger("click");

    expect(wrapper.emitted("select-roster")).toContainEqual(["roster-2"]);
    expect(wrapper.emitted("select-template")).toContainEqual(["template-2"]);
    expect(wrapper.emitted("edit-roster")).toEqual([[]]);
    expect(wrapper.emitted("create-roster")).toEqual([[]]);
    expect(wrapper.emitted("delete-current-roster")).toEqual([[]]);
    expect(wrapper.emitted("edit-current-template")).toEqual([[buildTemplates()[0]]]);
    expect(wrapper.emitted("create-template")).toEqual([[]]);
    expect(wrapper.emitted("delete-current-template")).toEqual([[]]);
  });


  it("keeps overview free of duplicate resume cards even when active drafts exist", () => {
    const wrapper = mountWorkspace({
      selectedTemplateId: "template-2",
      visibleGroupingDraft: {
        id: "draft-grouping-1",
        draft_kind: "grouping",
        template_id: null,
        template_name: null,
        status: "active",
        revision: 4,
        last_opened_at: "2026-03-23T09:00:00Z",
        updated_at: "2026-03-23T09:10:00Z",
      },
      visibleSeatingDraft: {
        id: "draft-seating-1",
        draft_kind: "seating",
        template_id: "template-1",
        template_name: "Sal 101",
        status: "active",
        revision: 7,
        last_opened_at: "2026-03-23T10:00:00Z",
        updated_at: "2026-03-23T10:10:00Z",
      },
    });

    expect(wrapper.find('[data-test="overview-resumable-surface"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Fortsätt grupper");
    expect(wrapper.text()).not.toContain("Fortsätt sittschema");
  });

  it("shows an explicit empty classroom state without exposing overview history controls", () => {
    const wrapper = mountWorkspace({
      selectedTemplateId: null,
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
    });

    expect(wrapper.text()).toContain("Klassrum saknas");
    expect(wrapper.text()).not.toContain("Inget klassrum valt");
    expect(wrapper.get("[data-test='overview-classroom-empty']").text()).toContain(
      "Välj klassrum",
    );
    expect(wrapper.text()).not.toContain("Aktiv klass");
    expect(wrapper.text()).not.toContain("Neutral översikt före byte");
    expect(wrapper.text()).not.toContain("Objekt");
    expect(wrapper.text()).not.toContain("Rutnät");
    expect(wrapper.text()).not.toContain("Zoner");
    expect(wrapper.text()).not.toContain("Ingen grupphistorik ännu.");
    expect(wrapper.text()).not.toContain("Visa grupphistorik");
    expect(wrapper.text()).not.toContain("Historik");
    expect(wrapper.text()).not.toContain("Revision 2");
  });

  it("keeps desktop overview rich while phone overview stays compact", () => {
    const crowdedRoster = {
      id: "roster-1",
      name: "SA24D",
      students: Array.from({ length: 40 }, (_, index) => ({
        id: `student-${index}`,
        display_name: `Elev${String(index + 1).padStart(2, "0")} Andersson`,
      })),
    };
    const wrapper = mountWorkspace({
      availableRosters: [crowdedRoster, ...buildRosters().slice(1)],
    });

    expect(wrapper.findAll("[data-test='overview-setup-panel']")).toHaveLength(1);
    expect(wrapper.get("[data-test='overview-setup-panel']").text()).toContain("Klasslista");
    expect(wrapper.get("[data-test='overview-setup-panel']").text()).toContain("Klassrum");
    expect(wrapper.get("[data-test='overview-roster-preview']").text()).toContain("Elev01 Andersson");
    expect(wrapper.get("[data-test='overview-roster-preview']").text()).toContain("...");
    expect(wrapper.find("[data-test='overview-classroom-preview']").exists()).toBe(true);
    expect(wrapper.find("[data-test='phone-overview-roster-preview']").exists()).toBe(false);
    expect(wrapper.find("[data-test='phone-overview-roster-preview-more']").exists()).toBe(false);
  });

  it("accepts public capability overrides without changing the shared shell layout", () => {
    const wrapper = mountWorkspace({
      overviewCapabilities: {
        show_grouping_option: false,
        show_seating_option: false,
        show_rules_option: false,
        show_roster_actions: false,
        show_template_actions: false,
      },
    });

    expect(wrapper.find("[data-test='planner-top-panel-status-message']").exists()).toBe(false);
    expect(wrapper.find("[data-test='planner-top-panel-supporting-text']").exists()).toBe(false);

    expect(wrapper.find("[data-test='overview-edit-roster']").exists()).toBe(false);
    expect(wrapper.find("[data-test='overview-edit-template']").exists()).toBe(false);

    expect(wrapper.findAll('[data-ui="segmented-toggle"] button')).toHaveLength(1);
    expect(wrapper.text()).not.toContain("Grupper");
    expect(wrapper.text()).not.toContain("Sittplatser");
    expect(wrapper.text()).not.toContain("Regler");
  });
});
