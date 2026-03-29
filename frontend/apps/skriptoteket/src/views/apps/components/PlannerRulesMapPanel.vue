<script setup lang="ts">
/**
 * Rules-workspace map panel.
 *
 * This component is the map host for the shared rules canvas and the
 * canvas-local projection switch.
 */

import type { RoomTemplate, SeatAssignment, Student } from "../classroomPlannerTypes";
import PlannerRulesMapCanvas from "./PlannerRulesMapCanvas.vue";

type RulesMapView = "planning_map" | "seating_arrangement";

withDefaults(defineProps<{
  mapView: RulesMapView;
  canShowSeatingArrangement?: boolean;
  seatingArrangementUnavailableMessage?: string | null;
  template?: RoomTemplate | null;
  students?: Student[];
  studentsById?: Record<string, Student | undefined>;
  seatAssignments?: SeatAssignment[];
  selectedStudentId?: string | null;
  pendingSelectedStudentIds?: string[];
  smartRuleMarkersByStudentId?: Record<string, string[]>;
}>(), {
  canShowSeatingArrangement: false,
  seatingArrangementUnavailableMessage: null,
  template: null,
  students: () => [],
  studentsById: () => ({}),
  seatAssignments: () => [],
  selectedStudentId: null,
  pendingSelectedStudentIds: () => [],
  smartRuleMarkersByStudentId: () => ({}),
});

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "update:mapView", value: RulesMapView): void;
}>();
</script>

<template>
  <div>
    <PlannerRulesMapCanvas
      :map-view="mapView"
      :can-show-seating-arrangement="canShowSeatingArrangement"
      :seating-arrangement-unavailable-message="seatingArrangementUnavailableMessage"
      :template="template"
      :students="students"
      :students-by-id="studentsById"
      :seat-assignments="seatAssignments"
      :selected-student-id="selectedStudentId"
      :pending-selected-student-ids="pendingSelectedStudentIds"
      :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
      @update:map-view="emit('update:mapView', $event)"
      @student-selected="emit('student-selected', $event)"
    />
  </div>
</template>
