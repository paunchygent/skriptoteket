<script setup lang="ts">
/**
 * Rules-workspace map panel.
 *
 * This component owns the view toggle and status line for the shared rules map
 * while delegating the actual room rendering to `PlannerRulesMapCanvas.vue`.
 */

import { computed } from "vue";

import UiSegmentedToggle from "../../../components/ui/UiSegmentedToggle.vue";
import type { RoomTemplate, SeatAssignment, SeatingSmartTool, Student } from "../classroomPlannerTypes";
import PlannerRulesMapCanvas from "./PlannerRulesMapCanvas.vue";

type RulesMapView = "planning_map" | "seating_arrangement";

const props = withDefaults(defineProps<{
  mapView: RulesMapView;
  template?: RoomTemplate | null;
  students?: Student[];
  studentsById?: Record<string, Student | undefined>;
  seatAssignments?: SeatAssignment[];
  selectedStudentId?: string | null;
  pendingSelectedStudentIds?: string[];
  smartRuleMarkersByStudentId?: Record<string, string[]>;
  activeTool?: SeatingSmartTool | null;
  canShowSeatingArrangement?: boolean;
  seatingArrangementUnavailableMessage?: string | null;
  statusText?: string | null;
}>(), {
  template: null,
  students: () => [],
  studentsById: () => ({}),
  seatAssignments: () => [],
  selectedStudentId: null,
  pendingSelectedStudentIds: () => [],
  smartRuleMarkersByStudentId: () => ({}),
  activeTool: null,
  canShowSeatingArrangement: false,
  seatingArrangementUnavailableMessage: null,
  statusText: null,
});

const emit = defineEmits<{
  (e: "update:map-view", value: RulesMapView): void;
  (e: "student-selected", studentId: string): void;
}>();

const mapOptions = computed(() => [
  { value: "planning_map", label: "Planeringskarta" },
  {
    value: "seating_arrangement",
    label: "Sittschema",
    disabled: !props.canShowSeatingArrangement,
    title: props.seatingArrangementUnavailableMessage ?? undefined,
  },
]);

function updateMapView(value: string): void {
  if (value === "planning_map" || value === "seating_arrangement") {
    emit("update:map-view", value);
  }
}
</script>

<template>
  <div class="space-y-3">
    <div class="border border-navy bg-white p-4 shadow-brutal-sm">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="space-y-1">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Kartvy
          </p>
          <p class="text-sm text-navy/70">
            {{ statusText ?? "Välj verktyg och klicka på eleverna på kartan." }}
          </p>
        </div>

        <UiSegmentedToggle
          :model-value="mapView"
          :options="mapOptions"
          aria-label="Välj kartvy för regler"
          density="default"
          :columns="2"
          width="auto"
          @update:model-value="updateMapView"
        />
      </div>

      <p
        v-if="!canShowSeatingArrangement && seatingArrangementUnavailableMessage"
        class="mt-3 text-sm text-navy/55"
      >
        {{ seatingArrangementUnavailableMessage }}
      </p>
    </div>

    <PlannerRulesMapCanvas
      :map-view="mapView"
      :template="template"
      :students="students"
      :students-by-id="studentsById"
      :seat-assignments="seatAssignments"
      :selected-student-id="selectedStudentId"
      :pending-selected-student-ids="pendingSelectedStudentIds"
      :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
      @student-selected="emit('student-selected', $event)"
    />
  </div>
</template>
