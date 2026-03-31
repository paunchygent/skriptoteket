<script setup lang="ts">
/**
 * Rules-workspace tool rail.
 *
 * This component keeps the active smart-rule tool obvious through icon-first
 * buttons and a dedicated clear-selection affordance.
 */

import { computed } from "vue";

import {
  IconBan,
  IconLink2,
  IconSchool,
  IconX,
} from "../../../components/icons";
import type { SeatingSmartTool } from "../classroomPlannerTypes";

const props = withDefaults(defineProps<{
  activeTool: SeatingSmartTool | null;
  canEdit?: boolean;
  pendingSelectionCount?: number;
  pendingStudents?: Array<{ id: string; name: string }>;
  editingRelationshipRuleId?: string | null;
  editingNearTeacherRule?: boolean;
  canCommitPendingRelationshipRule?: boolean;
  feedbackMessage?: string | null;
}>(), {
  canEdit: false,
  pendingSelectionCount: 0,
  pendingStudents: () => [],
  editingRelationshipRuleId: null,
  editingNearTeacherRule: false,
  canCommitPendingRelationshipRule: false,
  feedbackMessage: null,
});

const emit = defineEmits<{
  (e: "select-tool", tool: SeatingSmartTool): void;
  (e: "clear-selection"): void;
  (e: "remove-pending-student", studentId: string): void;
  (e: "commit-pending"): void;
}>();

const toolButtons = computed(() => [
  {
    id: "near_teacher",
    label: "Nära läraren",
    icon: IconSchool,
  },
  {
    id: "keep_apart",
    label: "Håll isär",
    icon: IconBan,
  },
  {
    id: "keep_near",
    label: "Håll nära",
    icon: IconLink2,
  },
] satisfies Array<{
  id: SeatingSmartTool;
  label: string;
  icon: typeof IconSchool;
}>);
const relationToolActive = computed(() => {
  return props.activeTool === "keep_near" || props.activeTool === "keep_apart";
});
const nearTeacherToolActive = computed(() => props.activeTool === "near_teacher");
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
</script>

<template>
  <aside
    class="planner-tool-rail flex h-full flex-col"
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

    <div class="planner-tool-rail-section">
      <template v-if="hasPendingFlow">
        <p class="planner-tool-rail-meta">
          {{ `${pendingHeading} · ${pendingSelectionLabel}` }}
        </p>

        <div
          v-if="feedbackMessage"
          class="mt-2 border border-burgundy/30 bg-burgundy/10 px-2.5 py-2 text-xs font-semibold text-burgundy"
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
                class="planner-row-remove-button inline-flex h-5 w-5 items-center justify-center rounded-[4px] border border-transparent hover:border-burgundy/20 hover:bg-burgundy/5"
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

          <button
            type="button"
            class="btn-primary planner-btn-primary-sm w-full"
            data-test="rules-commit-rule"
            :disabled="!canCommitPendingRelationshipRule"
            @click="emit('commit-pending')"
          >
            {{ pendingActionLabel }}
          </button>
        </div>
      </template>

      <template v-else>
        <p class="planner-tool-rail-meta">
          {{ pendingSelectionCount }} valda
        </p>
      </template>

      <button
        type="button"
        class="btn-ghost planner-btn-ghost planner-btn-ghost-sm mt-2.5 w-full"
        data-test="rules-clear-selection"
        :disabled="pendingSelectionCount === 0"
        @click="emit('clear-selection')"
      >
        Rensa markering
      </button>
    </div>
  </aside>
</template>
