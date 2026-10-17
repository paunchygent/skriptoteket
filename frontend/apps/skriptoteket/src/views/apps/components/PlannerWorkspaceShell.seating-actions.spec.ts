/** Seating reset, shuffle, undo/redo, history, new-draft, and busy-state workflows. */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
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

  it("confirms before clearing the current seating draft in place", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
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

    await wrapper.get('[data-test="reset-seating-draft"]').trigger("click");

    expect(wrapper.text()).toContain("Töm sittplaceringarna?");

    await wrapper.get('[data-test="confirm-dialog-confirm"]').trigger("click");

    expect(stateMocks.plannerState.clearSeatingAssignments).toHaveBeenCalledTimes(1);
    expect(wrapper.emitted("new-seating-draft")).toBeUndefined();
    expect((wrapper.get('[data-test="seating-template-select"]').element as HTMLSelectElement).value).toBe("template-1");
  });

  it("disables börja om for seating when there is nothing to clear", () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    stateMocks.plannerState.seatAssignments = [];
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
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

    expect((wrapper.get('[data-test="reset-seating-draft"]').element as HTMLButtonElement).disabled).toBe(true);
  });

  it("runs seating Slumpa from the seating action row only when a classroom is selected", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
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

    expect(wrapper.get('[data-test="randomize-seating"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="randomize-seating"]').trigger("click");

    expect(stateMocks.plannerState.runSeatingShuffle).toHaveBeenCalledTimes(1);
  });

  it("disables seating Slumpa when no classroom is selected", () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    stateMocks.plannerState.template = null;
    stateMocks.plannerState.seats = [];
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
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

    expect(wrapper.get('[data-test="randomize-seating"]').attributes("disabled")).toBeDefined();
  });

  it("runs seating undo and redo from the seating action row only when backend history allows it", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    stateMocks.plannerState.canUndo = true;
    stateMocks.plannerState.canRedo = true;
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
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

    expect(wrapper.get('[data-test="undo-seating-draft"]').attributes("disabled")).toBeUndefined();
    expect(wrapper.get('[data-test="redo-seating-draft"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="undo-seating-draft"]').trigger("click");
    await wrapper.get('[data-test="redo-seating-draft"]').trigger("click");

    expect(stateMocks.plannerState.undoSeatingDraft).toHaveBeenCalledTimes(1);
    expect(stateMocks.plannerState.redoSeatingDraft).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="grouping-history"]').exists()).toBe(false);
  });

  it("opens seating history from the seating toolbar and routes drawer actions to the parent", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
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

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="seating-history"]').trigger("click");

    expect(wrapper.text()).toContain("Aktuellt sittschema");
    expect(wrapper.text()).toContain("Tidigare sittscheman");

    const openButton = wrapper.findAll("button").find((button) => button.text().includes("Revision 3"));
    if (!openButton) {
      throw new Error("Expected the seating history row to be openable from the seating toolbar.");
    }
    await openButton.trigger("click");
    expect(wrapper.emitted("open-seating-history-draft")).toEqual([["seating-history-1"]]);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="seating-history"]').trigger("click");

    const deleteButton = wrapper.find('[aria-label="Ta bort historiskt utkast"]');
    await deleteButton.trigger("click");

    const confirmButton = wrapper.findAll("button").find((button) => button.text() === "Ta bort");
    if (!confirmButton) {
      throw new Error("Expected the live seating history drawer to confirm delete.");
    }
    await confirmButton.trigger("click");

    expect(wrapper.emitted("delete-seating-history-draft")).toEqual([["seating-history-1"]]);
  });

  it("focuses the classroom picker instead of emitting new seating draft when no classroom is selected", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    stateMocks.plannerState.template = null;
    const wrapper = mount(PlannerWorkspaceShell, {
      attachTo: document.body,
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
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

    await wrapper.get('[data-test="new-seating-draft"]').trigger("click");

    expect(wrapper.emitted("new-seating-draft")).toBeUndefined();
    expect(wrapper.get('[data-test="seating-template-select"]').element).toBe(document.activeElement);
    expect(wrapper.text()).toContain("Välj klassrum innan du startar ett nytt sittschema.");

    wrapper.unmount();
  });

  it("forwards the explicit new seating draft action with the current seating classroom", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
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

    await wrapper.get('[data-test="new-seating-draft"]').trigger("click");

    expect(wrapper.emitted("new-seating-draft")).toEqual([[{ templateId: "template-1" }]]);
  });

  it("locks seating toolbar and drawer actions while a seating lifecycle transition is in flight", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "seats",
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

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="seating-history"]').trigger("click");
    expect(wrapper.text()).toContain("Tidigare sittscheman");

    await wrapper.setProps({
      seatingLifecycleBusy: true,
      seatingHistoryBusyDraftId: "seating-history-1",
    });

    expect(wrapper.get('[data-test="undo-seating-draft"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="redo-seating-draft"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="new-seating-draft"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.get('[data-test="seating-history"]').attributes("disabled")).toBeDefined();

    const openButton = wrapper.findAll("button").find((button) => button.text().includes("Revision 3"));
    expect(openButton?.attributes("disabled")).toBeDefined();
    expect(wrapper.find('[aria-label="Ta bort historiskt utkast"]').exists()).toBe(false);

    await wrapper.get('[data-test="undo-seating-draft"]').trigger("click");
    await wrapper.get('[data-test="redo-seating-draft"]').trigger("click");
    await wrapper.get('[data-test="new-seating-draft"]').trigger("click");
    expect(wrapper.emitted("new-seating-draft")).toBeUndefined();
    expect(wrapper.emitted("open-seating-history-draft")).toBeUndefined();
    expect(wrapper.emitted("delete-seating-history-draft")).toBeUndefined();
    expect(stateMocks.plannerState.undoSeatingDraft).not.toHaveBeenCalled();
    expect(stateMocks.plannerState.redoSeatingDraft).not.toHaveBeenCalled();
  });
});
