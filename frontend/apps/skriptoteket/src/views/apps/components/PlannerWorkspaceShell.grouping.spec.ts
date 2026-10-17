/** Grouping count, student pool, context changes, history, editing, and export workflows. */

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildRosters,
  buildWorkspaceSummary,
  resetPlannerState,
  stateMocks,
  toastMocks,
} from "./PlannerWorkspaceShell.test-support";
import PlannerWorkspaceShell from "./PlannerWorkspaceShell.vue";

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

vi.mock("../../../composables/useToast", () => ({
  useToast: () => toastMocks,
}));

describe("PlannerWorkspaceShell", () => {
  beforeEach(resetPlannerState);

  it("preserves grouping count action labels, disabled state and commands", async () => {
    stateMocks.plannerState.groups.push({ id: "group-b", name: "Grupp B", sort_order: 1, name_is_custom: false });
    const wrapper = mount(PlannerWorkspaceShell, {
      props: { initialView: "groups", workspaceSummary: buildWorkspaceSummary() },
      global: {
        stubs: {
          PlannerGroupingWorkspacePane: true,
          PlannerMetadataDrawer: true,
          PlannerHistoryDrawer: true,
        },
      },
    });
    const decrement = wrapper.get('[data-test="decrement-group-count"]');
    const increment = wrapper.get('[data-test="increment-group-count"]');
    expect(decrement.attributes("aria-label")).toBe("Minska antal grupper");
    expect(increment.attributes("aria-label")).toBe("Öka antal grupper");
    expect(decrement.attributes("disabled")).toBeUndefined();
    expect(increment.attributes("disabled")).toBeUndefined();
    await decrement.trigger("click");
    expect(stateMocks.plannerState.removeGroup).toHaveBeenCalledExactlyOnceWith("group-b");
    await increment.trigger("click");
    expect(stateMocks.plannerState.addGroup).toHaveBeenCalledExactlyOnceWith();
    stateMocks.plannerState.isWorkspaceBusy = true;
    await nextTick();
    expect(decrement.attributes("disabled")).toBeDefined();
    expect(increment.attributes("disabled")).toBeDefined();
    await decrement.trigger("click");
    await increment.trigger("click");
    expect(stateMocks.plannerState.removeGroup).toHaveBeenCalledTimes(1);
    expect(stateMocks.plannerState.addGroup).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("keeps grouping drafts on the grouping surface only", async () => {
    stateMocks.plannerState.template = null;
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    expect(wrapper.text()).toContain("Översikt");
    expect(wrapper.text()).toContain("Sittplatser");
    expect(wrapper.text()).toContain("Utan klassrum");

    const groupingPoolStudent = wrapper.get("[data-test='grouping-student-pool'] button");

    expect(groupingPoolStudent.classes()).toContain("planner-choice-button-strong");
    expect(groupingPoolStudent.classes()).not.toContain("planner-choice-button-active");

    await groupingPoolStudent.trigger("click");

    expect(groupingPoolStudent.classes()).toContain("planner-choice-button-strong");
    expect(groupingPoolStudent.classes()).not.toContain("planner-choice-button-active");
  });

  it("forwards the explicit new grouping draft action with the current grouping context", async () => {
    stateMocks.plannerState.template = {
      id: "template-2",
      name: "Sal 202",
      seats: [],
      fixtures: [],
    };
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get("[data-test='new-grouping-draft']").trigger("click");

    expect(wrapper.emitted("new-grouping-draft")).toEqual([[{ templateId: "template-2" }]]);
  });

  it("forwards grouping class changes from the toolbar selector", async () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableRosters: buildRosters(),
        selectedRosterId: "roster-1",
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get('[data-test="grouping-roster-select"]').setValue("roster-2");

    expect(wrapper.emitted("change-grouping-roster")).toEqual([[{ rosterId: "roster-2" }]]);
  });

  it("opens grouping history from the grouping toolbar instead of overview", async () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="grouping-history"]').trigger("click");

    expect(wrapper.text()).toContain("Aktuellt grupputkast");
    expect(wrapper.text()).toContain("Tidigare grupputkast");
    expect(wrapper.text()).toContain("Revision 2");
  });

  it("routes grouping history drawer actions back to the parent from the live workspace", async () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="grouping-history"]').trigger("click");

    const openButton = wrapper.findAll("button").find((button) => button.text().includes("Revision 2"));
    if (!openButton) {
      throw new Error("Expected the grouping history row to be openable from the grouping toolbar.");
    }
    await openButton.trigger("click");
    expect(wrapper.emitted("open-grouping-history-draft")).toEqual([["grouping-history-1"]]);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="grouping-history"]').trigger("click");

    const deleteButton = wrapper.find('[aria-label="Ta bort historiskt utkast"]');
    await deleteButton.trigger("click");

    const confirmButton = wrapper.findAll("button").find((button) => button.text() === "Ta bort");
    if (!confirmButton) {
      throw new Error("Expected the live history drawer to confirm delete.");
    }
    await confirmButton.trigger("click");

    expect(wrapper.emitted("delete-grouping-history-draft")).toEqual([["grouping-history-1"]]);
  });

  it("lets the grouping toolbar open Redigera klass for parity with seating settings", async () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="edit-grouping-roster"]').trigger("click");

    expect(wrapper.emitted("edit-roster")).toEqual([[]]);
  });

  it("forwards grouping export actions without changing the seating-only defaults", async () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get('[data-test="grouping-share-trigger"]').trigger("click");
    await wrapper.get('[data-test="grouping-export-option-xlsx"]').trigger("click");
    expect(wrapper.emitted("export-grouping-default")).toEqual([[]]);

    await wrapper.get('[data-test="grouping-export-option-pdf"]').trigger("click");

    expect(wrapper.emitted("export-grouping-option")).toEqual([["pdf_a4_portrait"]]);
    expect(wrapper.text()).not.toContain("Affisch (A3)");
  });
});
