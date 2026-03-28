<script setup lang="ts">
/**
 * Rules-workspace inspector.
 *
 * This component keeps active rules, edit affordances, and the current
 * relation-rule commit surface visible in the main rules workspace instead of
 * moving authoring back into task-pane drawers.
 */

import { computed, ref, watch } from "vue";

import type { RelationshipRule, SeatingSmartTool, Student } from "../classroomPlannerTypes";
import {
  formatRelationshipRuleHeading,
  resolveStudentNames,
  sortStudentsAlphabetically,
} from "../classroomPlannerSmartRulePresentation";

const props = withDefaults(defineProps<{
  nearTeacherStudents?: Student[];
  relationshipRules?: RelationshipRule[];
  studentsById?: Record<string, Student | undefined>;
  pendingSelectedStudentIds?: string[];
  activeTool?: SeatingSmartTool | null;
  editingRelationshipRuleId?: string | null;
  canCommitPendingRelationshipRule?: boolean;
  canEdit?: boolean;
  feedbackMessage?: string | null;
}>(), {
  nearTeacherStudents: () => [],
  relationshipRules: () => [],
  studentsById: () => ({}),
  pendingSelectedStudentIds: () => [],
  activeTool: null,
  editingRelationshipRuleId: null,
  canCommitPendingRelationshipRule: false,
  canEdit: false,
  feedbackMessage: null,
});

const emit = defineEmits<{
  (e: "replace-near-teacher", payload: { previousStudentId: string; nextStudentId: string }): void;
  (e: "remove-near-teacher", studentId: string): void;
  (e: "edit-rule", ruleId: string): void;
  (e: "delete-rule", ruleId: string): void;
  (e: "commit-pending"): void;
  (e: "clear-selection"): void;
}>();

const editingNearTeacherStudentId = ref<string | null>(null);
const pendingNearTeacherStudentId = ref<string>("");
const relationToolActive = computed(() => {
  return props.activeTool === "keep_near" || props.activeTool === "keep_apart";
});
const pendingStudentNames = computed(() => {
  return resolveStudentNames(props.pendingSelectedStudentIds, props.studentsById);
});
const commitLabel = computed(() => {
  return props.editingRelationshipRuleId ? "Spara regel" : "Skapa regel";
});
const editableStudents = computed<Student[]>(() => {
  return sortStudentsAlphabetically(
    Object.values(props.studentsById).filter((student): student is Student => student !== undefined),
  );
});

function relationshipRuleLabel(rule: RelationshipRule, index: number): string {
  return `${formatRelationshipRuleHeading(rule, index)}: ${resolveStudentNames(rule.student_ids, props.studentsById).join(", ")}`;
}

function beginNearTeacherEdit(studentId: string): void {
  editingNearTeacherStudentId.value = studentId;
  pendingNearTeacherStudentId.value = studentId;
}

function cancelNearTeacherEdit(): void {
  editingNearTeacherStudentId.value = null;
  pendingNearTeacherStudentId.value = "";
}

function nearTeacherOptions(studentId: string): Student[] {
  const occupiedStudentIds = new Set(props.nearTeacherStudents.map((student) => student.id));
  return editableStudents.value.filter((student) => {
    return student.id === studentId || !occupiedStudentIds.has(student.id);
  });
}

function saveNearTeacherEdit(previousStudentId: string): void {
  const nextStudentId = pendingNearTeacherStudentId.value.trim();
  if (nextStudentId.length === 0 || nextStudentId === previousStudentId) {
    cancelNearTeacherEdit();
    return;
  }

  emit("replace-near-teacher", { previousStudentId, nextStudentId });
  cancelNearTeacherEdit();
}

watch(
  () => props.nearTeacherStudents.map((student) => student.id).join("|"),
  () => {
    if (
      editingNearTeacherStudentId.value
      && !props.nearTeacherStudents.some((student) => student.id === editingNearTeacherStudentId.value)
    ) {
      cancelNearTeacherEdit();
    }
  },
);
</script>

