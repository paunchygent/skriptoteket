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
      "Bygg arbetsgrupper genom att dra elever till rätt grupp och justera grupperna efter behov.",
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
    expect(wrapper.text()).not.toContain("Sittplatser");
    expect(wrapper.text()).toContain("Utan klassrum");

    await wrapper.get("[data-test='group-student']").trigger("click");
    expect(wrapper.get("[data-test='drawer']").text()).toBe("closed");
  });

  it("respects the initial planner view when opening directly into seating", () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
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
    expect(wrapper.text()).not.toContain("Gruppvy");
    expect(wrapper.text()).toContain("Sittplatser");
    expect(wrapper.text()).toContain(
      "Dra elever till platser och klicka på en elev när du vill öppna elevanteckningar.",
    );
  });
});
