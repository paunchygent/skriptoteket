/**
 * Planner class-workspace component tests.
 *
 * These tests verify that the class workspace stays neutral on entry, uses the
 * top segmented toggle as the only mode switch, and keeps the overview free of
 * workspace-local history controls.
 */

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { RoomTemplate } from "../classroomPlannerTypes";
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

function buildRosters() {
  return [
    { id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] },
    { id: "roster-2", name: "NA25A", students: [{ id: "s2", display_name: "Bo" }] },
  ];
}

function buildTemplates(): RoomTemplate[] {
  return [
    {
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [{ id: "seat-1", x: 96, y: 96, zone: "front" }],
      fixtures: [
        {
          id: "door-1",
          type: "door",
          x: 0,
          y: 96,
          width: 96,
          height: 96,
          label: null,
        },
      ],
    },
    {
      id: "template-2",
      name: "Sal 202",
      grid_cols: 12,
      grid_rows: 8,
      seats: [{ id: "seat-2", x: 192, y: 192, zone: "middle" }],
      fixtures: [],
    },
  ];
}

function mountWorkspace(props?: Record<string, unknown>) {
  return mount(PlannerClassWorkspace, {
    props: {
      isLoadingWorkspace: false,
      workspaceSummary: buildWorkspaceSummary(),
      availableRosters: buildRosters(),
      availableTemplates: buildTemplates(),
      selectedRosterId: "roster-1",
      selectedTemplateId: "template-1",
      visibleGroupingDraft: null,
      visibleSeatingDraft: null,
      ...props,
    },
  });
}

function findWorkspaceToggle(
  wrapper: ReturnType<typeof mountWorkspace>,
  label: "Grupper" | "Sittplatser" | "Regler",
) {
  const button = wrapper.findAll('[data-ui="segmented-toggle"] button').find(
    (candidate) => candidate.text() === label,
  );
  if (!button) {
    throw new Error(`Expected the segmented toggle to expose ${label}.`);
  }
  return button;
}

