<script setup lang="ts">
/**
 * Rules-workspace tool rail.
 *
 * Purpose:
 *   Renders compact smart-rule tools, pending selections, confirmation
 *   actions, and feedback for the rules workspace.
 *
 * Relationships:
 *   - rendered by `PlannerRulesWorkspacePane.vue`
 *   - receives derived authoring state from the planner store
 *   - emits selection and commit intents back to the workspace
 */

import { computed } from "vue";

import {
  IconKeepApart,
  IconKeepNear,
  IconLink2,
  IconLock,
  IconTeacherAnchor,
  IconX,
} from "../../../components/icons";
import type { SeatingSmartTool } from "../classroomPlannerTypes";

const props = withDefaults(defineProps<{
  activeTool: SeatingSmartTool | null;
  canEdit?: boolean;
  pendingSelectionCount?: number;
  pendingStudents?: Array<{ id: string; name: string }>;
  pendingFixedSeatStudentName?: string | null;
  pendingFixedSeatSeatLabel?: string | null;
  editingRelationshipRuleId?: string | null;
  editingFixedSeatRuleId?: string | null;
  editingNearTeacherRule?: boolean;
  canCommitPendingRelationshipRule?: boolean;
  canCommitPendingFixedSeatRule?: boolean;
  feedbackMessage?: string | null;
}>(), {
  canEdit: false,
  pendingSelectionCount: 0,
  pendingStudents: () => [],
  pendingFixedSeatStudentName: null,
  pendingFixedSeatSeatLabel: null,
  editingRelationshipRuleId: null,
  editingFixedSeatRuleId: null,
  editingNearTeacherRule: false,
  canCommitPendingRelationshipRule: false,
  canCommitPendingFixedSeatRule: false,
  feedbackMessage: null,
});

const emit = defineEmits<{
  (e: "select-tool", tool: SeatingSmartTool): void;
  (e: "clear-selection"): void;
  (e: "remove-pending-student", studentId: string): void;
  (e: "commit-pending"): void;
  (e: "commit-fixed-seat"): void;
}>();

const toolButtons = computed(() => [
  {
    id: "near_teacher",
    label: "Nära läraren",
    icon: IconTeacherAnchor,
  },
  {
    id: "fixed_seat",
    label: "Fast plats",
    icon: IconLock,
  },
  {
    id: "keep_apart",
    label: "Håll isär",
    icon: IconKeepApart,
  },
  {
    id: "keep_near",
    label: "Håll nära",
    icon: IconKeepNear,
  },
] satisfies Array<{
  id: SeatingSmartTool;
  label: string;
  icon: typeof IconTeacherAnchor;
}>);
const relationToolActive = computed(() => {
  return props.activeTool === "keep_near" || props.activeTool === "keep_apart";
});
const nearTeacherToolActive = computed(() => props.activeTool === "near_teacher");
const fixedSeatToolActive = computed(() => props.activeTool === "fixed_seat");
const hasPendingFlow = computed(() => {
  return relationToolActive.value || nearTeacherToolActive.value;
});
const pendingHeading = computed(() => {
  return props.editingRelationshipRuleId || props.editingNearTeacherRule
    ? "Redigerar regel"
    : "Pågående regel";
});
const pendingSelectionLabel = computed(() => {
  return props.pendingSelectionCount === 1 ? "1 vald" : `${props.pendingSelectionCount} valda`;
});
const pendingHelpText = computed(() => {
  if (nearTeacherToolActive.value) {
    return "Välj minst en elev på kartan.";
  }
  return "Välj minst två elever på kartan.";
});
const pendingActionLabel = computed(() => {
  return props.editingRelationshipRuleId || props.editingNearTeacherRule
    ? "Spara regel"
    : "Skapa regel";
});
const fixedSeatHeading = computed(() => {
  return props.editingFixedSeatRuleId ? "Redigerar fast plats" : "Pågående fast plats";
});
const fixedSeatHelpText = computed(() => {
  if (!props.pendingFixedSeatStudentName) {
    return "Välj en elev på kartan.";
  }
  if (!props.pendingFixedSeatSeatLabel) {
    return "Välj elevens fasta plats i klassrumsvyn.";
  }
  return props.editingFixedSeatRuleId
    ? "Spara regel uppdaterar den fasta platsen."
    : "Skapa regel låser eleven till platsen.";
});
const fixedSeatActionLabel = computed(() => {
  return props.editingFixedSeatRuleId ? "Spara regel" : "Skapa regel";
});
</script>

