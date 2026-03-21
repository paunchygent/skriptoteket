import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { defaultPlanningProfile } from "./classroomPlannerTypes";
import { useClassroomState } from "./useClassroomState";

function seedWorkspace() {
  const state = useClassroomState();
  state.roster = {
    id: "roster-1",
    name: "Klass 9A",
    students: [
      { id: "s1", display_name: "Student 1" },
      { id: "s2", display_name: "Student 2" },
      { id: "s3", display_name: "Student 3" },
    ],
  };
  state.template = {
    id: "template-1",
    name: "Sal 101",
    seats: [
      { id: "seat-1", x: 0, y: 0, zone: "front" },
      { id: "seat-2", x: 120, y: 0, zone: "front" },
    ],
    fixtures: [],
  };
  state.groups = [
    { id: "group-a", name: "Grupp A", sort_order: 0 },
    { id: "group-b", name: "Grupp B", sort_order: 1 },
  ];
  state.planningProfile = defaultPlanningProfile();
  state.groupAssignmentsByStudentId = {};
  state.seatAssignmentsByStudentId = {};
  state.studentPlanningMetaByStudentId = {};
  state.pairConstraints = [];
  return state;
}

describe("useClassroomState", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("assigns and removes students from groups", () => {
    const state = seedWorkspace();

    state.assignStudentToGroup("s1", "group-a");

    expect(state.groupAssignmentsByStudentId["s1"]).toBe("group-a");
    expect(state.studentsByGroupId["group-a"]).toHaveLength(1);

    state.removeStudentFromGroup("s1");

    expect(state.groupAssignmentsByStudentId["s1"]).toBeNull();
    expect(state.ungroupedStudents).toHaveLength(3);
  });

  it("reassigns occupied seats to the latest student", () => {
    const state = seedWorkspace();

    state.assignStudentToSeat("s1", "seat-1");
    state.assignStudentToSeat("s2", "seat-1");

    expect(state.seatAssignmentsByStudentId["s1"]).toBeNull();
    expect(state.seatAssignmentsByStudentId["s2"]).toBe("seat-1");
  });

  it("supports group lifecycle operations", () => {
    const state = seedWorkspace();

    state.addGroup("Grupp C");
    const createdGroup = state.groups.find((group) => group.name === "Grupp C");

    expect(createdGroup).toBeTruthy();

    state.moveGroup(createdGroup!.id, -1);
    state.renameGroup(createdGroup!.id, "Nya Grupp C");

    expect(state.groups.find((group) => group.id === createdGroup!.id)?.name).toBe("Nya Grupp C");

    state.removeGroup(createdGroup!.id);

    expect(state.groups.find((group) => group.id === createdGroup!.id)).toBeUndefined();
  });

  it("stores student planning metadata and pair constraints", () => {
    const state = seedWorkspace();

    state.setStudentPlanningMeta("s1", {
      preferred_zone: "front",
      notes: "Behöver lugn plats",
    });
    state.setPairConstraint("s1", "s2", "keep_apart", true, 2);

    expect(state.studentPlanningMetaByStudentId["s1"]?.preferred_zone).toBe("front");
    expect(state.pairConstraints).toEqual([
      {
        student_id_a: "s1",
        student_id_b: "s2",
        kind: "keep_apart",
        strength: 2,
      },
    ]);
  });

  it("updates planning profile toggles and weights", () => {
    const state = seedWorkspace();

    state.updatePlanningProfile({
      enable_history_rules: true,
      rotation_weight: 3,
      profile_kind: "rotation_first",
    });

    expect(state.planningProfile.enable_history_rules).toBe(true);
    expect(state.planningProfile.rotation_weight).toBe(3);
    expect(state.planningProfile.profile_kind).toBe("rotation_first");
  });
});
