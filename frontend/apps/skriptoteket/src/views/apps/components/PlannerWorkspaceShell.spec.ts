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
  saveStatus: string;
  saveMessage: string | null;
  reloadActiveWorkspace: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    roster: { id: "roster-1", name: "SA24D", students: [] },
    template: { id: "template-1", name: "Sal 101", seats: [], fixtures: [] },
    draft: { id: "draft-1", draft_kind: "grouping", revision: 3 },
    saveStatus: "saved",
    saveMessage: null,
    reloadActiveWorkspace: vi.fn(),
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
    seating_history: [],
  };
}

describe("PlannerWorkspaceShell", () => {
  beforeEach(() => {
    stateMocks.plannerState.reloadActiveWorkspace.mockReset();
    stateMocks.plannerState.template = {
      id: "template-1",
      name: "Sal 101",
      seats: [],
      fixtures: [],
    };
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
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    expect(wrapper.find("[data-test='group-board']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Grupper utan klassrumsstöd");
    expect(wrapper.text()).toContain("Arbeta utan klassrum");

    await wrapper.get("select").setValue("template-2");

    expect(wrapper.emitted("change-grouping-template")).toEqual([[{ templateId: "template-2" }]]);
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
    expect(wrapper.text()).toContain("Välj klassrum för sittschemat");
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
    expect(wrapper.find("[data-test='room-canvas']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Sal 101");
    expect(wrapper.text()).toContain("Redigera klassrum");
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

    const deleteButton = wrapper.find('[aria-label="Ta bort historiskt utkast"]');
    await deleteButton.trigger("click");

    const confirmButton = wrapper.findAll("button").find((button) => button.text() === "Ta bort");
    if (!confirmButton) {
      throw new Error("Expected the live history drawer to confirm delete.");
    }
    await confirmButton.trigger("click");

    expect(wrapper.emitted("open-grouping-history-draft")).toEqual([["grouping-history-1"]]);
    expect(wrapper.emitted("delete-grouping-history-draft")).toEqual([["grouping-history-1"]]);
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
    await wrapper.get('[data-test="edit-current-template"]').trigger("click");

    expect(wrapper.emitted("edit-current-template")).toEqual([[stateMocks.plannerState.template]]);
  });
});
