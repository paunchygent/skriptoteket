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

const toastMocks = vi.hoisted(() => ({
  info: vi.fn(),
  success: vi.fn(),
  warning: vi.fn(),
}));

type PlannerStateMock = {
  roster: Roster;
  template: RoomTemplate | null;
  draft: Pick<PlanDraft, "id" | "draft_kind" | "revision"> & {
    smart_enabled?: boolean;
    use_history?: boolean;
    grouping_seating_distance_enabled?: boolean;
  };
  students: Roster["students"];
  ungroupedStudents: Roster["students"];
  unseatedStudents: Roster["students"];
  groups: Array<{ id: string; name: string; sort_order: number; name_is_custom: boolean }>;
  studentsByGroupId: Record<string, Roster["students"]>;
  groupAssignments: Array<{ student_id: string; group_id: string }>;
  seats: RoomTemplate["seats"];
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: Array<{ id: string; kind: "keep_near" | "keep_apart"; student_ids: string[] }>;
  pendingRelationshipStudentIds: string[];
  smartRuleFeedbackMessage: string | null;
  smartGroupingRunMessage: string | null;
  smartGroupingRunTone: "neutral" | "success" | "warning";
  smartSeatingRunMessage: string | null;
  smartSeatingRunTone: "neutral" | "success" | "warning";
  canCommitPendingRelationshipRule: boolean;
  plannerStatusLabel: string;
  plannerStatusMessage: string | null;
  plannerStatusTone: "neutral" | "success" | "warning" | "danger";
  plannerConflictMessage: string | null;
  isWorkspaceBusy: boolean;
  isRunningSmartGrouping: boolean;
  isRunningSmartSeating: boolean;
  canEditSeatingSmartRules: boolean;
  canUndo: boolean;
  canRedo: boolean;
  activeSeatingSmartTool: "near_teacher" | "keep_near" | "keep_apart" | null;
  setActiveSeatingSmartTool: ReturnType<typeof vi.fn>;
  clearPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  handleSeatingSmartToolStudentSelection: ReturnType<typeof vi.fn>;
  commitPendingRelationshipRule: ReturnType<typeof vi.fn>;
  deleteRelationshipRule: ReturnType<typeof vi.fn>;
  setDraftSmartEnabled: ReturnType<typeof vi.fn>;
  setDraftUseHistoryEnabled: ReturnType<typeof vi.fn>;
  setDraftGroupingSeatingDistanceEnabled: ReturnType<typeof vi.fn>;
  reloadActiveWorkspace: ReturnType<typeof vi.fn>;
  undoGroupingDraft: ReturnType<typeof vi.fn>;
  redoGroupingDraft: ReturnType<typeof vi.fn>;
  runGroupingShuffle: ReturnType<typeof vi.fn>;
  clearGroupingAssignments: ReturnType<typeof vi.fn>;
  addGroup: ReturnType<typeof vi.fn>;
  assignStudentToGroup: ReturnType<typeof vi.fn>;
  removeStudentFromGroup: ReturnType<typeof vi.fn>;
  renameGroup: ReturnType<typeof vi.fn>;
  moveGroup: ReturnType<typeof vi.fn>;
  removeGroup: ReturnType<typeof vi.fn>;
  undoSeatingDraft: ReturnType<typeof vi.fn>;
  redoSeatingDraft: ReturnType<typeof vi.fn>;
  randomizeSeating: ReturnType<typeof vi.fn>;
  runSeatingShuffle: ReturnType<typeof vi.fn>;
  clearSeatingAssignments: ReturnType<typeof vi.fn>;
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
    ungroupedStudents: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ],
    unseatedStudents: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ],
    groups: [{ id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false }],
    studentsByGroupId: { "group-a": [] },
    groupAssignments: [],
    seats: [
      { id: "seat-1", x: 0, y: 0, zone: null },
      { id: "seat-2", x: 120, y: 0, zone: null },
    ],
    seatAssignments: [{ student_id: "student-1", seat_id: "seat-1" }],
    seatingPreferences: [],
    relationshipRules: [],
    pendingRelationshipStudentIds: [],
    smartRuleFeedbackMessage: null,
    smartGroupingRunMessage: null,
    smartGroupingRunTone: "neutral",
    smartSeatingRunMessage: null,
    smartSeatingRunTone: "neutral",
    canCommitPendingRelationshipRule: false,
    plannerStatusLabel: "Sparad",
    plannerStatusMessage: null,
    plannerStatusTone: "success",
    plannerConflictMessage: null,
    isWorkspaceBusy: false,
    isRunningSmartGrouping: false,
    isRunningSmartSeating: false,
    canEditSeatingSmartRules: true,
    canUndo: false,
    canRedo: false,
    activeSeatingSmartTool: null,
    setActiveSeatingSmartTool: vi.fn(),
    clearPendingRelationshipSelection: vi.fn(),
    handleSeatingSmartToolStudentSelection: vi.fn(() => false),
    commitPendingRelationshipRule: vi.fn(() => true),
    deleteRelationshipRule: vi.fn(),
    setDraftSmartEnabled: vi.fn(),
    setDraftUseHistoryEnabled: vi.fn(),
    setDraftGroupingSeatingDistanceEnabled: vi.fn(),
    reloadActiveWorkspace: vi.fn(),
    undoGroupingDraft: vi.fn(),
    redoGroupingDraft: vi.fn(),
    runGroupingShuffle: vi.fn(),
    clearGroupingAssignments: vi.fn(),
    addGroup: vi.fn(),
    assignStudentToGroup: vi.fn(),
    removeStudentFromGroup: vi.fn(),
    renameGroup: vi.fn(),
    moveGroup: vi.fn(),
    removeGroup: vi.fn(),
    undoSeatingDraft: vi.fn(),
    redoSeatingDraft: vi.fn(),
    randomizeSeating: vi.fn(),
    runSeatingShuffle: vi.fn(),
    clearSeatingAssignments: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

