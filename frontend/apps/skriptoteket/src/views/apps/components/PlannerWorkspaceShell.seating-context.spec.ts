/** Seating student selection, classroom prerequisites, initial context, feedback, and editing. */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Roster } from "../classroomPlannerTypes";

import {
  buildRosters,
  buildWorkspaceSummary,
  findWorkspaceModeToggle,
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

  it("treats seating student clicks as a true no-op", async () => {
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

    await wrapper.get("[data-test='seating-student-pool'] button").trigger("click");

    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).not.toHaveBeenCalled();
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
    expect(wrapper.get('[data-test="seating-template-select"]').attributes("aria-label")).toBe("Klassrum");
    expect(wrapper.text()).toContain(
      "Välj eller byt klassrum direkt här i sittschemat.",
    );

    await wrapper.get("select").setValue("template-2");

    expect(wrapper.emitted("change-seating-template")).toEqual([[{ templateId: "template-2" }]]);
  });

  it("disables Sittplatser in the live shell until a classroom context exists", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "grouping",
      revision: 3,
    };
    stateMocks.plannerState.template = null;

    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-2", name: "Sal 202", seats: [], fixtures: [] }],
        initialView: "groups",
        selectedWorkspaceTemplateId: null,
        workspaceSummary: {
          ...buildWorkspaceSummary(),
          active_seating_draft: null,
        },
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

    const groupingToggle = findWorkspaceModeToggle(wrapper, "Grupper");
    const seatingToggle = findWorkspaceModeToggle(wrapper, "Sittplatser");
    const rulesToggle = findWorkspaceModeToggle(wrapper, "Regler");

    expect(groupingToggle.attributes("disabled")).toBeUndefined();
    expect(seatingToggle.attributes("disabled")).toBeDefined();
    expect(seatingToggle.attributes("title")).toBe("Skapa eller välj först ett klassrum.");
    expect(rulesToggle.attributes("disabled")).toBeUndefined();

    await groupingToggle.trigger("click");
    await seatingToggle.trigger("click");
    await rulesToggle.trigger("click");

    expect(wrapper.emitted("select-workspace-mode")).toEqual([["rules"]]);
  });

  it("keeps Sittplatser available in the live shell when overview already has a selected classroom", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "grouping",
      revision: 3,
    };
    stateMocks.plannerState.template = null;

    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-2", name: "Sal 202", seats: [], fixtures: [] }],
        initialView: "groups",
        selectedWorkspaceTemplateId: "template-2",
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

    const seatingToggle = findWorkspaceModeToggle(wrapper, "Sittplatser");
    expect(seatingToggle.attributes("disabled")).toBeUndefined();

    await seatingToggle.trigger("click");
    expect(wrapper.emitted("select-workspace-mode")).toEqual([["seating"]]);
  });

  it("uses the selected class and classroom while seating setup has no loaded draft state", async () => {
    stateMocks.plannerState.roster = null as unknown as Roster;
    stateMocks.plannerState.template = null;
    stateMocks.plannerState.draft = {
      id: "draft-setup",
      draft_kind: "seating",
      revision: 1,
    };

    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableRosters: buildRosters(),
        availableTemplates: [{ id: "template-2", name: "Sal 202", seats: [], fixtures: [] }],
        initialView: "seats",
        selectedRosterId: "roster-1",
        selectedWorkspaceTemplateId: "template-2",
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

    expect(wrapper.text()).toContain("SA24D");
    expect(wrapper.text()).toContain("Sal 202");

    const seatingToggle = findWorkspaceModeToggle(wrapper, "Sittplatser");
    expect(seatingToggle.attributes("disabled")).toBeUndefined();

    await wrapper.get("[data-test='planner-phone-mode-sheet-trigger']").trigger("click");

    const phoneSeating = document.body.querySelector<HTMLButtonElement>(
      "[data-test='planner-phone-mode-sheet-seating']",
    );
    expect(phoneSeating?.disabled).toBe(false);
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

  it("keeps stale smart-run feedback out of the seating pane after the shell cut-over", () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    stateMocks.plannerState.smartSeatingRunMessage =
      "För att använda historik behöver du först exportera ett sittschema för just det här klassrummet.";
    stateMocks.plannerState.smartSeatingRunTone = "warning";

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

    expect(wrapper.find('[data-test="seating-smart-run-message"]').exists()).toBe(false);
  });

  it("lets the seating toolbar edit both the current class and classroom without exposing grouping actions", async () => {
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
    await wrapper.get('[data-test="edit-seating-roster"]').trigger("click");
    expect(wrapper.emitted("edit-roster")).toEqual([[]]);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="edit-current-template"]').trigger("click");

    expect(wrapper.emitted("edit-current-template")).toEqual([[stateMocks.plannerState.template]]);
  });
});
