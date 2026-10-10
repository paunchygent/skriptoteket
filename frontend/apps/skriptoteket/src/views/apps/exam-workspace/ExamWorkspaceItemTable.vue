<script setup lang="ts">
/**
 * Exam workspace question table.
 *
 * Domain purpose:
 *   List the exam's questions with type, points, and review status, flag
 *   questions with an open answer-key proposal, and show the per-item
 *   blockers from the server's last refused export.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; emits `select` with the item id and
 *     the view selects it through `useExamWorkspaceDocument`.
 */

import { IconCheck, IconWarning } from "../../../components/icons";
import type { ExamWorkspaceItemRow } from "./examWorkspaceRows";

defineProps<{
  exportBlockersByItemId: Record<string, string[]>;
  proposalItemIds: string[];
  rows: ExamWorkspaceItemRow[];
  selectedItemId: string | null;
}>();

const emit = defineEmits<{
  select: [itemId: string];
}>();
</script>

<template>
  <div class="overflow-x-auto border border-navy/20 bg-canvas">
    <table
      class="w-full table-fixed border-collapse text-left text-sm text-navy"
      data-test="exam-workspace-item-table"
    >
      <thead>
        <tr class="border-b border-navy/45">
          <th class="px-3 py-3 font-semibold">
            Fråga
          </th>
          <th class="w-32 px-2 py-3 font-semibold">
            Typ
          </th>
          <th class="w-20 px-2 py-3 font-semibold">
            Poäng
          </th>
          <th class="w-40 px-2 py-3 font-semibold">
            Status
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="row.itemId"
          class="cursor-pointer border-b border-navy/15"
          :class="row.itemId === selectedItemId ? 'bg-navy/5 shadow-[inset_4px_0_0_var(--color-navy)]' : 'hover:bg-panel'"
          :aria-selected="row.itemId === selectedItemId ? 'true' : 'false'"
          :data-test="`exam-workspace-item-row-${row.itemId}`"
          @click="emit('select', row.itemId)"
        >
          <td class="min-w-0 px-3 py-3 align-top">
            <span class="block truncate">
              <span class="font-semibold">{{ row.sequence }}.</span>
              {{ row.title }}
            </span>
            <span
              v-if="row.promptExcerpt"
              class="mt-0.5 line-clamp-2 block text-xs text-navy/65"
            >
              {{ row.promptExcerpt }}
            </span>
          </td>
          <td class="px-2 py-3 align-top">
            {{ row.typeLabel }}
          </td>
          <td class="px-2 py-3 align-top">
            {{ row.pointsLabel }}
          </td>
          <td class="px-2 py-3 align-top">
            <span
              class="inline-flex items-center gap-2"
              :title="row.reviewReasons.length > 0 ? row.reviewReasons.join(', ') : undefined"
              :data-test="`exam-workspace-item-status-${row.itemId}`"
            >
              <IconWarning
                v-if="row.reviewRequired"
                :size="18"
                class="h-[1.125rem] w-[1.125rem] shrink-0 text-warning"
                aria-hidden="true"
              />
              <IconCheck
                v-else
                :size="18"
                class="h-[1.125rem] w-[1.125rem] shrink-0 text-success"
                aria-hidden="true"
              />
              <span class="text-xs font-semibold leading-tight text-navy">
                {{ row.statusLabel }}
              </span>
            </span>
            <span
              v-if="proposalItemIds.includes(row.itemId)"
              class="mt-1 block text-xs leading-snug text-navy/70"
              :data-test="`exam-workspace-item-proposal-${row.itemId}`"
            >
              Facitförslag finns
            </span>
            <ul
              v-if="exportBlockersByItemId[row.itemId]"
              class="mt-1 grid gap-0.5 text-xs leading-snug text-error"
              :data-test="`exam-workspace-item-blockers-${row.itemId}`"
            >
              <li
                v-for="blocker in exportBlockersByItemId[row.itemId]"
                :key="blocker"
              >
                {{ blocker }}
              </li>
            </ul>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