<template>
  <aside
    class="planner-tool-rail planner-rules-tool-lane flex flex-col"
    aria-label="Regelverktyg"
    data-test="rules-tool-rail"
  >
    <div class="planner-tool-rail-stack">
      <button
        v-for="tool in toolButtons"
        :key="tool.id"
        type="button"
        class="planner-tool-rail-action"
        :class="
          activeTool === tool.id
            ? 'planner-choice-button-active'
            : 'planner-choice-button-idle'
        "
        :data-test="`rules-tool-${tool.id}`"
        :disabled="!canEdit"
        @click="emit('select-tool', tool.id)"
      >
        <component
          :is="tool.icon"
          :size="16"
        />
        <span class="leading-none">
          {{ tool.label }}
        </span>
      </button>
    </div>

    <div class="planner-tool-rail-section flex flex-1 flex-col">
      <template v-if="hasPendingFlow">
        <div class="planner-tool-rail-state">
          <p class="planner-tool-rail-meta">
            {{ `${pendingHeading} · ${pendingSelectionLabel}` }}
          </p>

          <div
            v-if="feedbackMessage"
            class="mt-2 border border-warning/30 bg-warning/10 px-2.5 py-2 text-xs font-semibold text-warning"
            data-test="rules-feedback"
          >
            {{ feedbackMessage }}
          </div>

          <div
            class="mt-2 space-y-2"
            data-test="rules-pending-panel"
          >
            <div
              v-if="pendingStudents.length > 0"
              class="flex flex-wrap gap-1.5"
            >
              <div
                v-for="student in pendingStudents"
                :key="student.id"
                class="inline-flex h-[26px] items-center gap-1 border border-navy/20 bg-white pl-2 pr-1 text-[11px] font-semibold text-navy"
                data-test="rules-pending-student-chip"
              >
                <span class="min-w-0 truncate">{{ student.name }}</span>
                <button
                  type="button"
                  class="planner-row-remove-button inline-flex h-5 w-5 items-center justify-center rounded-[4px] border border-transparent hover:border-critical/20 hover:bg-critical/5"
                  :aria-label="`Ta bort ${student.name} från regeln`"
                  @click="emit('remove-pending-student', student.id)"
                >
                  <IconX :size="12" />
                </button>
              </div>
            </div>
            <p
              v-else
              class="text-xs leading-relaxed text-navy/70"
            >
              {{ pendingHelpText }}
            </p>
          </div>
        </div>
      </template>

      <template v-else-if="fixedSeatToolActive">
        <div class="planner-tool-rail-state">
          <p class="planner-tool-rail-meta">
            {{ fixedSeatHeading }}
          </p>

          <div
            v-if="feedbackMessage"
            class="mt-2 border border-warning/30 bg-warning/10 px-2.5 py-2 text-xs font-semibold text-warning"
            data-test="rules-feedback"
          >
            {{ feedbackMessage }}
          </div>

          <div
            class="mt-2 space-y-2"
            data-test="rules-fixed-seat-panel"
          >
            <div
              v-if="pendingFixedSeatStudentName || pendingFixedSeatSeatLabel"
              class="grid w-full gap-1"
              data-test="rules-fixed-seat-pending-binding"
            >
              <span
                class="inline-flex min-h-[28px] w-full items-center border border-navy/20 bg-white px-2 text-[11px] font-semibold text-navy"
                data-test="rules-fixed-seat-pending-student"
              >
                <span class="min-w-0 truncate">
                  {{ pendingFixedSeatStudentName ?? "Välj elev" }}
                </span>
              </span>

              <span
                class="flex h-5 items-center justify-center text-action"
                data-test="rules-fixed-seat-pending-link"
              >
                <IconLink2 :size="14" />
              </span>

              <span
                class="inline-flex min-h-[28px] w-full items-center border border-navy/20 bg-white px-2 text-[11px] font-semibold text-navy"
                data-test="rules-fixed-seat-pending-seat"
              >
                <span class="min-w-0 truncate">
                  {{ pendingFixedSeatSeatLabel ?? "välj plats" }}
                </span>
              </span>
            </div>

            <p
              class="text-xs leading-relaxed text-navy/70"
              data-test="rules-fixed-seat-help"
            >
              {{ fixedSeatHelpText }}
            </p>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="planner-tool-rail-state">
          <p class="planner-tool-rail-meta">
            {{ pendingSelectionCount }} valda
          </p>
        </div>
      </template>

      <div
        class="planner-tool-rail-actions mt-auto grid gap-2 pt-2.5"
        data-test="rules-tool-rail-actions"
      >
        <button
          v-if="hasPendingFlow"
          type="button"
          class="btn-primary planner-btn-primary-sm w-full"
          data-test="rules-commit-rule"
          :disabled="!canCommitPendingRelationshipRule"
          @click="emit('commit-pending')"
        >
          {{ pendingActionLabel }}
        </button>

        <button
          v-else-if="fixedSeatToolActive"
          type="button"
          class="btn-primary planner-btn-primary-sm w-full"
          data-test="rules-commit-fixed-seat"
          :disabled="!canCommitPendingFixedSeatRule"
          @click="emit('commit-fixed-seat')"
        >
          {{ fixedSeatActionLabel }}
        </button>

        <button
          type="button"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-sm w-full"
          data-test="rules-clear-selection"
          :disabled="pendingSelectionCount === 0"
          @click="emit('clear-selection')"
        >
          Rensa markering
        </button>
      </div>
    </div>
  </aside>
</template>
