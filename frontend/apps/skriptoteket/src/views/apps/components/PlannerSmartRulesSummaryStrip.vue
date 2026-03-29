<script setup lang="ts">
/**
 * Compact smart-rule summary strip.
 *
 * This component keeps seating and grouping task panes calm by rendering a
 * read-only summary of shared smart rules while leaving authoring to the
 * dedicated `Regler` workspace.
 */

import { computed } from "vue";

import type { RelationshipRule, Student } from "../classroomPlannerTypes";
import {
  formatRelationshipRuleHeading,
  resolveStudentNames,
} from "../classroomPlannerSmartRulePresentation";

const props = withDefaults(defineProps<{
  emptyLabel?: string;
  nearTeacherStudents?: Student[];
  relationshipRules?: RelationshipRule[];
  studentsById?: Record<string, Student | undefined>;
}>(), {
  emptyLabel: "Inga regler ännu. Öppna Regler för att lägga till eller ändra dem.",
  nearTeacherStudents: () => [],
  relationshipRules: () => [],
  studentsById: () => ({}),
});

defineSlots<{
  controls?: () => unknown;
}>();

const totalRuleCount = computed(() => {
  return props.nearTeacherStudents.length + props.relationshipRules.length;
});

function relationshipRuleLabel(rule: RelationshipRule, index: number): string {
  const names = resolveStudentNames(rule.student_ids, props.studentsById);
  return `${formatRelationshipRuleHeading(rule, index)}: ${names.join(", ")}`;
}
</script>

<template>
  <section
    class="border border-navy/20 bg-white px-3 py-2.5 shadow-brutal-sm"
    aria-label="Aktiva regler"
  >
    <div class="flex flex-wrap items-start justify-between gap-3">
      <p class="text-sm text-navy/70">
        {{ totalRuleCount }} aktiva regler
      </p>

      <div
        v-if="$slots.controls"
        class="flex flex-wrap items-center justify-end gap-2"
      >
        <slot name="controls" />
      </div>
    </div>

    <div
      v-if="totalRuleCount === 0"
      class="mt-3 border border-dashed border-navy/20 bg-canvas px-3 py-2 text-sm text-navy/55"
    >
      {{ emptyLabel }}
    </div>

    <div
      v-else
      class="mt-3 flex flex-wrap gap-2"
    >
      <span
        v-if="nearTeacherStudents.length > 0"
        class="border border-navy/20 bg-canvas px-2 py-1 text-[11px] font-semibold text-navy/70"
      >
        Närmare läraren: {{ nearTeacherStudents.map((student) => student.display_name).join(", ") }}
      </span>

      <span
        v-for="(rule, index) in relationshipRules"
        :key="rule.id"
        class="border border-navy/20 bg-white px-2 py-1 text-[11px] font-semibold text-navy/70"
      >
        {{ relationshipRuleLabel(rule, index) }}
      </span>
    </div>
  </section>
</template>
