<script setup lang="ts">
/**
 * Exam workspace question list.
 *
 * Domain purpose:
 *   List the exam's questions compactly for selection in Redigera: sequence,
 *   title, type, points, and whether the question is ready for export. Flag
 *   questions with an open answer-key proposal and show the per-item
 *   blockers from the server's last refused export.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` in the Redigera list panel and in the
 *     phone question sheet; emits `select` with the item id and the view
 *     selects it through `useExamWorkspaceDocument`.
 */

import { IconCheck, IconWarning } from "../../../components/icons";
import type { ExamWorkspaceItemRow } from "./examWorkspaceRows";

defineProps<{
  exportBlockersByItemId: Record<string, string[]>;
  proposalItemIds: string[];
  readinessByItemId: Record<string, string[]>;
  rows: ExamWorkspaceItemRow[];
  selectedItemId: string | null;
}>();

const emit = defineEmits<{
  select: [itemId: string];
}>();
</script>

<template>
  <ol
    class="grid content-start"
    aria-label="Frågor"
    data-test="exam-workspace-item-table"
  >
    <li
      v-for="row in rows"
      :key="row.itemId"
      class="border-b border-navy/15"
    >
      <button
        type="button"
        class="grid w-full gap-1 px-3 py-2.5 text-left text-navy"
        :class="row.itemId === selectedItemId ? 'bg-navy/5 shadow-[inset_4px_0_0_var(--color-navy)]' : 'hover:bg-canvas'"
        :aria-current="row.itemId === selectedItemId ? 'true' : undefined"
        :data-test="`exam-workspace-item-row-${row.itemId}`"
        @click="emit('select', row.itemId)"
      >
        <span class="flex min-w-0 items-start gap-2">
          <span class="min-w-0 flex-1 truncate text-sm leading-snug">
            <span class="font-semibold">{{ row.sequence }}.</span>
            {{ row.title }}
          </span>
          <IconWarning
            v-if="readinessByItemId[row.itemId]"
            :size="16"
            class="mt-0.5 h-4 w-4 shrink-0 text-warning"
            aria-hidden="true"
          />
          <IconCheck
            v-else
            :size="16"
            class="mt-0.5 h-4 w-4 shrink-0 text-success"
            aria-hidden="true"
          />
        </span>
        <span class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs leading-snug text-navy/65">
          <span>{{ row.typeLabel }}</span>
          <span aria-hidden="true">·</span>
          <span>{{ row.pointsLabel }}</span>
          <span aria-hidden="true">·</span>
          <span
            class="font-semibold text-navy/80"
            :title="row.reviewReasons.length > 0 ? row.reviewReasons.join(' ') : undefined"
            :data-test="`exam-workspace-item-status-${row.itemId}`"
          >{{ row.statusLabel }}</span>
        </span>
        <span
          v-if="readinessByItemId[row.itemId] && !exportBlockersByItemId[row.itemId]"
          class="sr-only"
        >Behöver åtgärdas före export: {{ readinessByItemId[row.itemId]?.join(' ') }}</span>
        <span
          v-if="proposalItemIds.includes(row.itemId)"
          class="text-xs font-semibold leading-snug text-action"
          :data-test="`exam-workspace-item-proposal-${row.itemId}`"
        >
          Facitförslag finns
        </span>
        <span
          v-if="exportBlockersByItemId[row.itemId]"
          class="grid gap-0.5 text-xs leading-snug text-error"
          :data-test="`exam-workspace-item-blockers-${row.itemId}`"
        >
          <span
            v-for="blocker in exportBlockersByItemId[row.itemId]"
            :key="blocker"
            class="block"
          >
            {{ blocker }}
          </span>
        </span>
      </button>
    </li>
  </ol>
</template>
