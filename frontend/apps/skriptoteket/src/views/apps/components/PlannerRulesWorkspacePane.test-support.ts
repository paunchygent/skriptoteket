/** Shared planner-state fixture and reset for the rules workspace workflow specs. */

import { vi } from "vitest";

import type {
  FixedSeatRule,
  RelationshipRule,
  RoomTemplate,
  SeatingSmartTool,
  Student,
} from "../classroomPlannerTypes";

type PlannerStateMock = {
  roster: { id: string; name: string; students: Student[] } | null;
  template: RoomTemplate | null;
  students: Student[];
  studentsById: Record<string, Student | undefined>;
  seatsById: Record<string, { id: string; x: number; y: number; zone?: string | null } | undefined>;
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: RelationshipRule[];
  fixedSeatRules: FixedSeatRule[];
  pendingRelationshipStudentIds: string[];
  pendingFixedSeatStudentId: string | null;
  pendingFixedSeatSeatId: string | null;
  activeSeatingSmartTool: SeatingSmartTool | null;
  canEditSeatingSmartRules: boolean;
  editingFixedSeatRuleId: string | null;
  editingRelationshipRuleId: string | null;
  editingNearTeacherRule: boolean;
  canCommitPendingRelationshipRule: boolean;
  smartRuleFeedbackMessage: string | null;
  smartRuleHydrationStatus: "idle" | "hydrating" | "ready" | "error";
  smartRuleHydrationMessage: string | null;
  canCommitPendingFixedSeatRule: boolean;
  setActiveSeatingSmartTool: ReturnType<typeof vi.fn>;
  clearPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  clearPendingRuleCandidates: ReturnType<typeof vi.fn>;
  removePendingRuleCandidate: ReturnType<typeof vi.fn>;
  retrySmartRuleHydration: ReturnType<typeof vi.fn>;
  beginRelationshipRuleEdit: ReturnType<typeof vi.fn>;
  beginNearTeacherEdit: ReturnType<typeof vi.fn>;
  beginFixedSeatRuleEdit: ReturnType<typeof vi.fn>;
  clearNearTeacherRule: ReturnType<typeof vi.fn>;
  deleteRelationshipRule: ReturnType<typeof vi.fn>;
  deleteFixedSeatRule: ReturnType<typeof vi.fn>;
  commitPendingRelationshipRule: ReturnType<typeof vi.fn>;
  commitPendingFixedSeatRule: ReturnType<typeof vi.fn>;
  selectFixedSeatRuleSeat: ReturnType<typeof vi.fn>;
  fixedSeatRuleForStudent: ReturnType<typeof vi.fn>;
  fixedSeatRuleForSeat: ReturnType<typeof vi.fn>;
  replaceNearTeacherPreference: ReturnType<typeof vi.fn>;
  handleSeatingSmartToolStudentSelection: ReturnType<typeof vi.fn>;
  isStudentInPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  isStudentInPendingRuleCandidates: ReturnType<typeof vi.fn>;
};

export const stateMocks = {
  plannerState: ((): PlannerStateMock => ({
    roster: {
      id: "roster-1",
      name: "SR24D",
      students: [
        { id: "student-1", display_name: "Ada Lovelace" },
        { id: "student-2", display_name: "Alan Turing" },
        { id: "student-3", display_name: "Grace Hopper" },
      ],
    },
    template: {
      id: "template-1",
      name: "Sal 101",
      seats: [
        { id: "seat-1", x: 0, y: 0, zone: null },
        { id: "seat-2", x: 120, y: 0, zone: null },
      ],
      fixtures: [],
    },
    students: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
      { id: "student-3", display_name: "Grace Hopper" },
    ],
    studentsById: {
      "student-1": { id: "student-1", display_name: "Ada Lovelace" },
      "student-2": { id: "student-2", display_name: "Alan Turing" },
      "student-3": { id: "student-3", display_name: "Grace Hopper" },
    },
    seatsById: {
      "seat-1": { id: "seat-1", x: 0, y: 0, zone: null },
      "seat-2": { id: "seat-2", x: 120, y: 0, zone: null },
    },
    seatAssignments: [{ student_id: "student-1", seat_id: "seat-1" }],
    seatingPreferences: [
      { student_id: "student-1", near_teacher: true },
      { student_id: "student-2", near_teacher: true },
    ],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
    ],
    fixedSeatRules: [],
    pendingRelationshipStudentIds: ["student-2", "student-3"],
    pendingFixedSeatStudentId: null,
    pendingFixedSeatSeatId: null,
    activeSeatingSmartTool: "keep_apart",
    canEditSeatingSmartRules: true,
    editingFixedSeatRuleId: null,
    editingRelationshipRuleId: null,
    editingNearTeacherRule: false,
    canCommitPendingRelationshipRule: true,
    smartRuleFeedbackMessage: null,
    smartRuleHydrationStatus: "ready",
    smartRuleHydrationMessage: null,
    canCommitPendingFixedSeatRule: false,
    setActiveSeatingSmartTool: vi.fn(),
    clearPendingRelationshipSelection: vi.fn(),
    clearPendingRuleCandidates: vi.fn(),
    removePendingRuleCandidate: vi.fn(),
    retrySmartRuleHydration: vi.fn(),
    beginRelationshipRuleEdit: vi.fn(),
    beginNearTeacherEdit: vi.fn(),
    beginFixedSeatRuleEdit: vi.fn(),
    clearNearTeacherRule: vi.fn(() => true),
    deleteRelationshipRule: vi.fn(),
    deleteFixedSeatRule: vi.fn(),
    commitPendingRelationshipRule: vi.fn(() => true),
    commitPendingFixedSeatRule: vi.fn(() => true),
    selectFixedSeatRuleSeat: vi.fn(() => true),
    fixedSeatRuleForStudent: vi.fn(() => null),
    fixedSeatRuleForSeat: vi.fn(() => null),
    replaceNearTeacherPreference: vi.fn(),
    handleSeatingSmartToolStudentSelection: vi.fn(() => true),
    isStudentInPendingRelationshipSelection: vi.fn(() => false),
    isStudentInPendingRuleCandidates: vi.fn(() => false),
  }))(),
};

