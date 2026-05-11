<script setup lang="ts">
/**
 * Dedicated rules workspace pane.
 *
 * This component hosts the approved `Regler` cut-over: one compact tool rail,
 * one wide shared map surface with a canvas-local projection switch, and one
 * top summary panel for active rules only.
 */

import { ref, watch } from "vue";

import {
  IconArrow,
  IconInfo,
} from "../../../components/icons";
import { PHONE_RULE_TOOL_ROWS } from "../plannerPhoneRuleToolRows";
import { usePlannerRulesWorkspaceViewState } from "../plannerRulesWorkspaceViewState";
import PlannerRulesInspector from "./PlannerRulesInspector.vue";
import PlannerRulesMapPanel from "./PlannerRulesMapPanel.vue";
import PlannerPhoneFixedSeatRulePanel from "./PlannerPhoneFixedSeatRulePanel.vue";
import PlannerPhoneRelationshipRuleSelection from "./PlannerPhoneRelationshipRuleSelection.vue";
import PlannerPhoneRulesSummary from "./PlannerPhoneRulesSummary.vue";
import PlannerStudentPool from "./PlannerStudentPool.vue";
import PlannerRulesToolRail from "./PlannerRulesToolRail.vue";
import PlannerFixedSeatSwitchPrompt from "./PlannerFixedSeatSwitchPrompt.vue";
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
const phoneStudentListOpen = ref(true);
const fixedSeatSwitchPromptOpen = ref(false);
const phoneFixedSeatClassroomMessageVisible = ref(false);

const {
  activeFixedSeatRules,
  canUseClassroomView,
  nearTeacherStudents,
  pendingFixedSeatSeatLabel,
  pendingFixedSeatStudentName,
  pendingRuleStudents,
  pendingSelectionCount,
  phoneCanCommitRelationshipRule,
  phoneSelectedStudentIds,
  phoneStudentCountLabel,
  seatingArrangementUnavailableMessage,
  smartRuleMarkersByStudentId,
} = usePlannerRulesWorkspaceViewState(plannerState);
const phoneToolRows = PHONE_RULE_TOOL_ROWS;

function activateFixedSeatTool(): void {
  fixedSeatSwitchPromptOpen.value = false;
  phoneFixedSeatClassroomMessageVisible.value = false;
  mapView.value = "seating_arrangement";
  plannerState.setActiveSeatingSmartTool("fixed_seat");
}

function selectTool(tool: "near_teacher" | "keep_near" | "keep_apart" | "fixed_seat"): void {
  if (tool === "fixed_seat") {
    if (!canUseClassroomView.value) {
      phoneFixedSeatClassroomMessageVisible.value = true;
      return;
    }
    phoneFixedSeatClassroomMessageVisible.value = false;
    if (mapView.value === "planning_map") {
      fixedSeatSwitchPromptOpen.value = true;
      return;
    }
    plannerState.setActiveSeatingSmartTool(tool);
    return;
  }
  phoneFixedSeatClassroomMessageVisible.value = false;
  if (tool === "near_teacher") {
    fixedSeatSwitchPromptOpen.value = false;
    if (plannerState.activeSeatingSmartTool === tool) {
      return;
    }
    plannerState.setActiveSeatingSmartTool(tool);
    return;
  }
  fixedSeatSwitchPromptOpen.value = false;
  if (plannerState.activeSeatingSmartTool === tool) {
    return;
  }
  plannerState.setActiveSeatingSmartTool(tool);
}

function declineFixedSeatSwitch(): void {
  fixedSeatSwitchPromptOpen.value = false;
}

function closeFixedSeatSwitchPrompt(): void {
  fixedSeatSwitchPromptOpen.value = false;
}

function editRelationshipRule(ruleId: string): void {
  plannerState.beginRelationshipRuleEdit(ruleId);
}

function beginNearTeacherEdit(): void {
  plannerState.beginNearTeacherEdit();
}

function removePendingRelationshipStudent(studentId: string): void {
  plannerState.removePendingRuleCandidate(studentId);
}

function togglePhoneStudentList(): void {
  phoneStudentListOpen.value = !phoneStudentListOpen.value;
}

