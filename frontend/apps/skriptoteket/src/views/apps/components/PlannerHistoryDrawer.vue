<script setup lang="ts">
/**
 * Task history drawer for class-level draft continuity.
 *
 * This drawer keeps grouping and seating history secondary to the active class
 * workspace flow. It can present the current active draft separately from
 * older drafts and emits explicit open/delete actions instead of mixing
 * history management into the main workspace.
 */

import { computed, ref } from "vue";

import { IconTrash, IconX } from "../../../components/icons";
import type { PlanDraftSummary } from "../classroomPlannerTypes";

const props = defineProps<{
  open: boolean;
  title: string;
  activeSummary?: PlanDraftSummary | null;
  summaries: PlanDraftSummary[];
  emptyLabel: string;
  activeLabel?: string;
  historyLabel?: string;
  canOpenSummaries?: boolean;
  canDeleteSummaries?: boolean;
  busySummaryId?: string | null;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "open-summary", draftId: string): void;
  (e: "delete-summary", draftId: string): void;
}>();

const confirmDeleteId = ref<string | null>(null);

const renderedActiveLabel = computed(() => props.activeLabel ?? "Aktuellt utkast");
const renderedHistoryLabel = computed(() => props.historyLabel ?? "Tidigare utkast");

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

function requestDelete(draftId: string): void {
  confirmDeleteId.value = draftId;
}

function cancelDelete(): void {
  confirmDeleteId.value = null;
}

function confirmDelete(draftId: string): void {
  emit("delete-summary", draftId);
  confirmDeleteId.value = null;
}
</script>

<template>
  <div v-if="props.open">
    <div
      class="fixed inset-0 z-40 bg-navy/40"
      @click="emit('close')"
    />
    <aside
      class="fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-[26rem] flex-col border border-navy bg-modal shadow-brutal"
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
          class="btn-ghost planner-btn-ghost-canvas planner-btn-icon-sm"
          aria-label="Stäng historik"
          @click="emit('close')"
        >
          <IconX :size="14" />
        </button>
      </div>

      <div
        class="flex-1 space-y-3 overflow-y-auto p-4"
      >
        <section
          v-if="props.activeSummary"
          class="space-y-2"
        >
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55">
            {{ renderedActiveLabel }}
          </p>
          <article class="space-y-2 border border-navy bg-panel-muted p-4 shadow-brutal-sm">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <p class="text-sm font-semibold text-navy">
                {{ props.activeSummary.template_name ?? "Utan klassrum" }}
              </p>
              <span class="border border-navy/20 bg-canvas px-2 py-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                Aktivt nu
              </span>
            </div>
            <p class="text-sm text-navy/70">
              Revision {{ props.activeSummary.revision }} · uppdaterad
              {{ formatTimestamp(props.activeSummary.updated_at) }}
            </p>
            <p class="text-xs uppercase tracking-[var(--huleedu-tracking-label)] text-navy/50">
              Senast öppnad {{ formatTimestamp(props.activeSummary.last_opened_at) }}
            </p>
          </article>
        </section>

        <section class="space-y-2">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55">
            {{ renderedHistoryLabel }}
          </p>
          <div
            v-if="props.summaries.length === 0"
            class="border border-dashed border-navy/20 bg-canvas px-4 py-8 text-center text-sm leading-relaxed text-navy/60"
          >
            {{ props.emptyLabel }}
          </div>
          <article
            v-for="summary in props.summaries"
            :key="summary.id"
            class="space-y-2 border border-navy/20 bg-canvas p-4"
          >
            <div class="flex items-start justify-between gap-3">
              <button
                type="button"
                class="planner-summary-button"
                :disabled="props.busySummaryId === summary.id"
                @click="props.canOpenSummaries ? emit('open-summary', summary.id) : undefined"
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
              </button>

              <button
                v-if="props.canDeleteSummaries"
                type="button"
                class="btn-ghost planner-btn-ghost-subtle planner-btn-icon-lg"
                :disabled="props.busySummaryId === summary.id"
                aria-label="Ta bort historiskt utkast"
                @click.stop="requestDelete(summary.id)"
              >
                <IconTrash :size="14" />
              </button>
            </div>

            <div
              v-if="confirmDeleteId === summary.id"
              class="space-y-3 border border-critical/20 bg-critical/5 p-3"
            >
              <div class="space-y-1">
                <p class="text-sm font-semibold text-navy">
                  Ta bort utkast?
                </p>
                <p class="text-sm text-navy/70">
                  Det här tar bort det här historiska utkastet permanent.
                </p>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="btn-ghost planner-btn-danger-soft"
                  @click="confirmDelete(summary.id)"
                >
                  Ta bort
                </button>
                <button
                  type="button"
                  class="btn-ghost planner-btn-ghost-soft"
                  @click="cancelDelete"
                >
                  Avbryt
                </button>
              </div>
            </div>
          </article>
        </section>
      </div>
    </aside>
  </div>
</template>
