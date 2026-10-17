/** Smart-rule candidate routing and grouping/seating advanced-settings drawer workflows. */

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

  it("routes Regler clicks through the active smart tool instead of opening the drawer", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    stateMocks.plannerState.activeSeatingSmartTool = "near_teacher";
    stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReturnValue(true);

    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "rules",
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerRulesWorkspacePane: {
            template: "<button data-test='rules-student' @click=\"$emit('student-selected', 'student-1')\" />",
          },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get("[data-test='rules-student']").trigger("click");

    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).toHaveBeenCalledWith(
      "student-1",
    );
  });

  it("removes already-selected Regler candidates without replaying the select toggle", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    stateMocks.plannerState.activeSeatingSmartTool = "keep_near";
    stateMocks.plannerState.pendingRelationshipStudentIds = ["student-1", "student-2"];
    stateMocks.plannerState.isStudentInPendingRuleCandidates.mockImplementation(
      (studentId: string) => studentId === "student-1",
    );

    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "rules",
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerRulesWorkspacePane: {
            template: "<button data-test='rules-student' @click=\"$emit('student-selected', 'student-1')\" />",
          },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get("[data-test='rules-student']").trigger("click");

    expect(stateMocks.plannerState.removePendingRuleCandidate).toHaveBeenCalledWith("student-1");
    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).not.toHaveBeenCalled();
  });

  it("ignores Regler student clicks when no smart tool is active", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
    };
    stateMocks.plannerState.activeSeatingSmartTool = null;

    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableTemplates: [{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }],
        initialView: "rules",
        workspaceSummary: buildWorkspaceSummary(),
      },
      global: {
        stubs: {
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
          PlannerRulesWorkspacePane: {
            props: ["selectedStudentId"],
            template: `
              <div>
                <span data-test="rules-selected-id">{{ selectedStudentId ?? 'none' }}</span>
                <button
                  data-test="rules-student"
                  @click="$emit('student-selected', 'student-1')"
                />
              </div>
            `,
          },
          PlannerMetadataDrawer: {
            props: ["open"],
            template: "<div data-test='drawer'>{{ open ? 'open' : 'closed' }}</div>",
          },
        },
      },
    });

    await wrapper.get("[data-test='rules-student']").trigger("click");

    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).not.toHaveBeenCalled();
    expect(wrapper.get("[data-test='rules-selected-id']").text()).toBe("none");
  });

  it("keeps the grouping toolbar focused on actions and moves Smart tuning into the drawer", async () => {
    stateMocks.plannerState.template = null;
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "grouping",
      revision: 3,
      grouping_seating_distance_enabled: false,
      use_history: false,
    };
    const wrapper = mount(PlannerWorkspaceShell, {
      props: {
        availableRosters: buildRosters(),
        availableTemplates: [{ id: "template-2", name: "Sal 202", seats: [], fixtures: [] }],
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

    expect(wrapper.find("[data-test='group-board']").exists()).toBe(true);
    expect(wrapper.get('[data-test="grouping-roster-select"]').attributes("aria-label")).toBe("Klass");
    expect(wrapper.get('[data-test="grouping-roster-select"]').element).toBeInstanceOf(HTMLSelectElement);
    expect(wrapper.find('[data-test="grouping-template-select"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-use-history-toggle"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-active-rule-count"]').exists()).toBe(false);
    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.get('[data-test="grouping-overflow-open-settings"]').text()).toContain(
      "Avancerade inställningar",
    );
    expect(wrapper.get('[data-test="grouping-overflow-open-settings"]').attributes("aria-haspopup")).toBe("dialog");

    await wrapper.get('[data-test="grouping-overflow-open-settings"]').trigger("click");

    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain("Avancerade inställningar");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).not.toContain("Smart-inställningar");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain("Smart placering");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Tar hänsyn till dina regler när du skapar en ny placering, till exempel fasta platser eller elever som inte bör sitta nära varandra.",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain("Historik");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain("Klassrum");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Tillämpa sittschema",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Försöker undvika att elever får samma plats eller samma bordsgrannar som tidigare. Stäng av om du vill börja utan historik.",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Välj först ett klassrum så Smart vet vilket sittschema som kan användas.",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Lägg till och ändra regler för placeringar.",
    );

    await wrapper.get('[data-test="grouping-settings-history-toggle"]').trigger("click");
    expect(stateMocks.plannerState.setDraftUseHistoryEnabled).toHaveBeenCalledWith(true);
    stateMocks.plannerState.draft = {
      ...stateMocks.plannerState.draft,
      use_history: true,
    };
    await nextTick();
    expect(wrapper.find('[data-test="grouping-settings-drawer"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-settings-template-select"]').setValue("template-2");

    expect(wrapper.emitted("change-grouping-template")).toEqual([[{ templateId: "template-2" }]]);
    expect((wrapper.get('[data-test="grouping-settings-template-select"]').element as HTMLSelectElement).value).toBe("template-2");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Försöker lägga elever som redan sitter nära varandra i samma grupp. Det kan göra gruppstarten lugnare när eleverna ska arbeta från sina platser.",
    );

    await wrapper.get('[data-test="grouping-settings-seating-toggle"]').trigger("click");
    expect(stateMocks.plannerState.setDraftGroupingSeatingDistanceEnabled)
      .toHaveBeenCalledWith(true);
    stateMocks.plannerState.draft = {
      ...stateMocks.plannerState.draft,
      grouping_seating_distance_enabled: true,
    };
    await nextTick();
    expect(wrapper.find('[data-test="grouping-settings-drawer"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-settings-open-rules"]').trigger("click");
    expect(wrapper.emitted("open-rules")).toEqual([[]]);
    expect(wrapper.find('[data-test="grouping-settings-drawer"]').exists()).toBe(false);
  });

  it("keeps the seating toolbar focused on actions and moves Smart tuning into the drawer", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-2",
      draft_kind: "seating",
      revision: 5,
      smart_enabled: true,
      use_history: true,
    };
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

    expect(wrapper.get('[data-test="seating-template-select"]').attributes("aria-label")).toBe("Klassrum");
    expect(wrapper.find('[data-test="seating-use-history-toggle"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-open-rules"]').exists()).toBe(false);
    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.get('[data-test="seating-overflow-open-settings"]').text()).toContain(
      "Avancerade inställningar",
    );
    expect(wrapper.get('[data-test="seating-overflow-open-settings"]').attributes("aria-haspopup")).toBe("dialog");

    await wrapper.get('[data-test="seating-overflow-open-settings"]').trigger("click");

    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain("Avancerade inställningar");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).not.toContain("Smart-inställningar");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain("Smart placering");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Tar hänsyn till dina regler när du skapar en ny placering, till exempel fasta platser eller elever som inte bör sitta nära varandra.",
    );
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain("Historik");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Försöker undvika att elever får samma plats eller samma bordsgrannar som tidigare. Stäng av om du vill börja utan historik.",
    );
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Lägg till och ändra regler för placeringar.",
    );

    await wrapper.get('[data-test="seating-settings-history-toggle"]').trigger("click");
    expect(stateMocks.plannerState.setDraftUseHistoryEnabled).toHaveBeenCalledWith(false);
    stateMocks.plannerState.draft = {
      ...stateMocks.plannerState.draft,
      use_history: false,
    };
    await nextTick();
    expect(wrapper.find('[data-test="seating-settings-drawer"]').exists()).toBe(true);

    await wrapper.get('[data-test="seating-settings-open-rules"]').trigger("click");
    expect(wrapper.emitted("open-rules")).toEqual([[]]);
    expect(wrapper.find('[data-test="seating-settings-drawer"]').exists()).toBe(false);
  });
});