vi.mock("../../../composables/useToast", () => ({
  useToast: () => toastMocks,
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

function buildRosters(): Roster[] {
  return [
    { id: "roster-1", name: "SA24D", students: [] },
    { id: "roster-2", name: "SA24E", students: [] },
  ];
}

function findWorkspaceModeToggle(
  wrapper: ReturnType<typeof mount>,
  label: "Översikt" | "Grupper" | "Sittplatser" | "Regler",
) {
  const button = wrapper.findAll('[data-ui="segmented-toggle"] button').find(
    (candidate) => candidate.text() === label,
  );
  if (!button) {
    throw new Error(`Expected the planner top panel to expose ${label}.`);
  }
  return button;
}

describe("PlannerWorkspaceShell", () => {
  beforeEach(() => {
    toastMocks.info.mockReset();
    toastMocks.success.mockReset();
    toastMocks.warning.mockReset();
    stateMocks.plannerState.reloadActiveWorkspace.mockReset();
    stateMocks.plannerState.undoGroupingDraft.mockReset();
    stateMocks.plannerState.redoGroupingDraft.mockReset();
    stateMocks.plannerState.runGroupingShuffle.mockReset();
    stateMocks.plannerState.clearGroupingAssignments.mockReset();
    stateMocks.plannerState.addGroup.mockReset();
    stateMocks.plannerState.assignStudentToGroup.mockReset();
    stateMocks.plannerState.removeStudentFromGroup.mockReset();
    stateMocks.plannerState.renameGroup.mockReset();
    stateMocks.plannerState.moveGroup.mockReset();
    stateMocks.plannerState.removeGroup.mockReset();
    stateMocks.plannerState.undoSeatingDraft.mockReset();
    stateMocks.plannerState.redoSeatingDraft.mockReset();
    stateMocks.plannerState.randomizeSeating.mockReset();
    stateMocks.plannerState.runSeatingShuffle.mockReset();
    stateMocks.plannerState.clearSeatingAssignments.mockReset();
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
    stateMocks.plannerState.ungroupedStudents = [...stateMocks.plannerState.students];
    stateMocks.plannerState.unseatedStudents = [...stateMocks.plannerState.students];
    stateMocks.plannerState.groups = [{ id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false }];
    stateMocks.plannerState.studentsByGroupId = { "group-a": [] };
    stateMocks.plannerState.groupAssignments = [];
    stateMocks.plannerState.seats = [
      { id: "seat-1", x: 0, y: 0, zone: null },
      { id: "seat-2", x: 120, y: 0, zone: null },
    ];
    stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];
    stateMocks.plannerState.seatingPreferences = [];
    stateMocks.plannerState.relationshipRules = [];
    stateMocks.plannerState.pendingRelationshipStudentIds = [];
    stateMocks.plannerState.smartRuleFeedbackMessage = null;
    stateMocks.plannerState.smartGroupingRunMessage = null;
    stateMocks.plannerState.smartGroupingRunTone = "neutral";
    stateMocks.plannerState.smartSeatingRunMessage = null;
    stateMocks.plannerState.smartSeatingRunTone = "neutral";
    stateMocks.plannerState.canCommitPendingRelationshipRule = false;
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.isRunningSmartGrouping = false;
    stateMocks.plannerState.canEditSeatingSmartRules = true;
    stateMocks.plannerState.canUndo = false;
    stateMocks.plannerState.canRedo = false;
    stateMocks.plannerState.activeSeatingSmartTool = null;
    stateMocks.plannerState.setActiveSeatingSmartTool.mockReset();
    stateMocks.plannerState.clearPendingRelationshipSelection.mockReset();
    stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReset();
    stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReturnValue(false);
    stateMocks.plannerState.commitPendingRelationshipRule.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReturnValue(true);
    stateMocks.plannerState.deleteRelationshipRule.mockReset();
    stateMocks.plannerState.setDraftSmartEnabled.mockReset();
    stateMocks.plannerState.setDraftUseHistoryEnabled.mockReset();
    stateMocks.plannerState.setDraftGroupingSeatingDistanceEnabled.mockReset();
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

  it("pulls grouping and seating toolbars up against the authenticated topbar once they become sticky", () => {
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
      expect.arrayContaining(["sticky", "top-0", "z-20", "md:-top-4"]),
    );
    expect(
      groupingWrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="groups"]').classes(),
    ).not.toContain(
      "top-3",
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
      expect.arrayContaining(["sticky", "top-0", "z-20", "md:-top-4"]),
    );
    expect(
      seatingWrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="seats"]').classes(),
    ).not.toContain(
      "top-3",
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
      expect.arrayContaining(["xl:min-h-0", "xl:max-h-full", "xl:overflow-y-auto"]),
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
      expect.arrayContaining(["xl:min-h-0", "xl:max-h-full", "xl:overflow-y-auto"]),
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
          GroupBoard: { template: "<div data-test='group-board' />" },
          RoomCanvas: { template: "<div data-test='room-canvas' />" },
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

    const groupingPoolStudent = wrapper.get("[data-test='grouping-student-pool'] button");

    expect(groupingPoolStudent.classes()).toContain("planner-choice-button-strong");
    expect(groupingPoolStudent.classes()).not.toContain("planner-choice-button-active");

    await groupingPoolStudent.trigger("click");

    expect(groupingPoolStudent.classes()).toContain("planner-choice-button-strong");
    expect(groupingPoolStudent.classes()).not.toContain("planner-choice-button-active");
    expect(wrapper.get("[data-test='drawer']").text()).toBe("closed");
  });

  it("opens the notes drawer when a seating student is selected", async () => {
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

    expect(wrapper.get("[data-test='drawer']").text()).toBe("closed");

    await wrapper.get("[data-test='seating-student-pool'] button").trigger("click");

    expect(wrapper.get("[data-test='drawer']").text()).toBe("open");
  });

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
    expect(wrapper.get("[data-test='drawer']").text()).toBe("closed");
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
    expect(wrapper.get("[data-test='drawer']").text()).toBe("closed");
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
    expect(wrapper.get('[data-test="grouping-open-settings"]').attributes("aria-label")).toBe(
      "Smart-inställningar",
    );

    await wrapper.get('[data-test="grouping-open-settings"]').trigger("click");

    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain("Smart-inställningar");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain("Historik");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain("Klassrum");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain("Sittschemat");
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Minskar risken att samma elever hamnar i samma grupp igen.",
    );
    expect(wrapper.get('[data-test="grouping-settings-drawer"]').text()).toContain(
      "Du lägger till och ändrar regler i arbetsytan Regler.",
    );

    await wrapper.get('[data-test="grouping-settings-template-select"]').setValue("template-2");

    expect(wrapper.emitted("change-grouping-template")).toEqual([[{ templateId: "template-2" }]]);
    expect((wrapper.get('[data-test="grouping-settings-template-select"]').element as HTMLSelectElement).value).toBe("template-2");

    await wrapper.get('[data-test="grouping-settings-open-rules"]').trigger("click");
    expect(wrapper.emitted("open-rules")).toEqual([[]]);
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
    expect(wrapper.get('[data-test="seating-open-settings"]').attributes("aria-label")).toBe(
      "Smart-inställningar",
    );

    await wrapper.get('[data-test="seating-open-settings"]').trigger("click");

    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain("Smart-inställningar");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain("Historik");
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Om du tidigare har exporterat ett sittschema kan Smart använda det för att variera placeringen över tid.",
    );
    expect(wrapper.get('[data-test="seating-settings-drawer"]').text()).toContain(
      "Du lägger till och ändrar regler i arbetsytan Regler.",
    );

    await wrapper.get('[data-test="seating-settings-history-toggle"]').trigger("click");
    expect(stateMocks.plannerState.setDraftUseHistoryEnabled).toHaveBeenCalledWith(false);

    await wrapper.get('[data-test="seating-settings-open-rules"]').trigger("click");
    expect(wrapper.emitted("open-rules")).toEqual([[]]);
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
    expect(wrapper.emitted("exit-app")).toHaveLength(1);
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

    await wrapper.get('[data-test="grouping-export-default"]').trigger("click");
    expect(wrapper.emitted("export-grouping-default")).toEqual([[]]);

    await wrapper.get('[data-test="grouping-export-menu-trigger"]').trigger("click");
    await wrapper.get('[data-test="grouping-export-option-pdf"]').trigger("click");

    expect(wrapper.emitted("export-grouping-option")).toEqual([["pdf_a4_portrait"]]);
    expect(wrapper.text()).not.toContain("Affisch (A3)");
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
