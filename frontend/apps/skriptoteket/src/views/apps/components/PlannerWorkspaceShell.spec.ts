/** Shell recovery, layout, shared commands, keyboard shortcuts, and exit navigation. */

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

  it("announces authenticated conflicts and reloads the active workspace from the recovery action", async () => {
    const message = "Utkastet har ändrats i en annan flik.";
    stateMocks.plannerState.plannerConflictMessage = message;
    const wrapper = mount(PlannerWorkspaceShell, {
      props: { workspaceSummary: buildWorkspaceSummary() },
      global: {
        stubs: {
          PlannerOverviewWorkspacePane: true,
          PlannerMetadataDrawer: true,
          PlannerHistoryDrawer: true,
        },
      },
    });

    const announcement = wrapper.findAll('[role="status"]').find(
      (candidate) => candidate.text().includes(message),
    );
    expect(announcement, "conflict feedback must be announced").toBeDefined();
    const reload = wrapper.findAll("button").find(
      (candidate) => candidate.text() === "Ladda om utkast",
    );
    expect(reload).toBeDefined();
    await reload!.trigger("click");
    expect(stateMocks.plannerState.reloadActiveWorkspace).toHaveBeenCalledExactlyOnceWith();
    wrapper.unmount();
  });

  it.each([
    ["groups", "grouping", "undo-grouping", "Ångra", "canUndo", "undoGroupingDraft"],
    ["groups", "grouping", "redo-grouping", "Gör om", "canRedo", "redoGroupingDraft"],
    ["seats", "seating", "undo-seating-draft", "Ångra", "canUndo", "undoSeatingDraft"],
    ["seats", "seating", "redo-seating-draft", "Gör om", "canRedo", "redoSeatingDraft"],
  ] as const)("preserves %s %s action %s label, disabled state and command", async (view, kind, hook, label, permission, command) => {
    stateMocks.plannerState.draft = { id: "draft-1", draft_kind: kind, revision: 3 };
    const wrapper = mount(PlannerWorkspaceShell, {
      props: { initialView: view, workspaceSummary: buildWorkspaceSummary() },
      global: {
        stubs: {
          PlannerGroupingWorkspacePane: true,
          PlannerSeatingWorkspacePane: true,
          PlannerMetadataDrawer: true,
          PlannerHistoryDrawer: true,
        },
      },
    });
    const button = wrapper.get(`[data-test="${hook}"]`);
    expect(button.attributes("aria-label")).toBe(label);
    expect(button.attributes("disabled")).toBeDefined();
    await button.trigger("click");
    expect(stateMocks.plannerState[command]).not.toHaveBeenCalled();
    stateMocks.plannerState[permission] = true;
    await nextTick();
    expect(button.attributes("disabled")).toBeUndefined();
    await button.trigger("click");
    expect(stateMocks.plannerState[command]).toHaveBeenCalledExactlyOnceWith();
    wrapper.unmount();
  });

  it("removes the visible placement-profile entry point from the default shell", () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div />" },
          PlannerMetadataDrawer: { props: ["open"], template: "<div>{{ open ? 'open' : 'closed' }}</div>" },
        },
      },
    });

    expect(wrapper.text()).not.toContain("Placeringprofil");
    expect(wrapper.text()).toContain("Slumpa");
    expect(wrapper.text()).toContain("Nytt utkast");
    expect(wrapper.text()).toContain(
      "Slumpa eller placera eleverna och dra dem mellan grupperna tills du är nöjd.",
    );
  });

  it("localizes workspace notices to a toast instead of a full-width helper band", () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
        workspaceNotice: "Regler använder ett sittschema i bakgrunden.",
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div />" },
          PlannerMetadataDrawer: { props: ["open"], template: "<div>{{ open ? 'open' : 'closed' }}</div>" },
        },
      },
    });

    expect(wrapper.find('[data-test="planner-workspace-notice"]').exists()).toBe(false);
    expect(toastMocks.info).toHaveBeenCalledWith(
      "Regler använder ett sittschema i bakgrunden.",
    );
    expect(wrapper.emitted("dismiss-workspace-notice")).toEqual([[]]);
  });

  it("keeps the shell stable and hides workspace surfaces while a cross-workspace transition is loading", async () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        initialView: "groups",
        transitionLabel: "Öppnar Regler...",
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          PlannerGroupingWorkspaceToolbar: { template: "<div data-test='grouping-toolbar' />" },
          PlannerSeatingWorkspaceToolbar: { template: "<div data-test='seating-toolbar' />" },
          PlannerGroupingWorkspacePane: { template: "<div data-test='grouping-pane' />" },
          PlannerSeatingWorkspacePane: { template: "<div data-test='seating-pane' />" },
          PlannerRulesWorkspacePane: { template: "<div data-test='rules-pane' />" },
          PlannerMetadataDrawer: { props: ["open"], template: "<div data-test='drawer' />" },
          PlannerHistoryDrawer: { template: "<div data-test='history-drawer' />" },
        },
      },
    });

    expect(wrapper.text()).toContain("Öppnar Regler...");
    expect(wrapper.text()).toContain(
      "Slumpa eller placera eleverna och dra dem mellan grupperna tills du är nöjd.",
    );
    expect(wrapper.find("[data-test='grouping-toolbar']").exists()).toBe(false);
    expect(wrapper.find("[data-test='grouping-pane']").exists()).toBe(false);

    await wrapper.setProps({ initialView: "rules" });

    expect(wrapper.text()).toContain(
      "Slumpa eller placera eleverna och dra dem mellan grupperna tills du är nöjd.",
    );
    expect(wrapper.find("[data-test='rules-pane']").exists()).toBe(false);

    await wrapper.setProps({ transitionLabel: null });

    expect(wrapper.text()).toContain(
      "Här ställer du in regler som påverkar hur sittschemat skapas.",
    );
    expect(wrapper.find("[data-test='rules-pane']").exists()).toBe(true);
  });

  it("keeps grouping and seating toolbars on the shared viewport-relative sticky shell contract", () => {
    const commonGlobal = {
      stubs: {
        GroupBoard: { template: "<div data-test='group-board' />" },
        RoomCanvas: { template: "<div data-test='room-canvas' />" },
        PlannerMetadataDrawer: {
          props: ["open"],
          template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
        },
      },
    };

    const groupingWrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableRosters: buildRosters(),
        selectedRosterId: "roster-1",
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: commonGlobal,
    });

    expect(
      groupingWrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="groups"]').classes(),
    ).toEqual(
      expect.arrayContaining(["planner-workspace-toolbar-shell"]),
    );
    expect(
      groupingWrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="groups"]').classes(),
    ).not.toContain(
      "md:-top-4",
    );

    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };

    const seatingWrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: commonGlobal,
    });

    expect(
      seatingWrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="seats"]').classes(),
    ).toEqual(
      expect.arrayContaining(["planner-workspace-toolbar-shell"]),
    );
    expect(
      seatingWrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="seats"]').classes(),
    ).not.toContain(
      "md:-top-4",
    );
  });

  it("wraps grouping and seating workspaces in bounded desktop pane shells", () => {
    const commonGlobal = {
      stubs: {
        GroupBoard: { template: "<div data-test='group-board' />" },
        RoomCanvas: { template: "<div data-test='room-canvas' />" },
        PlannerMetadataDrawer: {
          props: ["open"],
          template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
        },
      },
    };

    const groupingWrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableRosters: buildRosters(),
        selectedRosterId: "roster-1",
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: commonGlobal,
    });

    expect(
      groupingWrapper.get('[data-ui="planner-workspace-pane-shell"][data-view="groups"]').classes(),
    ).toEqual(
      expect.arrayContaining(["planner-workspace-pane-shell"]),
    );

    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };

    const seatingWrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: commonGlobal,
    });

    expect(
      seatingWrapper.get('[data-ui="planner-workspace-pane-shell"][data-view="seats"]').classes(),
    ).toEqual(
      expect.arrayContaining(["planner-workspace-pane-shell"]),
    );
  });

  it("routes Cmd/Ctrl+Z to the active grouping undo action at the shell seam", async () => {
    stateMocks.plannerState.canUndo = true;
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "grouping",
      revision: 3,
    };

    mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div />" },
          PlannerMetadataDrawer: { props: ["open"], template: "<div>{{ open ? 'open' : 'closed' }}</div>" },
        },
      },
    });

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "z", ctrlKey: true }));

    expect(stateMocks.plannerState.undoGroupingDraft).toHaveBeenCalled();
  });

  it("ignores undo shortcuts while typing inside an input", async () => {
    stateMocks.plannerState.canUndo = true;
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };

    mount(PlannerWorkspaceShell, {
      props: {
        initialView: "seats",
        workspaceSummary: buildWorkspaceSummary(),
      },
      attachTo: document.body,
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

    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "z", ctrlKey: true, bubbles: true }));

    expect(stateMocks.plannerState.undoSeatingDraft).not.toHaveBeenCalled();

    document.body.removeChild(input);
  });

  it("uses the top panel exit action instead of workspace-local navigation buttons", async () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div />" },
          RoomCanvas: { template: "<div />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get('[data-test="planner-exit"]').trigger("click");
    expect(wrapper.emitted("exit-app")).toHaveLength(1);
  });
});
