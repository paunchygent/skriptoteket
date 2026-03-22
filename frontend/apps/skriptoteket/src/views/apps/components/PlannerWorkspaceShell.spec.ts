/**
 * Planner workspace shell tests.
 *
 * These tests verify that the live planner shell respects the active draft
 * kind so grouping and seating do not collapse back into a shared workspace.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerWorkspaceShell from "./PlannerWorkspaceShell.vue";
import type { PlanDraft, RoomTemplate, Roster } from "../classroomPlannerTypes";

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
      global: {
        stubs: {
          GroupBoard: { template: "<div />" },
          RoomCanvas: { template: "<div />" },
          PlannerMetadataDrawer: { props: ["open"], template: "<div>{{ open ? 'open' : 'closed' }}</div>" },
        },
      },
    });

    expect(wrapper.text()).not.toContain("Placeringprofil");
    expect(wrapper.text()).not.toContain("Slumpa");
    expect(wrapper.text()).toContain(
      "Dra elever mellan grupperna tills grupparbetet sitter.",
    );
  });

  it("keeps grouping drafts on the grouping surface only", async () => {
    stateMocks.plannerState.template = null;
    const wrapper = mount(PlannerWorkspaceShell, {
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
    expect(wrapper.text()).toContain("Välj klassrum för sittplatserna");
    expect(wrapper.text()).toContain(
      "Välj eller byt klassrum direkt här i sittarbetsytan.",
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
  });

  it("uses the top panel exit action instead of workspace-local navigation buttons", async () => {
    const wrapper = mount(PlannerWorkspaceShell, {
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
});
