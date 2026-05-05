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
  IconLock,
  IconTeacherAnchor,
  IconX,
} from "../../../components/icons";
import type { Student } from "../classroomPlannerTypes";
import {
  buildSmartRuleMarkersByStudentId,
  formatSeatDisplayLabel,
} from "../classroomPlannerSmartRulePresentation";
import PlannerRulesInspector from "./PlannerRulesInspector.vue";
import PlannerRulesMapPanel from "./PlannerRulesMapPanel.vue";
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

const nearTeacherStudents = computed<Student[]>(() => {
  return plannerState.seatingPreferences
    .filter((preference) => preference.near_teacher === true)
    .map((preference) => plannerState.studentsById[preference.student_id] ?? null)
    .filter((student): student is Student => student !== null);
});
const activeFixedSeatRules = computed(() => {
  const templateId = plannerState.template?.id ?? null;
  if (!templateId) {
    return [];
  }
  return plannerState.fixedSeatRules.filter((rule) => rule.template_id === templateId);
});
const smartRuleMarkersByStudentId = computed(() => {
  return buildSmartRuleMarkersByStudentId(
    plannerState.seatingPreferences,
    plannerState.relationshipRules,
    activeFixedSeatRules.value,
  );
});
const pendingFixedSeatStudentName = computed(() => {
  const studentId = plannerState.pendingFixedSeatStudentId;
  if (!studentId) {
    return null;
  }
  return plannerState.studentsById[studentId]?.display_name ?? null;
});
const pendingFixedSeatSeatLabel = computed(() => {
  const seatId = plannerState.pendingFixedSeatSeatId;
  return seatId ? formatSeatDisplayLabel(seatId) : null;
});
const pendingSelectionCount = computed(() => {
  if (plannerState.activeSeatingSmartTool === "fixed_seat") {
    return Number(plannerState.pendingFixedSeatStudentId !== null)
      + Number(plannerState.pendingFixedSeatSeatId !== null);
  }
  return plannerState.pendingRelationshipStudentIds.length;
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
const phoneCanCommitRelationshipRule = computed(() => {
  return (
    plannerState.activeSeatingSmartTool !== "fixed_seat"
    && plannerState.activeSeatingSmartTool !== null
  );
});
const canUseClassroomView = computed(() => plannerState.template !== null);
const seatingArrangementUnavailableMessage = computed(() => {
  if (plannerState.template === null) {
    return "Klassrumsvyn blir tillgänglig när klassen har ett klassrum.";
  }
  return null;
});
const phoneToolRows = computed(() => [
  {
    id: "near_teacher" as const,
    label: "Nära läraren",
    subtitle: "Placera elever nära katedern.",
    icon: IconTeacherAnchor,
  },
  {
    id: "fixed_seat" as const,
    label: "Fast plats",
    subtitle: "Lås en elev till en plats.",
    icon: IconLock,
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

function activateFixedSeatTool(): void {
  fixedSeatSwitchPromptOpen.value = false;
  mapView.value = "seating_arrangement";
  plannerState.setActiveSeatingSmartTool("fixed_seat");
}

function selectTool(tool: "near_teacher" | "keep_near" | "keep_apart" | "fixed_seat"): void {
  if (tool === "fixed_seat") {
    if (!canUseClassroomView.value) {
      return;
    }
    if (mapView.value === "planning_map") {
      fixedSeatSwitchPromptOpen.value = true;
      return;
    }
    plannerState.setActiveSeatingSmartTool(tool);
    return;
  }
  if (tool === "near_teacher") {
    fixedSeatSwitchPromptOpen.value = false;
    plannerState.beginNearTeacherEdit();
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

watch(canUseClassroomView, (nextValue) => {
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
        v-if="phoneCanCommitRelationshipRule"
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
            @clear-selection="plannerState.clearPendingRelationshipSelection()"
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
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          @update:map-view="mapView = $event"
          @student-selected="emit('student-selected', $event)"
          @seat-selected="plannerState.selectFixedSeatRuleSeat($event)"
        />
      </div>
    </div>
  </div>
</template>
