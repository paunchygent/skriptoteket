/**
 * Planner class-workspace task-entry tests: the top selector enters tasks
 * directly, and each task waits for its classlist or classroom prerequisite.
 */

import { afterEach, describe, expect, it } from "vitest";

import { mountWorkspace, findWorkspaceToggle } from "./PlannerClassWorkspace.specSupport";

describe("PlannerClassWorkspace task entry", () => {
  afterEach(() => {
    document.body.innerHTML = "";
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
});
