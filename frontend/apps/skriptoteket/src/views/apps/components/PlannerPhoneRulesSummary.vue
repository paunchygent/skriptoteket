<script setup lang="ts">
/**
 * Phone active rules summary.
 *
 * Purpose:
 *   Presents persisted smart-rule management on the reduced phone `Regler`
 *   workspace without duplicating the desktop inspector or owning rule state.
 *
 * Relationships:
 *   - rendered by `PlannerRulesWorkspacePane.vue` only in the phone branch
 *   - mirrors `PlannerRulesInspector.vue` edit/delete events
 *   - labels rules through `classroomPlannerSmartRulePresentation.ts`
 */

import { computed, ref } from "vue";

import {
  IconArrow,
  IconEdit,
  IconKeepApart,
  IconKeepNear,
  IconLock,
  IconTeacherAnchor,
  IconTrash,
} from "../../../components/icons";
import type { FixedSeatRule, RelationshipRule, Student } from "../classroomPlannerTypes";
import {
  formatRelationshipRuleHeading,
  formatSeatDisplayLabel,
  resolveStudentNames,
  sortStudentsAlphabetically,
} from "../classroomPlannerSmartRulePresentation";

const props = withDefaults(defineProps<{
  nearTeacherStudents?: Student[];
  relationshipRules?: RelationshipRule[];
  fixedSeatRules?: FixedSeatRule[];
  studentsById?: Record<string, Student | undefined>;
  editingRelationshipRuleId?: string | null;
  editingFixedSeatRuleId?: string | null;
  editingNearTeacherRule?: boolean;
  canEdit?: boolean;
}>(), {
  nearTeacherStudents: () => [],
  relationshipRules: () => [],
  fixedSeatRules: () => [],
  studentsById: () => ({}),
  editingRelationshipRuleId: null,
  editingFixedSeatRuleId: null,
  editingNearTeacherRule: false,
  canEdit: false,
});

const emit = defineEmits<{
  (e: "edit-near-teacher"): void;
  (e: "delete-near-teacher"): void;
  (e: "edit-rule", ruleId: string): void;
  (e: "delete-rule", ruleId: string): void;
  (e: "edit-fixed-seat-rule", ruleId: string): void;
  (e: "delete-fixed-seat-rule", ruleId: string): void;
}>();

const isExpanded = ref(true);

const nearTeacherStudentNames = computed(() => {
  return sortStudentsAlphabetically(props.nearTeacherStudents).map((student) => student.display_name);
});
const ruleCount = computed(() => (
  props.fixedSeatRules.length
  + props.relationshipRules.length
  + (nearTeacherStudentNames.value.length > 0 ? 1 : 0)
));

function relationshipRuleHeading(rule: RelationshipRule, index: number): string {
  return formatRelationshipRuleHeading(rule, index);
}

function relationshipRuleNames(rule: RelationshipRule): string {
  return resolveStudentNames(rule.student_ids, props.studentsById).join(", ");
}

function fixedSeatRuleHeading(rule: FixedSeatRule): string {
  const studentName = props.studentsById[rule.student_id]?.display_name ?? "Elev";
  return `${studentName} -> ${formatSeatDisplayLabel(rule.seat_id)}`;
}
</script>

