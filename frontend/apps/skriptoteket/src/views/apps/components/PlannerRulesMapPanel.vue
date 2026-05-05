<script setup lang="ts">
/**
 * Rules-workspace map panel.
 *
 * Purpose:
 *   Passes classroom, roster, selection, and fixed-seat marker state into the
 *   shared rules canvas.
 *
 * Relationships:
 *   - rendered by `PlannerRulesWorkspacePane.vue`
 *   - delegates map view switching and seat/student clicks to the workspace
 *   - wraps `PlannerRulesMapCanvas.vue`
 */

import type {
  FixedSeatRule,
  RoomTemplate,
  SeatAssignment,
  SeatingSmartTool,
  Student,
} from "../classroomPlannerTypes";
import PlannerRulesMapCanvas from "./PlannerRulesMapCanvas.vue";

type RulesMapView = "planning_map" | "seating_arrangement";

withDefaults(defineProps<{
  mapView: RulesMapView;
  rosterName?: string | null;
  canShowSeatingArrangement?: boolean;
  seatingArrangementUnavailableMessage?: string | null;
  template?: RoomTemplate | null;
  students?: Student[];
  studentsById?: Record<string, Student | undefined>;
  seatAssignments?: SeatAssignment[];
  selectedStudentId?: string | null;
  pendingSelectedStudentIds?: string[];
  activeTool?: SeatingSmartTool | null;
  pendingFixedSeatStudentId?: string | null;
  pendingFixedSeatSeatId?: string | null;
  fixedSeatRules?: FixedSeatRule[];
  smartRuleMarkersByStudentId?: Record<string, string[]>;
}>(), {
  canShowSeatingArrangement: false,
  rosterName: null,
  seatingArrangementUnavailableMessage: null,
  template: null,
  students: () => [],
  studentsById: () => ({}),
  seatAssignments: () => [],
  selectedStudentId: null,
  pendingSelectedStudentIds: () => [],
  activeTool: null,
  pendingFixedSeatStudentId: null,
  pendingFixedSeatSeatId: null,
  fixedSeatRules: () => [],
  smartRuleMarkersByStudentId: () => ({}),
});

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "seat-selected", seatId: string): void;
  (e: "update:mapView", value: RulesMapView): void;
}>();
</script>

<template>
  <div>
    <PlannerRulesMapCanvas
      :map-view="mapView"
      :roster-name="rosterName"
      :can-show-seating-arrangement="canShowSeatingArrangement"
      :seating-arrangement-unavailable-message="seatingArrangementUnavailableMessage"
      :template="template"
      :students="students"
      :students-by-id="studentsById"
      :seat-assignments="seatAssignments"
      :selected-student-id="selectedStudentId"
      :pending-selected-student-ids="pendingSelectedStudentIds"
      :active-tool="activeTool"
      :pending-fixed-seat-student-id="pendingFixedSeatStudentId"
      :pending-fixed-seat-seat-id="pendingFixedSeatSeatId"
      :fixed-seat-rules="fixedSeatRules"
      :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
      @update:map-view="emit('update:mapView', $event)"
      @student-selected="emit('student-selected', $event)"
      @seat-selected="emit('seat-selected', $event)"
    />
  </div>
</template>
