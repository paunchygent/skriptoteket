<script setup lang="ts">
/**
 * Seating smart-rule surface.
 *
 * This component renders the first visible teacher-facing smart-rule workflow
 * for seating: one active tool at a time, explicit relation commits, overlap
 * feedback, and a main-surface summary of active unary and relationship rules.
 */

import { computed } from "vue";

import type { RelationshipRule, SeatingSmartTool, Student } from "../classroomPlannerTypes";
import { useClassroomState } from "../useClassroomState";

const plannerState = useClassroomState();

const smartRunEnabled = computed(() => (plannerState.draft?.smart_enabled ?? false) === true);
const canEditSmartRules = computed(() => plannerState.canEditSeatingSmartRules);
const pendingRelationToolActive = computed(() => {
  return (
    plannerState.activeSeatingSmartTool === "keep_near"
    || plannerState.activeSeatingSmartTool === "keep_apart"
  );
});
const pendingStudentCount = computed(() => plannerState.pendingRelationshipStudentIds.length);
const nearTeacherStudents = computed<Student[]>(() => {
  return plannerState.seatingPreferences
    .filter((preference) => preference.near_teacher === true)
    .map((preference) => plannerState.studentsById[preference.student_id] ?? null)
    .filter((student): student is Student => student !== null);
});

function relationRuleHeading(rule: RelationshipRule, index: number): string {
  const suffix = String.fromCharCode(65 + index);
  return `${rule.kind === "keep_apart" ? "Håll isär" : "Håll nära"} ${suffix}`;
}

function relationRuleStudents(rule: RelationshipRule): Student[] {
  return rule.student_ids
    .map((studentId) => plannerState.studentsById[studentId] ?? null)
    .filter((student): student is Student => student !== null);
}

function toggleTool(tool: SeatingSmartTool): void {
  plannerState.setActiveSeatingSmartTool(tool);
}
</script>

<template>
  <section
    class="border border-navy bg-white p-4 shadow-brutal-sm"
    data-test="seating-smart-rule-surface"
  >
    <div class="flex flex-col gap-2 border-b border-navy/20 pb-3">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Smart placering
          </p>
          <h3 class="font-serif text-xl text-navy">
            Regler i sittschemat
          </h3>
        </div>
        <span
          class="border px-2 py-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)]"
          :class="smartRunEnabled ? 'border-navy bg-canvas text-navy/70' : 'border-navy/25 bg-white text-navy/40'"
        >
          {{ smartRunEnabled ? "Smart slumpa: På" : "Smart slumpa: Av" }}
        </span>
      </div>
      <p class="max-w-[56rem] text-sm leading-relaxed text-navy/70">
        Välj ett verktyg och klicka direkt i klassöversikten. Närmare läraren växlar direkt,
        medan Håll isär och Håll nära byggs upp som en tillfällig elevmarkering innan du skapar regeln.
      </p>
    </div>

    <div class="mt-4 flex flex-wrap items-center gap-2">
      <button
        type="button"
        class="btn-ghost border-navy/30 bg-white shadow-none"
        :class="plannerState.activeSeatingSmartTool === 'near_teacher' ? 'border-burgundy bg-burgundy/10 text-burgundy' : ''"
        data-test="seating-smart-tool-near-teacher"
        :disabled="!canEditSmartRules"
        @click="toggleTool('near_teacher')"
      >
        Närmare läraren
      </button>
      <button
        type="button"
        class="btn-ghost border-navy/30 bg-white shadow-none"
        :class="plannerState.activeSeatingSmartTool === 'keep_apart' ? 'border-burgundy bg-burgundy/10 text-burgundy' : ''"
        data-test="seating-smart-tool-keep-apart"
        :disabled="!canEditSmartRules"
        @click="toggleTool('keep_apart')"
      >
        Håll isär
      </button>
      <button
        type="button"
        class="btn-ghost border-navy/30 bg-white shadow-none"
        :class="plannerState.activeSeatingSmartTool === 'keep_near' ? 'border-burgundy bg-burgundy/10 text-burgundy' : ''"
        data-test="seating-smart-tool-keep-near"
        :disabled="!canEditSmartRules"
        @click="toggleTool('keep_near')"
      >
        Håll nära
      </button>
      <button
        type="button"
        class="btn-ghost border-navy/30 bg-white shadow-none"
        data-test="seating-smart-clear-selection"
        :disabled="plannerState.pendingRelationshipStudentIds.length === 0"
        @click="plannerState.clearPendingRelationshipSelection()"
      >
        Rensa markering
      </button>
      <div
        v-if="pendingRelationToolActive"
        class="ml-auto flex flex-wrap items-center gap-2"
      >
        <span
          class="border border-navy/20 bg-canvas px-2 py-1 text-[11px] font-semibold text-navy/70"
          data-test="seating-smart-pending-count"
        >
          {{ pendingStudentCount }} valda
        </span>
        <button
          type="button"
          class="btn-primary px-3 py-1.5"
          data-test="seating-smart-commit-rule"
          :disabled="!plannerState.canCommitPendingRelationshipRule"
          @click="plannerState.commitPendingRelationshipRule()"
        >
          Skapa regel
        </button>
      </div>
    </div>

    <p
      v-if="plannerState.smartRuleFeedbackMessage"
      class="mt-3 border border-burgundy/30 bg-burgundy/10 px-3 py-2 text-sm font-semibold text-burgundy"
      data-test="seating-smart-feedback"
    >
      {{ plannerState.smartRuleFeedbackMessage }}
    </p>

    <div class="mt-4 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h4 class="text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Aktiva regler
        </h4>
        <span class="text-xs text-navy/50">
          {{ nearTeacherStudents.length + plannerState.relationshipRules.length }} totalt
        </span>
      </div>

      <div
        v-if="nearTeacherStudents.length === 0 && plannerState.relationshipRules.length === 0"
        class="border border-dashed border-navy/20 bg-canvas px-4 py-3 text-sm text-navy/55"
      >
        Inga smarta regler ännu. Välj ett verktyg och markera elever direkt i sittschemat.
      </div>

      <div
        v-if="nearTeacherStudents.length > 0"
        class="flex flex-wrap items-start justify-between gap-3 border border-navy/20 bg-canvas px-3 py-3"
      >
        <div>
          <p class="text-sm font-semibold text-navy">
            Närmare läraren
          </p>
          <p class="mt-1 text-sm text-navy/70">
            {{ nearTeacherStudents.map((student) => student.display_name).join(", ") }}
          </p>
        </div>
      </div>

      <div
        v-for="(rule, index) in plannerState.relationshipRules"
        :key="rule.id"
        class="flex flex-wrap items-start justify-between gap-3 border border-navy/20 bg-white px-3 py-3"
      >
        <div>
          <p class="text-sm font-semibold text-navy">
            {{ relationRuleHeading(rule, index) }}
          </p>
          <p class="mt-1 text-sm text-navy/70">
            {{ relationRuleStudents(rule).map((student) => student.display_name).join(", ") }}
          </p>
        </div>
        <button
          type="button"
          class="btn-ghost border-navy/30 bg-white px-3 py-1.5 shadow-none"
          :data-test="`seating-smart-delete-rule-${index}`"
          :disabled="!canEditSmartRules"
          @click="plannerState.deleteRelationshipRule(rule.id)"
        >
          Ta bort
        </button>
      </div>
    </div>
  </section>
</template>