function handlePhoneStudentSelection(studentId: string): void {
  if (plannerState.activeSeatingSmartTool) {
    if (plannerState.isStudentInPendingRuleCandidates(studentId)) {
      plannerState.removePendingRuleCandidate(studentId);
      return;
    }
    plannerState.handleSeatingSmartToolStudentSelection(studentId);
    return;
  }
  emit("student-selected", studentId);
}

function onPhoneStudentDragStart(event: DragEvent, studentId: string): void {
  if (!event.dataTransfer) {
    return;
  }
  event.dataTransfer.setData("studentId", studentId);
  event.dataTransfer.effectAllowed = "move";
}

function onPhoneSelectionDragOver(event: DragEvent): void {
  if (!plannerState.activeSeatingSmartTool) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
}

function onPhoneSelectionDrop(event: DragEvent): void {
  event.preventDefault();
  const studentId = event.dataTransfer?.getData("studentId");
  if (studentId && plannerState.activeSeatingSmartTool) {
    if (plannerState.isStudentInPendingRelationshipSelection(studentId)) {
      return;
    }
    plannerState.handleSeatingSmartToolStudentSelection(studentId);
  }
}

watch(
  () => plannerState.canEditSeatingSmartRules,
  (canEdit) => {
    if (canEdit && !plannerState.activeSeatingSmartTool) {
      plannerState.setActiveSeatingSmartTool("near_teacher");
    }
  },
  { immediate: true },
);

watch(canUseClassroomView, (nextValue) => {
  if (nextValue) {
    phoneFixedSeatClassroomMessageVisible.value = false;
  }
  if (nextValue && mapView.value === "planning_map") {
    mapView.value = "seating_arrangement";
    return;
  }
  if (!nextValue && mapView.value === "seating_arrangement") {
    mapView.value = "planning_map";
  }
}, { immediate: true });

watch(mapView, (nextValue) => {
  if (nextValue === "planning_map" && plannerState.activeSeatingSmartTool === "fixed_seat") {
    plannerState.setActiveSeatingSmartTool(null);
  }
  if (nextValue !== "planning_map") {
    fixedSeatSwitchPromptOpen.value = false;
  }
});
</script>

