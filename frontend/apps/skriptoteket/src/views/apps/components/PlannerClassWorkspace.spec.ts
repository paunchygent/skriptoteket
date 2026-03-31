/**
 * Planner class-workspace component tests.
 *
 * These tests verify that the class workspace stays neutral on entry, uses the
 * top segmented toggle as the only mode switch, and keeps the overview free of
 * workspace-local history controls.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

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

    const createRosterButton = wrapper.findAll("button").find((button) => button.text() === "Ny klasslista");
    if (!createRosterButton) {
      throw new Error("Expected the overview to expose class creation.");
    }
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

    const groupingToggle = findWorkspaceToggle(wrapper, "Grupper");
    const seatingToggle = findWorkspaceToggle(wrapper, "Sittplatser");
    const rulesToggle = findWorkspaceToggle(wrapper, "Regler");

    expect(groupingToggle.attributes("disabled")).toBeDefined();
    expect(groupingToggle.attributes("title")).toBe("Skapa först en klasslista.");
    expect(seatingToggle.attributes("disabled")).toBeDefined();
    expect(seatingToggle.attributes("title")).toBe("Skapa först en klasslista.");
    expect(rulesToggle.attributes("disabled")).toBeDefined();
    expect(rulesToggle.attributes("title")).toBe("Skapa först en klasslista.");

    await groupingToggle.trigger("click");
    await seatingToggle.trigger("click");
    await rulesToggle.trigger("click");

    expect(wrapper.emitted("open-grouping")).toBeUndefined();
    expect(wrapper.emitted("open-seating")).toBeUndefined();
    expect(wrapper.emitted("open-rules")).toBeUndefined();
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

    expect(wrapper.text()).toContain("Inget klassrum valt");
    expect(wrapper.text()).toContain("Inget klassrum valt");
    expect(wrapper.get("[data-test='overview-classroom-empty']").text()).toContain(
      "Välj ett klassrum i listan ovan",
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

  it("renders a fixed three-column roster preview with ellipsis when not all names fit", () => {
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

    const preview = wrapper.get("[data-test='overview-roster-preview']");
    expect(preview.text()).toContain("Elev01 Andersson");
    expect(preview.text()).toContain("...");
  });
});