describe("PlannerClassWorkspace", () => {
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
    expect(wrapper.get("[data-test='phone-overview-edit-roster']").text()).toContain("Ändra");
    expect(wrapper.get("[data-test='phone-overview-edit-roster']").find("svg").exists()).toBe(true);
    expect(wrapper.get("[data-test='phone-overview-create-roster']").find("svg").exists()).toBe(true);
    expect(wrapper.get("[data-test='phone-overview-delete-roster']").find("svg").exists()).toBe(true);
    expect(wrapper.get("[data-test='phone-overview-edit-template']").text()).toContain("Ändra");
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

  it("renders the phone Dela affordance expanded in place with grouping and seating scopes", async () => {
    const wrapper = mountWorkspace();

    expect(wrapper.find("[data-test='phone-overview-share-export-panel']").exists()).toBe(true);
    expect(wrapper.get("[data-test='planner-share-export-scope-grouping']").text()).toContain("Gruppindelning");
    expect(wrapper.get("[data-test='planner-share-export-scope-seating']").text()).toContain("Sittschema");
    expect(wrapper.get("[data-test='planner-share-export-scope-context']").text()).toBe("SA24D · Sal 101");
    expect(wrapper.get("[data-test='planner-share-export-scope-meta']").text()).toContain("Sittschema · 1 plats");
    expect(wrapper.get("[data-test='phone-overview-share-export-panel']").text()).not.toContain("Länk, PDF, Excel");
    expect(wrapper.get("[data-test='phone-overview-share-export-panel']").text()).not.toContain(
      "Aktiva länkar visas här",
    );
    expect(wrapper.emitted("prepare-overview-distribution")).toEqual([["seating"]]);
    expect(wrapper.emitted("open-seating")).toBeUndefined();
    expect(wrapper.emitted("open-grouping")).toBeUndefined();

    await wrapper.get("[data-test='planner-share-export-scope-grouping']").trigger("click");
    expect(wrapper.emitted("prepare-overview-distribution")).toEqual([["seating"], ["grouping"]]);
    expect(wrapper.get("[data-test='planner-share-export-scope-context']").text()).toBe("SA24D · Sal 101");
    expect(wrapper.get("[data-test='planner-share-export-scope-meta']").text()).toContain("Gruppindelning · 28 elever");

    await wrapper.get("[data-test='phone-overview-share-create-mobile']").trigger("click");
    await wrapper.get("[data-test='phone-overview-export-option-xlsx']").trigger("click");
    expect(wrapper.emitted("share-overview-grouping-link")).toEqual([[]]);
    expect(wrapper.emitted("export-overview-grouping-default")).toEqual([[]]);
  });

  it("keeps seating share disabled in overview until a classroom is selected", async () => {
    const wrapper = mountWorkspace({
      selectedTemplateId: null,
    });

    expect(wrapper.emitted("prepare-overview-distribution")).toEqual([["grouping"]]);
    expect(wrapper.get("[data-test='planner-share-export-scope-seating']").attributes("disabled"))
      .toBeDefined();
    expect(wrapper.get("[data-test='planner-share-export-scope-prerequisite']").text())
      .toBe("Sittschema: Välj ett klassrum först.");
  });

  it("does not preselect a share/export scope when requirements are missing", () => {
    const wrapper = mountWorkspace({
      selectedRosterId: null,
      selectedTemplateId: null,
      workspaceSummary: null,
      availableRosters: [],
      availableTemplates: [],
    });

    const groupingScope = wrapper.get("[data-test='planner-share-export-scope-grouping']");
    const seatingScope = wrapper.get("[data-test='planner-share-export-scope-seating']");

    expect(groupingScope.attributes("disabled")).toBeDefined();
    expect(seatingScope.attributes("disabled")).toBeDefined();
    expect(groupingScope.attributes("aria-pressed")).toBe("false");
    expect(seatingScope.attributes("aria-pressed")).toBe("false");
    expect(groupingScope.classes()).not.toContain("bg-action");
    expect(seatingScope.classes()).not.toContain("bg-action");
    expect(wrapper.find("[data-test='planner-share-export-scope-summary']").exists()).toBe(false);
    expect(wrapper.get("[data-test='planner-share-export-scope-prerequisite']").text())
      .toBe("Skapa en klasslista först.");
    expect(wrapper.get("[data-test='phone-overview-share-export-panel']").text()).not.toContain("Länk");
    expect(wrapper.get("[data-test='phone-overview-share-export-panel']").text()).not.toContain("Filer");
  });

  it("uses the top selector as direct task entry and carries the selected classroom only for seating", async () => {
    const wrapper = mountWorkspace({
      selectedTemplateId: "template-2",
    });

    const groupingToggle = findWorkspaceToggle(wrapper, "Grupper");
    await groupingToggle.trigger("click");
    expect(groupingToggle.attributes("aria-checked")).toBe("false");
    expect(wrapper.emitted("open-grouping")).toEqual([[{ templateId: null }]]);

    const seatingToggle = findWorkspaceToggle(wrapper, "Sittplatser");
    await seatingToggle.trigger("click");
    expect(seatingToggle.attributes("aria-checked")).toBe("false");
    expect(wrapper.emitted("open-seating")).toEqual([[{ templateId: "template-2" }]]);
  });

  it("locks every task workspace until a classlist has been selected", async () => {
    const wrapper = mountWorkspace({
      workspaceSummary: null,
      availableRosters: [],
      availableTemplates: [],
      selectedRosterId: null,
      selectedTemplateId: null,
    });

    expect(wrapper.get("[data-test='planner-top-panel-status-message']").text()).toBe(
      "Börja med att skapa en klasslista.",
    );
    expect(wrapper.get("[data-test='planner-top-panel-supporting-text']").text()).toBe(
      "Behöver du mer vägledning kan du trycka på Hjälp.",
    );
    expect(wrapper.get("[data-test='planner-top-panel-compact-status-message']").text()).toBe(
      "Börja med att skapa en klasslista. Tryck på hjälp för vägledning.",
    );
    expect(wrapper.text()).toContain("Klass saknas");
    expect(wrapper.text()).toContain("Klassrum saknas");
    expect(wrapper.text()).not.toContain("Planering");
    expect(wrapper.text()).not.toContain("Inget klassrum valt");
    expect(wrapper.get("[data-test='phone-overview-roster-select']").text()).toContain("Skapa en klasslista");
    expect(wrapper.get("[data-test='phone-overview-template-select']").text()).toContain("Skapa ett klassrum");
    expect(wrapper.get("[data-test='phone-overview-edit-roster']").attributes("disabled")).toBeDefined();
    expect(wrapper.get("[data-test='phone-overview-delete-roster']").attributes("disabled")).toBeDefined();
    expect(wrapper.get("[data-test='phone-overview-edit-template']").attributes("disabled")).toBeDefined();
    expect(wrapper.get("[data-test='phone-overview-delete-template']").attributes("disabled")).toBeDefined();

    const groupingToggle = findWorkspaceToggle(wrapper, "Grupper");
    const seatingToggle = findWorkspaceToggle(wrapper, "Sittplatser");
    const rulesToggle = findWorkspaceToggle(wrapper, "Regler");

    expect(groupingToggle.attributes("disabled")).toBeDefined();
    expect(groupingToggle.attributes("title")).toBe("Skapa först en klasslista.");
    expect(seatingToggle.attributes("disabled")).toBeDefined();
    expect(seatingToggle.attributes("title")).toBe("Skapa först en klasslista.");
    expect(rulesToggle.attributes("disabled")).toBeDefined();
    expect(rulesToggle.attributes("title")).toBe("Skapa först en klasslista.");

    await wrapper.get("[data-test='planner-phone-mode-sheet-trigger']").trigger("click");

    const phoneGrouping = document.body.querySelector<HTMLButtonElement>(
      "[data-test='planner-phone-mode-sheet-grouping']",
    );
    const phoneSeating = document.body.querySelector<HTMLButtonElement>(
      "[data-test='planner-phone-mode-sheet-seating']",
    );
    const phoneRules = document.body.querySelector<HTMLButtonElement>(
      "[data-test='planner-phone-mode-sheet-rules']",
    );

    expect(phoneGrouping?.disabled).toBe(true);
    expect(phoneGrouping?.title).toBe("Skapa först en klasslista.");
    expect(phoneSeating?.disabled).toBe(true);
    expect(phoneSeating?.title).toBe("Skapa först en klasslista.");
    expect(phoneRules?.disabled).toBe(true);
    expect(phoneRules?.title).toBe("Skapa först en klasslista.");
    expect(wrapper.get("[data-test='phone-overview-share-export-row']").attributes("disabled"))
      .toBeDefined();

    await groupingToggle.trigger("click");
    await seatingToggle.trigger("click");
    await rulesToggle.trigger("click");

    expect(wrapper.emitted("open-grouping")).toBeUndefined();
    expect(wrapper.emitted("open-seating")).toBeUndefined();
    expect(wrapper.emitted("open-rules")).toBeUndefined();
    const rosterPanelText = wrapper.get('[data-test="overview-roster-panel"]').text();
    expect(rosterPanelText).toContain("Klasslista");
    expect(rosterPanelText).toContain("0 elever");
    expect(rosterPanelText).not.toContain("VÄLJ EN KLASSLISTA");
  });

  it("keeps Grupper and Regler available while Sittplatser waits for a classroom", async () => {
    const wrapper = mountWorkspace({
      selectedTemplateId: null,
    });

    expect(wrapper.get("[data-test='planner-top-panel-status-message']").text()).toBe(
      "Nu har du skapat din klass. Skapa eller välj ett klassrum för att använda Sittplatser.",
    );
    expect(wrapper.get("[data-test='planner-top-panel-supporting-text']").text()).toBe(
      "Behöver du mer vägledning kan du trycka på Hjälp.",
    );

    const groupingToggle = findWorkspaceToggle(wrapper, "Grupper");
    const seatingToggle = findWorkspaceToggle(wrapper, "Sittplatser");
    const rulesToggle = findWorkspaceToggle(wrapper, "Regler");

    expect(groupingToggle.attributes("disabled")).toBeUndefined();
    expect(seatingToggle.attributes("disabled")).toBeDefined();
    expect(seatingToggle.attributes("title")).toBe("Skapa eller välj först ett klassrum.");
    expect(rulesToggle.attributes("disabled")).toBeUndefined();

    await wrapper.get("[data-test='planner-phone-mode-sheet-trigger']").trigger("click");

    const phoneGrouping = document.body.querySelector<HTMLButtonElement>(
      "[data-test='planner-phone-mode-sheet-grouping']",
    );
    const phoneSeating = document.body.querySelector<HTMLButtonElement>(
      "[data-test='planner-phone-mode-sheet-seating']",
    );
    const phoneRules = document.body.querySelector<HTMLButtonElement>(
      "[data-test='planner-phone-mode-sheet-rules']",
    );

    expect(phoneGrouping?.disabled).toBe(false);
    expect(phoneSeating?.disabled).toBe(true);
    expect(phoneSeating?.title).toBe("Skapa eller välj först ett klassrum.");
    expect(phoneRules?.disabled).toBe(false);

    await groupingToggle.trigger("click");
    await seatingToggle.trigger("click");
    await rulesToggle.trigger("click");

    expect(wrapper.emitted("open-grouping")).toEqual([[{ templateId: null }]]);
    expect(wrapper.emitted("open-seating")).toBeUndefined();
    expect(wrapper.emitted("open-rules")).toEqual([[]]);
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
