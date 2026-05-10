<script setup lang="ts">
/**
 * Phone fixed-seat rule panel.
 *
 * Purpose:
 *   Presents the phone-only fixed-seat binding summary and compact classroom
 *   seat map while preserving the canonical room template seat identities.
 *
 * Relationships:
 *   - rendered by `PlannerRulesWorkspacePane.vue` when `Fast plats` is active
 *   - emits the existing fixed-seat seat-selection event consumed by planner
 *     smart-rule state
 */

import { computed } from "vue";

import type {
  FixedSeatRule,
  RelationshipRule,
  RoomTemplate,
  SeatAssignment,
  SmartRuleDiagnostic,
  Student,
  StudentSeatingPreference,
} from "../classroomPlannerTypes";
import { formatSeatDisplayLabel } from "../classroomPlannerSmartRulePresentation";
import PlannerPhoneClassroomSeatMap from "./PlannerPhoneClassroomSeatMap.vue";

const props = withDefaults(defineProps<{
  template?: RoomTemplate | null;
  studentsById?: Record<string, Student | undefined>;
  seatAssignments?: SeatAssignment[];
  pendingFixedSeatStudentId?: string | null;
  pendingFixedSeatSeatId?: string | null;
  fixedSeatRules?: FixedSeatRule[];
  relationshipRules?: RelationshipRule[];
  seatingPreferences?: StudentSeatingPreference[];
  ruleDiagnostics?: SmartRuleDiagnostic[];
}>(), {
  template: null,
  studentsById: () => ({}),
  seatAssignments: () => [],
  pendingFixedSeatStudentId: null,
  pendingFixedSeatSeatId: null,
  fixedSeatRules: () => [],
  relationshipRules: () => [],
  seatingPreferences: () => [],
  ruleDiagnostics: () => [],
});

const emit = defineEmits<{
  (e: "clear-selection"): void;
  (e: "seat-selected", seatId: string): void;
}>();

const pendingStudentName = computed(() => {
  const studentId = props.pendingFixedSeatStudentId;
  return studentId ? props.studentsById[studentId]?.display_name ?? null : null;
});
const pendingSeatLabel = computed(() => {
  const seatId = props.pendingFixedSeatSeatId;
  return seatId ? formatSeatDisplayLabel(seatId) : null;
});
const canClearSelection = computed(() => (
  props.pendingFixedSeatStudentId !== null || props.pendingFixedSeatSeatId !== null
));
</script>

<template>
  <section
    class="planner-phone-fixed-seat-panel"
    data-test="phone-fixed-seat-panel"
  >
    <div class="flex items-start justify-between gap-3">
      <div>
        <h3 class="text-sm font-semibold text-navy">
          Fast plats
        </h3>
        <p class="text-xs text-navy/65">
          Välj elev och plats.
        </p>
      </div>
      <button
        type="button"
        class="planner-phone-link-button"
        data-test="phone-fixed-seat-clear"
        :disabled="!canClearSelection"
        @click="emit('clear-selection')"
      >
        Rensa
      </button>
    </div>

    <dl class="planner-phone-fixed-seat-binding">
      <div data-test="phone-fixed-seat-pending-student">
        <dt>Elev</dt>
        <dd>{{ pendingStudentName ?? "Välj elev" }}</dd>
      </div>
      <div data-test="phone-fixed-seat-pending-seat">
        <dt>Plats</dt>
        <dd>{{ pendingSeatLabel ?? "Välj en plats" }}</dd>
      </div>
    </dl>

    <PlannerPhoneClassroomSeatMap
      v-if="template"
      :template="template"
      :students-by-id="studentsById"
      :seat-assignments="seatAssignments"
      :selected-seat-id="pendingFixedSeatSeatId"
      :pending-fixed-seat-student-id="pendingFixedSeatStudentId"
      :pending-fixed-seat-seat-id="pendingFixedSeatSeatId"
      :fixed-seat-rules="fixedSeatRules"
      :relationship-rules="relationshipRules"
      :seating-preferences="seatingPreferences"
      :rule-diagnostics="ruleDiagnostics"
      data-test="phone-fixed-seat-map"
      @seat-selected="emit('seat-selected', $event)"
    />

    <div
      v-else
      class="planner-phone-fixed-seat-empty"
      data-test="phone-fixed-seat-empty"
    >
      Fast plats kräver ett klassrum. Välj ett klassrum först.
    </div>
  </section>
</template>