<template>
  <div class="space-y-3">
    <div
      v-if="plannerState.smartRuleHydrationStatus === 'error'"
      class="border border-warning/50 bg-warning/10 px-4 py-3 text-sm text-navy shadow-brutal-sm"
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

    <div
      class="planner-phone-rules-workspace"
      data-test="phone-rules-workspace"
    >
      <div
        class="planner-phone-status-row"
        data-test="phone-rules-scope-status"
      >
        <IconInfo :size="16" />
        <span>Reglerna gäller hela klassen.</span>
      </div>

      <div class="grid gap-1.5">
        <button
          v-for="tool in phoneToolRows"
          :key="tool.id"
          type="button"
          class="planner-phone-rule-row"
          :class="plannerState.activeSeatingSmartTool === tool.id ? 'planner-phone-rule-row-active' : ''"
          :disabled="!plannerState.canEditSeatingSmartRules"
          :data-test="`phone-rules-tool-${tool.id}`"
          @click="selectTool(tool.id)"
        >
          <component
            :is="tool.icon"
            :size="18"
            class="shrink-0"
          />
          <span class="min-w-0 flex-1">
            <span class="block text-sm font-semibold">{{ tool.label }}</span>
            <span
              class="block text-xs"
              :class="plannerState.activeSeatingSmartTool === tool.id ? 'text-button-primary-text/75' : 'text-navy/60'"
            >
              {{ tool.subtitle }}
            </span>
          </span>
          <span aria-hidden="true">›</span>
        </button>
      </div>

      <PlannerPhoneRulesSummary
        :near-teacher-students="nearTeacherStudents"
        :relationship-rules="plannerState.relationshipRules"
        :fixed-seat-rules="activeFixedSeatRules"
        :students-by-id="plannerState.studentsById"
        :editing-relationship-rule-id="plannerState.editingRelationshipRuleId"
        :editing-fixed-seat-rule-id="plannerState.editingFixedSeatRuleId"
        :editing-near-teacher-rule="plannerState.editingNearTeacherRule"
        :can-edit="plannerState.canEditSeatingSmartRules"
        @edit-near-teacher="beginNearTeacherEdit"
        @delete-near-teacher="plannerState.clearNearTeacherRule()"
        @edit-rule="editRelationshipRule"
        @delete-rule="plannerState.deleteRelationshipRule($event)"
        @edit-fixed-seat-rule="plannerState.beginFixedSeatRuleEdit($event)"
        @delete-fixed-seat-rule="plannerState.deleteFixedSeatRule($event)"
      />

      <div
        v-if="phoneFixedSeatClassroomMessageVisible"
        class="planner-phone-fixed-seat-empty"
        data-test="phone-rules-fixed-seat-classroom-required"
      >
        Fast plats kräver ett klassrum. Välj ett klassrum först.
      </div>

      <PlannerPhoneFixedSeatRulePanel
        v-if="plannerState.activeSeatingSmartTool === 'fixed_seat'"
        :template="plannerState.template"
        :students-by-id="plannerState.studentsById"
        :seat-assignments="plannerState.seatAssignments"
        :pending-fixed-seat-student-id="plannerState.pendingFixedSeatStudentId"
        :pending-fixed-seat-seat-id="plannerState.pendingFixedSeatSeatId"
        :fixed-seat-rules="activeFixedSeatRules"
        :relationship-rules="plannerState.relationshipRules"
        :seating-preferences="plannerState.seatingPreferences"
        :rule-diagnostics="plannerState.smartRuleDiagnostics"
        @clear-selection="plannerState.clearPendingRuleCandidates()"
        @seat-selected="plannerState.selectFixedSeatRuleSeat($event)"
      />

      <PlannerPhoneRelationshipRuleSelection
        v-else
        :students="pendingRuleStudents"
        @clear-selection="plannerState.clearPendingRuleCandidates()"
        @remove-student="removePendingRelationshipStudent"
        @selection-dragover="onPhoneSelectionDragOver"
        @selection-drop="onPhoneSelectionDrop"
      />

      <button
        type="button"
        class="planner-phone-row-action"
        data-test="phone-rules-student-list-trigger"
        :aria-expanded="phoneStudentListOpen"
        @click="togglePhoneStudentList"
      >
        <span>Elever</span>
        <span class="flex shrink-0 items-center gap-2 text-xs text-navy/60">
          {{ phoneStudentCountLabel }}
          <IconArrow
            :size="15"
            :direction="phoneStudentListOpen ? 'up' : 'down'"
          />
        </span>
      </button>

      <div
        v-if="phoneStudentListOpen"
        class="planner-phone-rules-student-tray"
        data-test="phone-rules-student-list"
      >
        <PlannerStudentPool
          title="Elever"
          :students="plannerState.students"
          :disabled="!plannerState.activeSeatingSmartTool"
          :selected-student-id="selectedStudentId"
          :selected-student-ids="phoneSelectedStudentIds"
          selected-click-action="remove"
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          empty-label="Inga elever"
          root-test-id="phone-rules-student-pool"
          @student-selected="handlePhoneStudentSelection"
          @selected-student-removed="removePendingRelationshipStudent"
          @student-dragstart="onPhoneStudentDragStart($event.event, $event.studentId)"
          @pool-dragover="onPhoneSelectionDragOver"
          @pool-drop="onPhoneSelectionDrop"
        />
      </div>

      <button
        v-if="phoneCanCommitRelationshipRule"
        type="button"
        class="btn-primary planner-btn-primary-sm w-full"
        data-test="phone-rules-commit-rule"
        :disabled="!plannerState.canCommitPendingRelationshipRule"
        @click="plannerState.commitPendingRelationshipRule()"
      >
        Spara regel
      </button>

      <button
        v-if="plannerState.activeSeatingSmartTool === 'fixed_seat'"
        type="button"
        class="btn-primary planner-btn-primary-sm w-full"
        data-test="phone-rules-commit-fixed-seat"
        :disabled="!plannerState.canCommitPendingFixedSeatRule"
        @click="plannerState.commitPendingFixedSeatRule()"
      >
        Spara regel
      </button>
    </div>

    <div class="planner-desktop-rules-workspace">
      <PlannerRulesInspector
        :near-teacher-students="nearTeacherStudents"
        :relationship-rules="plannerState.relationshipRules"
        :fixed-seat-rules="activeFixedSeatRules"
        :students-by-id="plannerState.studentsById"
        :editing-relationship-rule-id="plannerState.editingRelationshipRuleId"
        :editing-fixed-seat-rule-id="plannerState.editingFixedSeatRuleId"
        :editing-near-teacher-rule="plannerState.editingNearTeacherRule"
        :can-edit="plannerState.canEditSeatingSmartRules"
        @edit-near-teacher="beginNearTeacherEdit"
        @delete-near-teacher="plannerState.clearNearTeacherRule()"
        @edit-rule="editRelationshipRule"
        @delete-rule="plannerState.deleteRelationshipRule($event)"
        @edit-fixed-seat-rule="plannerState.beginFixedSeatRuleEdit($event)"
        @delete-fixed-seat-rule="plannerState.deleteFixedSeatRule($event)"
      />

      <div
        class="planner-rules-layout-row"
        data-test="rules-workspace-layout"
      >
        <div class="planner-rules-tool-column relative grid gap-2">
          <PlannerRulesToolRail
            :active-tool="plannerState.activeSeatingSmartTool"
            :can-edit="plannerState.canEditSeatingSmartRules"
            :pending-selection-count="pendingSelectionCount"
            :pending-students="pendingRuleStudents"
            :pending-fixed-seat-student-name="pendingFixedSeatStudentName"
            :pending-fixed-seat-seat-label="pendingFixedSeatSeatLabel"
            :editing-relationship-rule-id="plannerState.editingRelationshipRuleId"
            :editing-fixed-seat-rule-id="plannerState.editingFixedSeatRuleId"
            :editing-near-teacher-rule="plannerState.editingNearTeacherRule"
            :can-commit-pending-relationship-rule="plannerState.canCommitPendingRelationshipRule"
            :can-commit-pending-fixed-seat-rule="plannerState.canCommitPendingFixedSeatRule"
            :feedback-message="plannerState.smartRuleFeedbackMessage"
            @select-tool="selectTool"
            @clear-selection="plannerState.clearPendingRuleCandidates()"
            @remove-pending-student="removePendingRelationshipStudent"
            @commit-pending="plannerState.commitPendingRelationshipRule()"
            @commit-fixed-seat="plannerState.commitPendingFixedSeatRule()"
          />

          <PlannerFixedSeatSwitchPrompt
            v-if="fixedSeatSwitchPromptOpen"
            @accept="activateFixedSeatTool"
            @decline="declineFixedSeatSwitch"
            @close="closeFixedSeatSwitchPrompt"
          />
        </div>

        <PlannerRulesMapPanel
          :map-view="mapView"
          :roster-name="plannerState.roster?.name ?? null"
          :can-show-seating-arrangement="canUseClassroomView"
          :seating-arrangement-unavailable-message="seatingArrangementUnavailableMessage"
          :template="plannerState.template"
          :students="plannerState.students"
          :students-by-id="plannerState.studentsById"
          :seat-assignments="plannerState.seatAssignments"
          :selected-student-id="selectedStudentId"
          :pending-selected-student-ids="plannerState.pendingRelationshipStudentIds"
          :active-tool="plannerState.activeSeatingSmartTool"
          :pending-fixed-seat-student-id="plannerState.pendingFixedSeatStudentId"
          :pending-fixed-seat-seat-id="plannerState.pendingFixedSeatSeatId"
          :fixed-seat-rules="activeFixedSeatRules"
          :relationship-rules="plannerState.relationshipRules"
          :seating-preferences="plannerState.seatingPreferences"
          :rule-diagnostics="plannerState.smartRuleDiagnostics"
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          @update:map-view="mapView = $event"
          @student-selected="emit('student-selected', $event)"
          @selected-student-removed="removePendingRelationshipStudent"
          @seat-selected="plannerState.selectFixedSeatRuleSeat($event)"
        />
      </div>
    </div>
  </div>
</template>
