<script setup lang="ts">
/**
 * Dedicated rules workspace pane.
 *
 * This component hosts the approved `Regler` cut-over: one compact tool rail,
 * one wide shared map surface with a canvas-local projection switch, and one
 * top summary panel for active rules only.
 */

import { computed, ref, watch } from "vue";

import {
  IconArrow,
  IconInfo,
  IconKeepApart,
  IconKeepNear,
  IconTeacherAnchor,
  IconX,
} from "../../../components/icons";
import type { Student } from "../classroomPlannerTypes";
import {
  buildSmartRuleMarkersByStudentId,
} from "../classroomPlannerSmartRulePresentation";
import PlannerRulesInspector from "./PlannerRulesInspector.vue";
import PlannerRulesMapPanel from "./PlannerRulesMapPanel.vue";
import PlannerStudentPool from "./PlannerStudentPool.vue";
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
const phoneStudentListOpen = ref(true);

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
const phoneStudentCountLabel = computed(() => {
  const count = plannerState.students.length;
  return count === 1 ? "1 elev" : `${count} elever`;
});
const canShowSeatingArrangement = computed(() => plannerState.seatAssignments.length > 0);
const seatingArrangementUnavailableMessage = computed(() => {
  if (plannerState.template === null) {
    return "Sittschema blir tillgängligt när klassen har ett klassrum och en aktuell sittplacering.";
  }
  return "Sittschema blir tillgängligt när det finns ett aktuellt sittschema att spegla.";
});
const phoneToolRows = computed(() => [
  {
    id: "near_teacher" as const,
    label: "Nära läraren",
    subtitle: "Placera elever nära katedern.",
    icon: IconTeacherAnchor,
  },
  {
    id: "keep_apart" as const,
    label: "Håll isär",
    subtitle: "Placera elever på avstånd.",
    icon: IconKeepApart,
  },
  {
    id: "keep_near" as const,
    label: "Håll nära",
    subtitle: "Placera elever tillsammans.",
    icon: IconKeepNear,
  },
]);

function selectTool(tool: "near_teacher" | "keep_near" | "keep_apart"): void {
  if (tool === "near_teacher") {
    plannerState.beginNearTeacherEdit();
    return;
  }
  if (plannerState.activeSeatingSmartTool === tool) {
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

function togglePhoneStudentList(): void {
  phoneStudentListOpen.value = !phoneStudentListOpen.value;
}

function handlePhoneStudentSelection(studentId: string): void {
  if (plannerState.activeSeatingSmartTool) {
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
    plannerState.handleSeatingSmartToolStudentSelection(studentId);
  }
}

watch(
  () => plannerState.canEditSeatingSmartRules,
  (canEdit) => {
    if (canEdit && !plannerState.activeSeatingSmartTool) {
      plannerState.beginNearTeacherEdit();
    }
  },
  { immediate: true },
);

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
              :class="plannerState.activeSeatingSmartTool === tool.id ? 'text-canvas/75' : 'text-navy/60'"
            >
              {{ tool.subtitle }}
            </span>
          </span>
          <span aria-hidden="true">›</span>
        </button>
      </div>

      <div
        class="planner-phone-rules-selection"
        data-test="phone-rules-selection"
        @dragover="onPhoneSelectionDragOver"
        @drop="onPhoneSelectionDrop"
      >
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-sm font-semibold text-navy">
            Valda elever ({{ pendingRuleStudents.length }})
          </h3>
          <button
            type="button"
            class="planner-phone-link-button"
            data-test="phone-rules-clear-selection"
            :disabled="pendingRuleStudents.length === 0"
            @click="plannerState.clearPendingRelationshipSelection()"
          >
            Rensa
          </button>
        </div>
        <div
          v-if="pendingRuleStudents.length > 0"
          class="mt-2 grid gap-1.5"
        >
          <div
            v-for="student in pendingRuleStudents"
            :key="student.id"
            class="planner-phone-selected-student-row"
            data-test="phone-rules-selected-student"
          >
            <span class="truncate">{{ student.name }}</span>
            <button
              type="button"
              class="planner-row-remove-button"
              :aria-label="`Ta bort ${student.name} från regeln`"
              @click="removePendingRelationshipStudent(student.id)"
            >
              <IconX :size="14" />
            </button>
          </div>
        </div>
      </div>

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
          :selected-student-ids="plannerState.pendingRelationshipStudentIds"
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          empty-label="Inga elever"
          root-test-id="phone-rules-student-pool"
          @student-selected="handlePhoneStudentSelection"
          @student-dragstart="onPhoneStudentDragStart($event.event, $event.studentId)"
          @pool-dragover="onPhoneSelectionDragOver"
          @pool-drop="onPhoneSelectionDrop"
        />
      </div>

      <button
        v-if="plannerState.activeSeatingSmartTool"
        type="button"
        class="btn-primary planner-btn-primary-sm w-full"
        data-test="phone-rules-commit-rule"
        :disabled="!plannerState.canCommitPendingRelationshipRule"
        @click="plannerState.commitPendingRelationshipRule()"
      >
        Spara regel
      </button>
    </div>

    <div class="planner-desktop-rules-workspace">
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
        class="planner-rules-layout-row"
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
          :roster-name="plannerState.roster?.name ?? null"
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
  </div>
</template>
