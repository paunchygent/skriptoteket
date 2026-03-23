/**
 * Planner workspace shell tests.
 *
 * These tests verify that the live planner shell respects the active draft
 * kind so grouping and seating do not collapse back into a shared workspace.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerWorkspaceShell from "./PlannerWorkspaceShell.vue";
import type { ClassWorkspaceSummary, PlanDraft, RoomTemplate, Roster } from "../classroomPlannerTypes";

type PlannerStateMock = {
  roster: Roster;
  template: RoomTemplate | null;
  draft: Pick<PlanDraft, "id" | "draft_kind" | "revision">;
  students: Roster["students"];
  seats: RoomTemplate["seats"];
  saveStatus: string;
  saveMessage: string | null;
  isWorkspaceBusy: boolean;
  canUndo: boolean;
  canRedo: boolean;
  reloadActiveWorkspace: ReturnType<typeof vi.fn>;
  undoSeatingDraft: ReturnType<typeof vi.fn>;
  redoSeatingDraft: ReturnType<typeof vi.fn>;
  randomizeSeating: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    roster: { id: "roster-1", name: "SA24D", students: [] },
    template: { id: "template-1", name: "Sal 101", seats: [], fixtures: [] },
    draft: { id: "draft-1", draft_kind: "grouping", revision: 3 },
    students: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ],
    seats: [
      { id: "seat-1", x: 0, y: 0, zone: null },
      { id: "seat-2", x: 120, y: 0, zone: null },
    ],
    saveStatus: "saved",
    saveMessage: null,
    isWorkspaceBusy: false,
    canUndo: false,
    canRedo: false,
    reloadActiveWorkspace: vi.fn(),
    undoSeatingDraft: vi.fn(),
    redoSeatingDraft: vi.fn(),
    randomizeSeating: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

function buildWorkspaceSummary(): ClassWorkspaceSummary {
  return {
    roster: { id: "roster-1", name: "SA24D", student_count: 28 },
    task_entry_options: [
      { draft_kind: "grouping", classroom_selection_mode: "optional" },
      { draft_kind: "seating", classroom_selection_mode: "optional" },
    ],
    active_grouping_draft: {
      id: "grouping-active-1",
      draft_kind: "grouping",
      template_id: "template-1",
      template_name: "Sal 101",
      status: "active",
      revision: 5,
      last_opened_at: "2026-03-21T10:00:00Z",
      updated_at: "2026-03-21T10:15:00Z",
    },
    active_seating_draft: {
      id: "seating-active-1",
      draft_kind: "seating",
      template_id: "template-1",
      template_name: "Sal 101",
      status: "active",
      revision: 4,
      last_opened_at: "2026-03-21T10:00:00Z",
      updated_at: "2026-03-21T10:15:00Z",
    },
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
    seating_history: [
      {
        id: "seating-history-1",
        draft_kind: "seating",
        template_id: "template-1",
        template_name: "Sal 101",
        status: "superseded",
        revision: 3,
        last_opened_at: "2026-03-21T08:00:00Z",
        updated_at: "2026-03-21T08:20:00Z",
      },
    ],
  };
}

describe("PlannerWorkspaceShell", () => {
  beforeEach(() => {
    stateMocks.plannerState.reloadActiveWorkspace.mockReset();
    stateMocks.plannerState.undoSeatingDraft.mockReset();
    stateMocks.plannerState.redoSeatingDraft.mockReset();
    stateMocks.plannerState.randomizeSeating.mockReset();
    stateMocks.plannerState.template = {
      id: "template-1",
      name: "Sal 101",
      seats: [],
      fixtures: [],
    };
    stateMocks.plannerState.students = [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ];
    stateMocks.plannerState.seats = [
      { id: "seat-1", x: 0, y: 0, zone: null },
      { id: "seat-2", x: 120, y: 0, zone: null },
    ];
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.canUndo = false;
    stateMocks.plannerState.canRedo = false;
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "grouping",
      revision: 3,
    };
  });

  it("removes the visible placement-profile entry point from the default shell", () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div>Slumpa Nytt grupputkast</div>" },
          RoomCanvas: { template: "<div />" },
          PlannerMetadataDrawer: { props: ["open"], template: "<div>{{ open ? 'open' : 'closed' }}</div>" },
        },
      },
    });

    expect(wrapper.text()).not.toContain("Placeringprofil");
    expect(wrapper.text()).toContain("Slumpa");
    expect(wrapper.text()).toContain("Nytt grupputkast");
    expect(wrapper.text()).toContain(
      "Dra elever mellan grupperna tills grupparbetet sitter.",
    );
  });

  it("keeps grouping drafts on the grouping surface only", async () => {
    stateMocks.plannerState.template = null;
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: {
            template: "<button type='button' data-test='group-student' @click=\"$emit('student-selected', 'student-1')\">Grupp</button>",
          },
          RoomCanvas: {
            template: "<button type='button' data-test='seat-student' @click=\"$emit('student-selected', 'student-1')\">Sittplats</button>",
          },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    expect(wrapper.get("[data-test='drawer']").text()).toBe("closed");
    expect(wrapper.text()).toContain("Översikt");
    expect(wrapper.text()).toContain("Sittplatser");
    expect(wrapper.text()).toContain("Utan klassrum");

    await wrapper.get("[data-test='group-student']").trigger("click");
    expect(wrapper.get("[data-test='drawer']").text()).toBe("closed");
  });

  it("keeps classroom-aware grouping as an optional in-workspace picker", async () => {
    stateMocks.plannerState.template = null;
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-2", name: "Sal 202", seats: [], fixtures: [] }],
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: {
            props: ["availableTemplates", "selectedTemplateId"],
            template: `
              <div data-test="group-board">
                <label>
                  Klassrum (valfritt)
                  <select :value="selectedTemplateId" data-test="grouping-template-select" @change="$emit('change-grouping-template', $event.target.value)">
                    <option value="">Arbeta utan klassrum</option>
                    <option value="template-2">Sal 202 · 0 platser</option>
                  </select>
                </label>
              </div>
            `,
          },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    expect(wrapper.find("[data-test='group-board']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Klassrum (valfritt)");
    expect(wrapper.text()).toContain("Arbeta utan klassrum");

    await wrapper.get('[data-test="grouping-template-select"]').setValue("template-2");

    expect(wrapper.emitted("change-grouping-template")).toEqual([[{ templateId: "template-2" }]]);
    expect((wrapper.get('[data-test="grouping-template-select"]').element as HTMLSelectElement).value).toBe("template-2");
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
          GroupBoard: {
            template: "<button type='button' data-test='new-grouping-draft' @click=\"$emit('new-grouping-draft')\">Nytt grupputkast</button>",
          },
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

  it("keeps the seating workspace open even before a classroom has been selected", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    stateMocks.plannerState.template = null;
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-2", name: "Sal 202", seats: [], fixtures: [] }],
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

    expect(wrapper.find("[data-test='group-board']").exists()).toBe(false);
    expect(wrapper.find("[data-test='room-canvas']").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Gruppvy");
    expect(wrapper.text()).toContain("Välj klassrum i sittschemat");
    expect(wrapper.text()).toContain("Klassrum");
    expect(wrapper.text()).toContain(
      "Välj eller byt klassrum direkt här i sittschemat.",
    );

    await wrapper.get("select").setValue("template-2");

    expect(wrapper.emitted("change-seating-template")).toEqual([[{ templateId: "template-2" }]]);
  });

  it("respects the initial planner view when seating already has a classroom", () => {
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

    expect(wrapper.find("[data-test='group-board']").exists()).toBe(false);
    expect(wrapper.text()).toContain("Sal 101");
    expect(wrapper.find('[data-test="seating-actions-menu"]').exists()).toBe(true);
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

    const exitButton = wrapper.findAll("button").find((button) => button.text() === "Avsluta");
    expect(exitButton).toBeDefined();
    if (!exitButton) {
      throw new Error("Expected the top panel to expose the Avsluta action.");
    }

    await exitButton.trigger("click");
    expect(wrapper.emitted("exit-to-landing")).toHaveLength(1);
  });

  it("opens grouping history from the grouping toolbar instead of overview", async () => {
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: {
            template: "<button type='button' data-test='grouping-history' @click=\"$emit('open-history')\">Historik</button>",
          },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

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
          GroupBoard: {
            template: "<button type='button' data-test='grouping-history' @click=\"$emit('open-history')\">Historik</button>",
          },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get('[data-test="grouping-history"]').trigger("click");

    const openButton = wrapper.findAll("button").find((button) => button.text().includes("Revision 2"));
    if (!openButton) {
      throw new Error("Expected the grouping history row to be openable from the grouping toolbar.");
    }
    await openButton.trigger("click");
    expect(wrapper.emitted("open-grouping-history-draft")).toEqual([["grouping-history-1"]]);

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
          GroupBoard: {
            template: "<button type='button' data-test='edit-grouping-roster' @click=\"$emit('edit-roster')\">Redigera klass</button>",
          },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get('[data-test="edit-grouping-roster"]').trigger("click");

    expect(wrapper.emitted("edit-roster")).toEqual([[]]);
  });

  it("lets the seating toolbar edit the current classroom without exposing grouping actions", async () => {
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

    expect(wrapper.text()).not.toContain("Lägg till grupp");
    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="edit-current-template"]').trigger("click");

    expect(wrapper.emitted("edit-current-template")).toEqual([[stateMocks.plannerState.template]]);
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

    expect(stateMocks.plannerState.randomizeSeating).toHaveBeenCalledTimes(1);
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
