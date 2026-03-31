<script setup lang="ts">
/**
 * Rules-workspace summary panel.
 *
 * This component lists the active rules in one compact top panel above the
 * map. It intentionally avoids owning the transient rule-creation flow so the
 * tool rail can stay authoritative for selection, confirmation, and feedback.
 */

import { computed } from "vue";

import { IconSettings, IconTrash } from "../../../components/icons";
import type { RelationshipRule, Student } from "../classroomPlannerTypes";
import {
  formatRelationshipRuleHeading,
  resolveStudentNames,
  sortStudentsAlphabetically,
} from "../classroomPlannerSmartRulePresentation";

const props = withDefaults(defineProps<{
  nearTeacherStudents?: Student[];
  relationshipRules?: RelationshipRule[];
  studentsById?: Record<string, Student | undefined>;
  editingRelationshipRuleId?: string | null;
  editingNearTeacherRule?: boolean;
  canEdit?: boolean;
}>(), {
  nearTeacherStudents: () => [],
  relationshipRules: () => [],
  studentsById: () => ({}),
  editingRelationshipRuleId: null,
  editingNearTeacherRule: false,
  canEdit: false,
});

const emit = defineEmits<{
  (e: "edit-near-teacher"): void;
  (e: "delete-near-teacher"): void;
  (e: "edit-rule", ruleId: string): void;
  (e: "delete-rule", ruleId: string): void;
}>();

const nearTeacherStudentNames = computed(() => {
  return sortStudentsAlphabetically(props.nearTeacherStudents).map((student) => student.display_name);
});

function relationshipRuleHeading(rule: RelationshipRule, index: number): string {
  return formatRelationshipRuleHeading(rule, index);
}
</script>

<template>
  <section
    class="planner-rules-summary-panel"
    aria-label="Aktiva regler"
    data-test="rules-summary-panel"
  >
    <p class="border-b border-navy/20 pb-2.5 text-sm text-navy/70">
      Reglerna gäller hela klassen och sparas gemensamt.
    </p>

    <div
      class="planner-rules-summary-cards"
      data-test="rules-active-cards"
    >
      <div
        v-if="nearTeacherStudents.length === 0 && relationshipRules.length === 0"
        class="flex min-h-full w-full items-center border border-dashed border-navy/20 bg-white px-3 py-3 text-sm text-navy/55"
        data-test="rules-summary-empty-state"
      >
        Inga smarta regler ännu.
      </div>

      <div
        v-if="nearTeacherStudentNames.length > 0"
        class="planner-rules-summary-card"
        :class="editingNearTeacherRule ? 'planner-rules-summary-card-editing' : ''"
        data-test="rules-active-card"
      >
        <p class="text-sm font-semibold text-navy">
          Nära läraren
        </p>
        <p class="mt-1 text-sm text-navy/70">
          {{ nearTeacherStudentNames.join(", ") }}
        </p>

        <div class="mt-3 flex items-center gap-1.5">
          <button
            type="button"
            class="btn-ghost planner-btn-ghost planner-btn-icon-sm"
            data-test="rules-edit-near-teacher-0"
            :disabled="!canEdit"
            aria-label="Redigera regeln Nära läraren"
            @click="emit('edit-near-teacher')"
          >
            <IconSettings :size="14" />
          </button>
          <button
            type="button"
            class="btn-ghost planner-btn-danger-soft planner-btn-icon-sm"
            data-test="rules-delete-near-teacher-0"
            :disabled="!canEdit"
            aria-label="Ta bort regeln Nära läraren"
            @click="emit('delete-near-teacher')"
          >
            <IconTrash :size="14" />
          </button>
        </div>
      </div>

      <div
        v-for="(rule, index) in relationshipRules"
        :key="rule.id"
        class="planner-rules-summary-card"
        :class="
          editingRelationshipRuleId === rule.id
            ? 'planner-rules-summary-card-editing'
            : ''
        "
        data-test="rules-active-card"
      >
        <p class="text-sm font-semibold text-navy">
          {{ relationshipRuleHeading(rule, index) }}
        </p>
        <p class="mt-1 text-sm text-navy/70">
          {{ resolveStudentNames(rule.student_ids, props.studentsById).join(", ") }}
        </p>

        <div class="mt-3 flex items-center gap-1.5">
          <button
            type="button"
            class="btn-ghost planner-btn-ghost planner-btn-icon-sm"
            :data-test="`rules-edit-rule-${index}`"
            :disabled="!canEdit"
            :aria-label="`Redigera ${relationshipRuleHeading(rule, index)}`"
            @click="emit('edit-rule', rule.id)"
          >
            <IconSettings :size="14" />
          </button>
          <button
            type="button"
            class="btn-ghost planner-btn-danger-soft planner-btn-icon-sm"
            :data-test="`rules-delete-rule-${index}`"
            :disabled="!canEdit"
            :aria-label="`Ta bort ${relationshipRuleHeading(rule, index)}`"
            @click="emit('delete-rule', rule.id)"
          >
            <IconTrash :size="14" />
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
