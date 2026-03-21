import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerWorkspaceShell from "./PlannerWorkspaceShell.vue";

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    roster: { id: "roster-1", name: "SA24D", students: [] },
    template: { id: "template-1", name: "Sal 101", seats: [], fixtures: [] },
    draft: { id: "draft-1", revision: 3 },
    saveStatus: "saved",
    saveMessage: null,
    reloadActiveWorkspace: vi.fn(),
  },
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerWorkspaceShell", () => {
  beforeEach(() => {
    stateMocks.plannerState.reloadActiveWorkspace.mockReset();
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

  it("opens student notes from seating without exposing them from grouping", async () => {
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

    await wrapper.get("[data-test='group-student']").trigger("click");
    expect(wrapper.get("[data-test='drawer']").text()).toBe("closed");

    await wrapper.get("button:nth-of-type(2)").trigger("click");
    await wrapper.get("[data-test='seat-student']").trigger("click");
    expect(wrapper.get("[data-test='drawer']").text()).toBe("open");
  });
});