<template>
  <aside class="space-y-3">
    <section class="border border-navy bg-white p-4 shadow-brutal-sm">
      <div class="space-y-1 border-b border-navy/20 pb-3">
        <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Inspektör
        </p>
        <p class="text-sm text-navy/70">
          Reglerna är gemensamma för klassen och sparas direkt för hela rosteren.
        </p>
      </div>

      <div
        v-if="feedbackMessage"
        class="mt-3 border border-burgundy/30 bg-burgundy/10 px-3 py-2 text-sm font-semibold text-burgundy"
        data-test="rules-feedback"
      >
        {{ feedbackMessage }}
      </div>

      <div
        v-if="relationToolActive || pendingStudentNames.length > 0"
        class="mt-3 border border-navy/20 bg-canvas px-3 py-3"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-navy">
              {{ editingRelationshipRuleId ? "Redigerar regel" : "Pågående regel" }}
            </p>
            <p class="mt-1 text-sm text-navy/70">
              {{ pendingStudentNames.length > 0 ? pendingStudentNames.join(", ") : "Välj minst två elever." }}
            </p>
          </div>
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-white px-3 py-1.5 shadow-none"
            :disabled="pendingStudentNames.length === 0"
            @click="emit('clear-selection')"
          >
            Rensa
          </button>
        </div>

        <button
          type="button"
          class="btn-primary mt-3 w-full px-3 py-1.5"
          data-test="rules-commit-rule"
          :disabled="!canCommitPendingRelationshipRule"
          @click="emit('commit-pending')"
        >
          {{ commitLabel }}
        </button>
      </div>

      <div
        v-if="activeTool === 'near_teacher'"
        class="mt-3 border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy/70"
      >
        Klicka på en elev på kartan för att lägga till eller ta bort regeln Närmare läraren direkt.
      </div>

      <div class="mt-4 space-y-3">
        <div class="flex items-center justify-between gap-3">
          <h4 class="text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Aktiva regler
          </h4>
          <span class="text-xs text-navy/50">
            {{ nearTeacherStudents.length + relationshipRules.length }} totalt
          </span>
        </div>

        <div
          v-if="nearTeacherStudents.length === 0 && relationshipRules.length === 0"
          class="border border-dashed border-navy/20 bg-white px-3 py-3 text-sm text-navy/55"
        >
          Inga smarta regler ännu.
        </div>

        <div
          v-for="(student, index) in nearTeacherStudents"
          :key="student.id"
          class="border px-3 py-3"
          :class="
            editingNearTeacherStudentId === student.id
              ? 'border-burgundy bg-burgundy/5'
              : 'border-navy/20 bg-canvas'
          "
        >
          <p class="text-sm font-semibold text-navy">
            Närmare läraren
          </p>

          <div v-if="editingNearTeacherStudentId === student.id">
            <label class="mt-3 block space-y-1">
              <span class="block text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                Elev
              </span>
              <select
                v-model="pendingNearTeacherStudentId"
                class="w-full border border-navy/20 bg-white px-3 py-2 text-sm text-navy"
                :disabled="!canEdit"
                :data-test="`rules-near-teacher-select-${index}`"
              >
                <option
                  v-for="option in nearTeacherOptions(student.id)"
                  :key="option.id"
                  :value="option.id"
                >
                  {{ option.display_name }}
                </option>
              </select>
            </label>

            <div class="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                class="btn-ghost border-navy/30 bg-white px-3 py-1.5 shadow-none"
                :disabled="!canEdit"
                @click="cancelNearTeacherEdit()"
              >
                Avbryt
              </button>
              <button
                type="button"
                class="btn-primary px-3 py-1.5"
                :disabled="!canEdit || pendingNearTeacherStudentId === student.id"
                :data-test="`rules-save-near-teacher-${index}`"
                @click="saveNearTeacherEdit(student.id)"
              >
                Spara regel
              </button>
            </div>
          </div>

          <template v-else>
            <p class="mt-1 text-sm text-navy/70">
              {{ student.display_name }}
            </p>

            <div class="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                class="btn-ghost border-navy/30 bg-white px-3 py-1.5 shadow-none"
                :data-test="`rules-edit-near-teacher-${index}`"
                :disabled="!canEdit"
                @click="beginNearTeacherEdit(student.id)"
              >
                Redigera
              </button>
              <button
                type="button"
                class="btn-ghost border-navy/30 bg-white px-3 py-1.5 shadow-none"
                :data-test="`rules-delete-near-teacher-${index}`"
                :disabled="!canEdit"
                @click="emit('remove-near-teacher', student.id)"
              >
                Ta bort
              </button>
            </div>
          </template>
        </div>

        <div
          v-for="(rule, index) in relationshipRules"
          :key="rule.id"
          class="border px-3 py-3"
          :class="
            editingRelationshipRuleId === rule.id
              ? 'border-burgundy bg-burgundy/5'
              : 'border-navy/20 bg-white'
          "
        >
          <p class="text-sm font-semibold text-navy">
            {{ relationshipRuleLabel(rule, index) }}
          </p>

          <div class="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              class="btn-ghost border-navy/30 bg-white px-3 py-1.5 shadow-none"
              :data-test="`rules-edit-rule-${index}`"
              :disabled="!canEdit"
              @click="emit('edit-rule', rule.id)"
            >
              Redigera
            </button>
            <button
              type="button"
              class="btn-ghost border-navy/30 bg-white px-3 py-1.5 shadow-none"
              :data-test="`rules-delete-rule-${index}`"
              :disabled="!canEdit"
              @click="emit('delete-rule', rule.id)"
            >
              Ta bort
            </button>
          </div>
        </div>
      </div>
    </section>
  </aside>
</template>
