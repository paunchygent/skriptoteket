<script setup lang="ts">
/**
 * Read-only task history drawer.
 *
 * This drawer keeps grouping and seating history secondary to the active class
 * workspace flow. It shows compact draft summaries only and deliberately does
 * not reactivate historical drafts.
 */

import type { PlanDraftSummary } from "../classroomPlannerTypes";

const props = defineProps<{
  open: boolean;
  title: string;
  summaries: PlanDraftSummary[];
  emptyLabel: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("sv-SE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(status: PlanDraftSummary["status"]): string {
  switch (status) {
    case "active":
      return "Aktiv";
    case "abandoned":
      return "Avslutad";
    case "superseded":
      return "Ersatt";
    default:
      return status;
  }
}
</script>

<template>
  <div v-if="props.open">
    <div
      class="fixed inset-0 z-40 bg-navy/40"
      @click="emit('close')"
    />
    <aside
      class="fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-[26rem] flex-col border border-navy bg-white shadow-brutal"
    >
      <div class="flex items-start justify-between gap-3 border-b border-navy/20 p-4">
        <div class="min-w-0">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Historik
          </p>
          <h3 class="font-serif text-xl text-navy">
            {{ props.title }}
          </h3>
        </div>
        <button
          type="button"
          class="btn-ghost h-[28px] w-[28px] border-navy/30 bg-canvas px-0 py-0 shadow-none"
          @click="emit('close')"
        >
          ×
        </button>
      </div>

      <div
        v-if="props.summaries.length === 0"
        class="flex flex-1 items-center justify-center px-6 text-center text-sm leading-relaxed text-navy/60"
      >
        {{ props.emptyLabel }}
      </div>

      <div
        v-else
        class="flex-1 space-y-3 overflow-y-auto p-4"
      >
        <article
          v-for="summary in props.summaries"
          :key="summary.id"
          class="space-y-2 border border-navy/20 bg-canvas p-4"
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <p class="text-sm font-semibold text-navy">
              {{ summary.template_name ?? "Utan klassrum" }}
            </p>
            <span class="border border-navy/20 bg-white px-2 py-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              {{ statusLabel(summary.status) }}
            </span>
          </div>
          <p class="text-sm text-navy/70">
            Revision {{ summary.revision }} · uppdaterad {{ formatTimestamp(summary.updated_at) }}
          </p>
          <p class="text-xs uppercase tracking-[var(--huleedu-tracking-label)] text-navy/50">
            Senast öppnad {{ formatTimestamp(summary.last_opened_at) }}
          </p>
        </article>
      </div>
    </aside>
  </div>
</template>
