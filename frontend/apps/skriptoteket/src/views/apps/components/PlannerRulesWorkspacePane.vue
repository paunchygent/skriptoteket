<script setup lang="ts">
/**
 * Dedicated rules workspace pane.
 *
 * This component hosts the approved `Regler` cut-over: one tool rail, one
 * shared map surface with dual projections, and one always-visible inspector.
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

const props = withDefaults(defineProps<{
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
const canShowSeatingArrangement = computed(() => plannerState.seatAssignments.length > 0);
const seatingArrangementUnavailableMessage = computed(() => {
  if (plannerState.template === null) {
    return "Sittschema blir tillgängligt när klassen har ett klassrum och en aktuell sittplacering.";
  }
  return "Sittschema blir tillgängligt när det finns ett aktuellt sittschema att spegla.";
});
const statusText = computed(() => {
  if (plannerState.activeSeatingSmartTool === "near_teacher") {
    return "Klicka på en elev för att lägga till eller ta bort Närmare läraren direkt.";
  }
  if (plannerState.activeSeatingSmartTool === "keep_near") {
    return "Välj minst två elever som ska hållas nära och spara regeln i inspektören.";
  }
  if (plannerState.activeSeatingSmartTool === "keep_apart") {
    return "Välj minst två elever som ska hållas isär och spara regeln i inspektören.";
  }
  return "Välj ett verktyg i railen och klicka sedan på eleverna på kartan.";
});

function selectTool(tool: "near_teacher" | "keep_near" | "keep_apart"): void {
  plannerState.setActiveSeatingSmartTool(tool);
}

function editRelationshipRule(ruleId: string): void {
  plannerState.beginRelationshipRuleEdit(ruleId);
}

function removeNearTeacherStudent(studentId: string): void {
  plannerState.setStudentNearTeacherEnabled(studentId, false);
}

function replaceNearTeacherStudent(payload: {
  previousStudentId: string;
  nextStudentId: string;
}): void {
  plannerState.replaceNearTeacherPreference(payload.previousStudentId, payload.nextStudentId);
}

watch(canShowSeatingArrangement, (nextValue) => {
  if (!nextValue && mapView.value === "seating_arrangement") {
    mapView.value = "planning_map";
  }
});
</script>

<template>
  <div class="space-y-4">
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
          class="btn-ghost border-amber-400/70 bg-white px-3 py-1.5 text-amber-900 shadow-none"
          data-test="rules-smart-retry-hydration"
          @click="void plannerState.retrySmartRuleHydration()"
        >
          Försök igen
        </button>
      </div>
    </div>

    <div class="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)_360px]">
      <PlannerRulesToolRail
        :active-tool="plannerState.activeSeatingSmartTool"
        :can-edit="plannerState.canEditSeatingSmartRules"
        :pending-selection-count="plannerState.pendingRelationshipStudentIds.length"
        @select-tool="selectTool"
        @clear-selection="plannerState.clearPendingRelationshipSelection()"
      />

      <PlannerRulesMapPanel
        :map-view="mapView"
        :template="plannerState.template"
        :students="plannerState.students"
        :students-by-id="plannerState.studentsById"
        :seat-assignments="plannerState.seatAssignments"
        :selected-student-id="selectedStudentId"
        :pending-selected-student-ids="plannerState.pendingRelationshipStudentIds"
        :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
        :active-tool="plannerState.activeSeatingSmartTool"
        :can-show-seating-arrangement="canShowSeatingArrangement"
        :seating-arrangement-unavailable-message="seatingArrangementUnavailableMessage"
        :status-text="statusText"
        @update:map-view="mapView = $event"
        @student-selected="emit('student-selected', $event)"
      />

      <PlannerRulesInspector
        :near-teacher-students="nearTeacherStudents"
        :relationship-rules="plannerState.relationshipRules"
        :students-by-id="plannerState.studentsById"
        :pending-selected-student-ids="plannerState.pendingRelationshipStudentIds"
        :active-tool="plannerState.activeSeatingSmartTool"
        :editing-relationship-rule-id="plannerState.editingRelationshipRuleId"
        :can-commit-pending-relationship-rule="plannerState.canCommitPendingRelationshipRule"
        :can-edit="plannerState.canEditSeatingSmartRules"
        :feedback-message="plannerState.smartRuleFeedbackMessage"
        @replace-near-teacher="replaceNearTeacherStudent"
        @remove-near-teacher="removeNearTeacherStudent"
        @edit-rule="editRelationshipRule"
        @delete-rule="plannerState.deleteRelationshipRule($event)"
        @commit-pending="plannerState.commitPendingRelationshipRule()"
        @clear-selection="plannerState.clearPendingRelationshipSelection()"
      />
    </div>
  </div>
</template>
