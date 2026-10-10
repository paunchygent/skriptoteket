<script setup lang="ts">
/**
 * Saved exam list in the exam workspace rail.
 *
 * Domain purpose:
 *   List the teacher's other saved exams (one entry per exam, newest saved
 *   version) and let the teacher open one. Exams that share a file name get
 *   a "N av M med samma namn" count, oldest first, beside version and saved
 *   time so they can be told apart. Opening is blocked while the open exam
 *   has unsaved edits.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; emits `open` with the lineage id and
 *     the view opens it through `useExamWorkspaceDocument`.
 */

import { computed } from "vue";

import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import { examWorkspaceDocumentLabel, examWorkspaceSavedAtLabel } from "./examWorkspaceRows";

const props = defineProps<{
  documents: ExamWorkspaceDocumentSummary[];
  isBusy: boolean;
  isDirty: boolean;
}>();

const emit = defineEmits<{
  open: [lineageId: string];
}>();

// "N av M med samma namn" per lineage id, only for names that repeat.
const sameNameCounts = computed(() => {
  const groups = new Map<string, ExamWorkspaceDocumentSummary[]>();
  for (const entry of props.documents) {
    const label = examWorkspaceDocumentLabel(entry.name);
    groups.set(label, [...(groups.get(label) ?? []), entry]);
  }
  const counts: Record<string, string> = {};
  for (const group of groups.values()) {
    if (group.length < 2) {
      continue;
    }
    [...group]
      .sort((left, right) => left.saved_at.localeCompare(right.saved_at))
      .forEach((entry, index) => {
        counts[entry.lineage_id] = `${index + 1} av ${group.length} med samma namn`;
      });
  }
  return counts;
});
</script>

<template>
  <section
    v-if="documents.length > 0"
    class="grid gap-2"
    data-test="exam-workspace-saved-documents"
  >
    <h2 class="text-sm font-semibold leading-tight text-navy">
      Sparade prov
    </h2>
    <ul class="grid gap-1">
      <li
        v-for="entry in documents"
        :key="entry.lineage_id"
      >
        <button
          type="button"
          class="grid w-full gap-0.5 border border-navy/20 bg-canvas px-3 py-2 text-left hover:bg-panel disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="isBusy || isDirty"
          :data-test="`exam-workspace-open-${entry.lineage_id}`"
          @click="emit('open', entry.lineage_id)"
        >
          <span class="truncate text-sm font-medium leading-snug text-navy">
            {{ examWorkspaceDocumentLabel(entry.name) }}
          </span>
          <span class="text-xs leading-snug text-navy/65">
            Version {{ entry.version }} · {{ examWorkspaceSavedAtLabel(entry.saved_at) }}<template v-if="sameNameCounts[entry.lineage_id]"> · {{ sameNameCounts[entry.lineage_id] }}</template>
          </span>
        </button>
      </li>
    </ul>
    <p
      v-if="isDirty"
      class="text-xs leading-snug text-navy/65"
    >
      Spara det öppna provet innan du öppnar ett annat.
    </p>
  </section>
</template>