export function resetPlannerState(): void {
  stateMocks.plannerState.roster = {
    id: "roster-1",
    name: "SR24D",
    students: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
      { id: "student-3", display_name: "Grace Hopper" },
    ],
  };
  stateMocks.plannerState.template = {
    id: "template-1",
    name: "Sal 101",
    seats: [
      { id: "seat-1", x: 0, y: 0, zone: null },
      { id: "seat-2", x: 120, y: 0, zone: null },
    ],
    fixtures: [],
  };
  stateMocks.plannerState.seatsById = {
    "seat-1": { id: "seat-1", x: 0, y: 0, zone: null },
    "seat-2": { id: "seat-2", x: 120, y: 0, zone: null },
  };
  stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];
  stateMocks.plannerState.seatingPreferences = [
    { student_id: "student-1", near_teacher: true },
    { student_id: "student-2", near_teacher: true },
  ];
  stateMocks.plannerState.relationshipRules = [
    { id: "rule-1", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
  ];
  stateMocks.plannerState.fixedSeatRules = [];
  stateMocks.plannerState.pendingRelationshipStudentIds = ["student-2", "student-3"];
  stateMocks.plannerState.pendingFixedSeatStudentId = null;
  stateMocks.plannerState.pendingFixedSeatSeatId = null;
  stateMocks.plannerState.activeSeatingSmartTool = "keep_apart";
  stateMocks.plannerState.canEditSeatingSmartRules = true;
  stateMocks.plannerState.editingFixedSeatRuleId = null;
  stateMocks.plannerState.editingRelationshipRuleId = null;
  stateMocks.plannerState.editingNearTeacherRule = false;
  stateMocks.plannerState.canCommitPendingRelationshipRule = true;
  stateMocks.plannerState.smartRuleFeedbackMessage = null;
  stateMocks.plannerState.smartRuleHydrationStatus = "ready";
  stateMocks.plannerState.smartRuleHydrationMessage = null;
  stateMocks.plannerState.canCommitPendingFixedSeatRule = false;
  stateMocks.plannerState.setActiveSeatingSmartTool.mockReset();
  stateMocks.plannerState.clearPendingRelationshipSelection.mockReset();
  stateMocks.plannerState.clearPendingRuleCandidates.mockReset();
  stateMocks.plannerState.removePendingRuleCandidate.mockReset();
  stateMocks.plannerState.retrySmartRuleHydration.mockReset();
  stateMocks.plannerState.beginRelationshipRuleEdit.mockReset();
  stateMocks.plannerState.beginNearTeacherEdit.mockReset();
  stateMocks.plannerState.beginFixedSeatRuleEdit.mockReset();
  stateMocks.plannerState.clearNearTeacherRule.mockReset();
  stateMocks.plannerState.clearNearTeacherRule.mockReturnValue(true);
  stateMocks.plannerState.deleteRelationshipRule.mockReset();
  stateMocks.plannerState.deleteFixedSeatRule.mockReset();
  stateMocks.plannerState.commitPendingRelationshipRule.mockReset();
  stateMocks.plannerState.commitPendingRelationshipRule.mockReturnValue(true);
  stateMocks.plannerState.commitPendingFixedSeatRule.mockReset();
  stateMocks.plannerState.commitPendingFixedSeatRule.mockReturnValue(true);
  stateMocks.plannerState.selectFixedSeatRuleSeat.mockReset();
  stateMocks.plannerState.selectFixedSeatRuleSeat.mockReturnValue(true);
  stateMocks.plannerState.fixedSeatRuleForStudent.mockReset();
  stateMocks.plannerState.fixedSeatRuleForStudent.mockReturnValue(null);
  stateMocks.plannerState.fixedSeatRuleForSeat.mockReset();
  stateMocks.plannerState.fixedSeatRuleForSeat.mockReturnValue(null);
  stateMocks.plannerState.replaceNearTeacherPreference.mockReset();
  stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReset();
  stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReturnValue(true);
  stateMocks.plannerState.isStudentInPendingRelationshipSelection.mockReset();
  stateMocks.plannerState.isStudentInPendingRelationshipSelection.mockReturnValue(false);
  stateMocks.plannerState.isStudentInPendingRuleCandidates.mockReset();
  stateMocks.plannerState.isStudentInPendingRuleCandidates.mockReturnValue(false);
}
