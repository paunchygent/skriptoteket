/**
 * Seating workspace pane smart-rule boundary tests.
 *
 * These tests keep the seating pane focused on the live work surface after
 * ST-29-02 moved smart-rule controls and transient feedback into the detached
 * shell toolbar and toast layer.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerSeatingWorkspacePane from "./PlannerSeatingWorkspacePane.vue";
import type {
  FixedSeatRule,
  PlanDraft,
  RelationshipRule,
  RoomFixture,
  RoomTemplate,
  Roster,
  Seat,
  SeatAssignment,
  Student,
} from "../classroomPlannerTypes";

type PlannerStateMock = {
  template: RoomTemplate | null;
  seats: Seat[];
  fixtures: RoomFixture[];
  draft: (
    Pick<PlanDraft, "id" | "draft_kind" | "revision">
    & { smart_enabled?: boolean; use_history?: boolean }
  ) | null;
  studentsById: Record<string, Roster["students"][number]>;
  seatAssignments: SeatAssignment[];
  studentBySeatId: Record<string, Student | null>;
  unseatedStudents: Roster["students"];
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: RelationshipRule[];
  fixedSeatRules: FixedSeatRule[];
  smartRuleHydrationStatus: "idle" | "hydrating" | "ready" | "error";
  smartRuleHydrationMessage: string | null;
  smartSeatingRunMessage: string | null;
  smartSeatingRunTone: "neutral" | "success" | "warning";
  assignStudentToSeat: ReturnType<typeof vi.fn>;
  clearSeatAssignment: ReturnType<typeof vi.fn>;
  swapSeatAssignments: ReturnType<typeof vi.fn>;
  retrySmartRuleHydration: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    template: {
      id: "template-1",
      name: "Sal 101",
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [],
    },
    seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
    fixtures: [],
    draft: { id: "draft-1", draft_kind: "seating", revision: 2, smart_enabled: true },
    studentsById: {
      "student-1": { id: "student-1", display_name: "Ada Lovelace" },
      "student-2": { id: "student-2", display_name: "Alan Turing" },
    },
    seatAssignments: [],
    studentBySeatId: { "seat-1": null },
    unseatedStudents: [{ id: "student-2", display_name: "Alan Turing" }],
    seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ],
    fixedSeatRules: [],
    smartRuleHydrationStatus: "ready",
    smartRuleHydrationMessage: null,
    smartSeatingRunMessage: null,
    smartSeatingRunTone: "neutral",
    assignStudentToSeat: vi.fn(),
    clearSeatAssignment: vi.fn(),
    swapSeatAssignments: vi.fn(),
    retrySmartRuleHydration: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerSeatingWorkspacePane smart-rule boundary", () => {
  beforeEach(() => {
    stateMocks.plannerState.seatingPreferences = [{ student_id: "student-1", near_teacher: true }];
    stateMocks.plannerState.relationshipRules = [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ];
    stateMocks.plannerState.fixedSeatRules = [];
    stateMocks.plannerState.seatAssignments = [];
    stateMocks.plannerState.studentBySeatId = { "seat-1": null };
    stateMocks.plannerState.seats = [{ id: "seat-1", x: 0, y: 0, zone: null }];
    stateMocks.plannerState.fixtures = [];
    stateMocks.plannerState.smartRuleHydrationStatus = "ready";
    stateMocks.plannerState.smartRuleHydrationMessage = null;
    stateMocks.plannerState.smartSeatingRunMessage = null;
    stateMocks.plannerState.smartSeatingRunTone = "neutral";
    stateMocks.plannerState.assignStudentToSeat.mockReset();
    stateMocks.plannerState.clearSeatAssignment.mockReset();
    stateMocks.plannerState.swapSeatAssignments.mockReset();
    stateMocks.plannerState.retrySmartRuleHydration.mockReset();
  });

  it("keeps smart-rule controls and transient feedback out of the seating pane", () => {
    stateMocks.plannerState.smartSeatingRunMessage =
      "För att använda historik behöver du först exportera ett sittschema för just det här klassrummet.";

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.find('[data-test="seating-open-rules"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-use-history-toggle"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-smart-run-message"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("aktiva regler");
  });

  it("shows smart-rule hydration errors without reintroducing inline editing", () => {
    stateMocks.plannerState.smartRuleHydrationStatus = "error";
    stateMocks.plannerState.smartRuleHydrationMessage = "Kunde inte ladda smarta regler.";

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.get('[data-test="seating-smart-hydration-error"]').text()).toContain(
      "Kunde inte ladda smarta regler.",
    );
    expect(wrapper.find('[data-test="seating-smart-commit-rule"]').exists()).toBe(false);
  });

  it("does not render false-valued near-teacher preferences as active markers", () => {
    stateMocks.plannerState.seatingPreferences = [{ student_id: "student-1", near_teacher: false }];
    stateMocks.plannerState.relationshipRules = [];

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.text()).not.toContain("Ada Lovelace");
    expect(wrapper.find('[data-test="student-pool-markers-student-2"]').exists()).toBe(false);
  });

  it("passes active fixed-seat rules into the seating canvas and marker pipeline", () => {
    stateMocks.plannerState.fixedSeatRules = [
      { id: "fixed-active", template_id: "template-1", student_id: "student-2", seat_id: "seat-1" },
      { id: "fixed-other-template", template_id: "template-2", student_id: "student-1", seat_id: "seat-9" },
    ];

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: {
            props: ["fixedSeatRules", "smartRuleMarkersByStudentId"],
            template: `
              <div data-test="room-canvas-stub">
                <span data-test="room-canvas-fixed-rules">
                  {{ fixedSeatRules.length === 1 ? fixedSeatRules[0].id : fixedSeatRules.length }}
                </span>
                <span data-test="room-canvas-fixed-marker">
                  {{ (smartRuleMarkersByStudentId["student-2"] ?? []).join(",") }}
                </span>
              </div>
            `,
          },
        },
      },
    });

    expect(wrapper.get('[data-test="room-canvas-fixed-rules"]').text()).toBe("fixed-active");
    expect(wrapper.get('[data-test="room-canvas-fixed-marker"]').text()).toContain("Fast plats");
    expect(wrapper.text()).not.toContain("fixed-other-template");
  });

  it("keeps the unseated pool and canvas lane in a bounded desktop split workspace", () => {
    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });
    const layoutRow = wrapper.get('[data-test="seating-layout-lane"]');
    const pool = wrapper.get('[data-test="seating-student-pool"]');
    const poolLane = wrapper.get('[data-test="seating-student-pool-lane"]');
    const workspaceLane = wrapper.get('[data-test="seating-workspace-lane"]');
    const scrollBody = wrapper.get('[data-test="seating-student-pool-scroll-body"]');

    expect(layoutRow.classes()).toEqual(
      expect.arrayContaining([
        "planner-workspace-split-row",
        "planner-seating-layout-row",
      ]),
    );
    expect(pool.classes()).toEqual(
      expect.arrayContaining([
        "planner-student-pool-surface",
      ]),
    );
    expect(poolLane.classes()).toEqual(
      expect.arrayContaining([
        "planner-workspace-pool-lane",
        "planner-seating-pool-lane",
      ]),
    );
    expect(workspaceLane.classes()).toEqual(
      expect.arrayContaining([
        "planner-seating-workspace-lane",
      ]),
    );
    expect(scrollBody.classes()).toEqual(
      expect.arrayContaining([
        "min-h-0",
        "flex-1",
        "overflow-y-auto",
      ]),
    );
  });

  it("keeps the phone seating workspace on the shared simplified classroom map", async () => {
    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    const phoneWorkspace = wrapper.get('[data-test="phone-seating-workspace"]');
    const toggle = wrapper.get('[data-test="phone-seating-show-students"]');
    const canvas = wrapper.get('[data-test="phone-seating-workspace-canvas"]');

    expect(phoneWorkspace.text()).toContain("Elever");
    expect(toggle.text()).toContain("1 ej placerad");
    expect(toggle.classes()).toContain("planner-phone-seating-student-toggle");
    expect(toggle.html()).toContain("lucide-users-round");
    expect(toggle.html()).not.toContain("lucide-school");
    expect(phoneWorkspace.find('[data-test="room-canvas-stub"]').exists()).toBe(false);
    expect(canvas.find('[data-test="phone-fixed-seat-map-seat-seat-1"]').exists()).toBe(true);
    expect(toggle.element.compareDocumentPosition(canvas.element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(wrapper.find('[data-test="phone-seating-student-sheet"]').exists()).toBe(false);

    await toggle.trigger("click");

    expect(wrapper.get('[data-test="phone-seating-student-sheet"]').text()).toContain("Alan Turing");
    expect(wrapper.get('[data-test="phone-seating-student-sheet"]').classes()).toContain(
      "planner-phone-seating-student-tray",
    );
  });

  it("uses tap-to-remove instead of a cramped remove button on the phone seating map", async () => {
    stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];
    stateMocks.plannerState.studentBySeatId = {
      "seat-1": { id: "student-1", display_name: "Ada Lovelace" },
    };

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
    });

    expect(wrapper.find('[data-test="phone-seat-remove-seat-1"]').exists()).toBe(false);

    await wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]').trigger("click");

    expect(stateMocks.plannerState.clearSeatAssignment).toHaveBeenCalledWith("student-1");
  });
});