<template>
  <section
    v-if="ruleCount > 0"
    class="planner-phone-rules-summary"
    data-test="phone-rules-active-summary"
  >
    <button
      type="button"
      class="planner-phone-rules-summary-toggle"
      data-test="phone-rules-active-summary-toggle"
      :aria-expanded="isExpanded"
      @click="isExpanded = !isExpanded"
    >
      <span>Aktiva regler</span>
      <span
        class="planner-phone-rules-summary-count"
        data-test="phone-rules-active-count"
      >
        {{ ruleCount }}
      </span>
      <IconArrow
        :size="15"
        :direction="isExpanded ? 'up' : 'down'"
      />
    </button>

    <div
      v-if="isExpanded"
      class="planner-phone-rules-active-list"
      data-test="phone-rules-active-list"
    >
      <div
        v-for="rule in fixedSeatRules"
        :key="rule.id"
        class="planner-phone-rules-active-row"
        :class="editingFixedSeatRuleId === rule.id ? 'planner-phone-rules-active-row-editing' : ''"
        data-test="phone-rules-active-row-fixed-seat"
      >
        <IconLock
          :size="18"
          class="planner-phone-rules-active-icon"
        />
        <div class="min-w-0 flex-1">
          <p class="planner-phone-rules-active-label">
            Fast plats
          </p>
          <p class="planner-phone-rules-active-target">
            {{ fixedSeatRuleHeading(rule) }}
          </p>
        </div>
        <div class="planner-phone-rules-active-actions">
          <button
            type="button"
            class="planner-phone-rule-action-button"
            :data-test="`phone-rules-edit-fixed-seat-${rule.id}`"
            :disabled="!canEdit"
            :aria-label="`Redigera fast plats ${fixedSeatRuleHeading(rule)}`"
            @click="emit('edit-fixed-seat-rule', rule.id)"
          >
            <IconEdit :size="14" />
          </button>
          <button
            type="button"
            class="planner-phone-rule-action-button planner-phone-rule-action-button-danger"
            :data-test="`phone-rules-delete-fixed-seat-${rule.id}`"
            :disabled="!canEdit"
            :aria-label="`Ta bort fast plats ${fixedSeatRuleHeading(rule)}`"
            @click="emit('delete-fixed-seat-rule', rule.id)"
          >
            <IconTrash :size="14" />
          </button>
        </div>
      </div>

      <div
        v-if="nearTeacherStudentNames.length > 0"
        class="planner-phone-rules-active-row"
        :class="editingNearTeacherRule ? 'planner-phone-rules-active-row-editing' : ''"
        data-test="phone-rules-active-row-near-teacher"
      >
        <IconTeacherAnchor
          :size="18"
          class="planner-phone-rules-active-icon"
        />
        <div class="min-w-0 flex-1">
          <p class="planner-phone-rules-active-label">
            Nära läraren
          </p>
          <p class="planner-phone-rules-active-target">
            {{ nearTeacherStudentNames.join(", ") }}
          </p>
        </div>
        <div class="planner-phone-rules-active-actions">
          <button
            type="button"
            class="planner-phone-rule-action-button"
            data-test="phone-rules-edit-near-teacher"
            :disabled="!canEdit"
            aria-label="Redigera regeln Nära läraren"
            @click="emit('edit-near-teacher')"
          >
            <IconEdit :size="14" />
          </button>
          <button
            type="button"
            class="planner-phone-rule-action-button planner-phone-rule-action-button-danger"
            data-test="phone-rules-delete-near-teacher"
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
        class="planner-phone-rules-active-row"
        :class="editingRelationshipRuleId === rule.id ? 'planner-phone-rules-active-row-editing' : ''"
        data-test="phone-rules-active-row-relationship"
      >
        <IconKeepNear
          v-if="rule.kind === 'keep_near'"
          :size="18"
          class="planner-phone-rules-active-icon"
        />
        <IconKeepApart
          v-else
          :size="18"
          class="planner-phone-rules-active-icon"
        />
        <div class="min-w-0 flex-1">
          <p class="planner-phone-rules-active-label">
            {{ relationshipRuleHeading(rule, index) }}
          </p>
          <p class="planner-phone-rules-active-target">
            {{ relationshipRuleNames(rule) }}
          </p>
        </div>
        <div class="planner-phone-rules-active-actions">
          <button
            type="button"
            class="planner-phone-rule-action-button"
            :data-test="`phone-rules-edit-rule-${index}`"
            :disabled="!canEdit"
            :aria-label="`Redigera ${relationshipRuleHeading(rule, index)}`"
            @click="emit('edit-rule', rule.id)"
          >
            <IconEdit :size="14" />
          </button>
          <button
            type="button"
            class="planner-phone-rule-action-button planner-phone-rule-action-button-danger"
            :data-test="`phone-rules-delete-rule-${index}`"
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
