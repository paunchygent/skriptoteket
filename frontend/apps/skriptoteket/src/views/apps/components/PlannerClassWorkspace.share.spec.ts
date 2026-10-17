/**
 * Planner class-workspace share and export scope tests: the phone Dela
 * affordance, scope availability and the default scope.
 */

import { afterEach, describe, expect, it } from "vitest";

import { groupingShare, mountWorkspace } from "./PlannerClassWorkspace.specSupport";

describe("PlannerClassWorkspace share scopes", () => {
  afterEach(() => {
    document.body.innerHTML = "";
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

  it("keeps a workspace-created grouping link visible as the default overview share scope", async () => {
    const wrapper = mountWorkspace({
      groupingShares: [groupingShare],
    });

    expect(wrapper.get("[data-test='planner-share-export-scope-meta']").text())
      .toContain("Gruppindelning · 28 elever");
    expect(wrapper.get("[data-test='planner-share-link-share-1']").text()).toContain("SA24D grupper");

    await wrapper.get("[data-test='phone-overview-share-create-mobile']").trigger("click");
    await wrapper.get("[data-test='phone-overview-export-option-xlsx']").trigger("click");

    expect(wrapper.emitted("share-overview-grouping-link")).toEqual([[]]);
    expect(wrapper.emitted("export-overview-grouping-default")).toEqual([[]]);
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
});
