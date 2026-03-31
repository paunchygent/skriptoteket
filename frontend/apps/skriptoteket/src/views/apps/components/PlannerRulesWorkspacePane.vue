<script setup lang="ts">
/**
 * Dedicated rules workspace pane.
 *
 * This component hosts the approved `Regler` cut-over: one compact tool rail,
 * one wide shared map surface with a canvas-local projection switch, and one
 * top summary panel for active rules only.
 */

import { computed, ref, watch } from "vue";

import type { Student } from "../classroomPlannerTypes";
import {
  buildSmartRuleMarkersByStudentId,
} from "../classroomPlannerSmartRulePresentation";
import PlannerRulesInspector from "./PlannerRulesInspector.vue";
import PlannerRulesMapPanel from "./PlannerRulesMapPanel.vue";
import PlannerRulesToolRail from "./PlannerRulesToolRail.vue";
import { useClassroomState } from "../useClassroomState";

type RulesMapView = "planning_map" | "seating_arrangement";

withDefaults(defineProps<{
  selectedStudentId?: string | null;
}>(), {
  selectedStudentId: null,
});

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
}>();

const plannerState = useClassroomState();
const mapView = ref<RulesMapView>("planning_map");

const nearTeacherStudents = computed<Student[]>(() => {
  return plannerState.seatingPreferences
    .filter((preference) => preference.near_teacher === true)
    .map((preference) => plannerState.studentsById[preference.student_id] ?? null)
    .filter((student): student is Student => student !== null);
});
const smartRuleMarkersByStudentId = computed(() => {
  return buildSmartRuleMarkersByStudentId(
    plannerState.seatingPreferences,
    plannerState.relationshipRules,
  );
});
const pendingRuleStudents = computed(() => {
  return plannerState.pendingRelationshipStudentIds
    .map((studentId) => {
      const student = plannerState.studentsById[studentId];
      if (!student) {
        return null;
      }
      return { id: student.id, name: student.display_name };
    })
    .filter((student): student is { id: string; name: string } => student !== null);
});
const canShowSeatingArrangement = computed(() => plannerState.seatAssignments.length > 0);
const seatingArrangementUnavailableMessage = computed(() => {
  if (plannerState.template === null) {
    return "Sittschema blir tillgängligt när klassen har ett klassrum och en aktuell sittplacering.";
  }
  return "Sittschema blir tillgängligt när det finns ett aktuellt sittschema att spegla.";
});

function selectTool(tool: "near_teacher" | "keep_near" | "keep_apart"): void {
  if (tool === "near_teacher") {
    if (plannerState.activeSeatingSmartTool === "near_teacher") {
      plannerState.setActiveSeatingSmartTool("near_teacher");
      return;
    }
    plannerState.beginNearTeacherEdit();
    return;
  }
  plannerState.setActiveSeatingSmartTool(tool);
}

function editRelationshipRule(ruleId: string): void {
  plannerState.beginRelationshipRuleEdit(ruleId);
}

function beginNearTeacherEdit(): void {
  plannerState.beginNearTeacherEdit();
}

function removePendingRelationshipStudent(studentId: string): void {
  plannerState.handleSeatingSmartToolStudentSelection(studentId);
}

watch(canShowSeatingArrangement, (nextValue) => {
  if (!nextValue && mapView.value === "seating_arrangement") {
    mapView.value = "planning_map";
  }
});
</script>

<template>
  <div class="space-y-3">
    <div
      v-if="plannerState.smartRuleHydrationStatus === 'error'"
      class="border border-amber-300/80 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-brutal-sm"
      data-test="rules-smart-hydration-error"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p>
          {{ plannerState.smartRuleHydrationMessage }}
        </p>
        <button
          type="button"
          class="btn-ghost planner-btn-alert planner-btn-ghost-sm"
          data-test="rules-smart-retry-hydration"
          @click="void plannerState.retrySmartRuleHydration()"
        >
          Försök igen
        </button>
      </div>
    </div>

    <PlannerRulesInspector
      :near-teacher-students="nearTeacherStudents"
      :relationship-rules="plannerState.relationshipRules"
      :students-by-id="plannerState.studentsById"
      :editing-relationship-rule-id="plannerState.editingRelationshipRuleId"
      :editing-near-teacher-rule="plannerState.editingNearTeacherRule"
      :can-edit="plannerState.canEditSeatingSmartRules"
      @edit-near-teacher="beginNearTeacherEdit"
      @delete-near-teacher="plannerState.clearNearTeacherRule()"
      @edit-rule="editRelationshipRule"
      @delete-rule="plannerState.deleteRelationshipRule($event)"
    />

    <div
      class="grid gap-3 xl:grid-cols-[176px_minmax(0,1fr)] xl:items-stretch"
      data-test="rules-workspace-layout"
    >
      <PlannerRulesToolRail
        :active-tool="plannerState.activeSeatingSmartTool"
        :can-edit="plannerState.canEditSeatingSmartRules"
        :pending-selection-count="plannerState.pendingRelationshipStudentIds.length"
        :pending-students="pendingRuleStudents"
        :editing-relationship-rule-id="plannerState.editingRelationshipRuleId"
        :editing-near-teacher-rule="plannerState.editingNearTeacherRule"
        :can-commit-pending-relationship-rule="plannerState.canCommitPendingRelationshipRule"
        :feedback-message="plannerState.smartRuleFeedbackMessage"
        @select-tool="selectTool"
        @clear-selection="plannerState.clearPendingRelationshipSelection()"
        @remove-pending-student="removePendingRelationshipStudent"
        @commit-pending="plannerState.commitPendingRelationshipRule()"
      />

      <PlannerRulesMapPanel
        :map-view="mapView"
        :can-show-seating-arrangement="canShowSeatingArrangement"
        :seating-arrangement-unavailable-message="seatingArrangementUnavailableMessage"
        :template="plannerState.template"
        :students="plannerState.students"
        :students-by-id="plannerState.studentsById"
        :seat-assignments="plannerState.seatAssignments"
        :selected-student-id="selectedStudentId"
        :pending-selected-student-ids="plannerState.pendingRelationshipStudentIds"
        :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
        @update:map-view="mapView = $event"
        @student-selected="emit('student-selected', $event)"
      />
    </div>
  </div>
</template>
