<script setup lang="ts">
/**
 * Class-first planner workspace.
 *
 * This component keeps the class workspace neutral on entry, lets the teacher
 * choose one task surface at a time, and keeps read-only history secondary via
 * task-specific drawers instead of always-open panels.
 */

import { computed, ref } from "vue";

import type {
  ClassWorkspaceSummary,
  PlanDraftSummary,
} from "../classroomPlannerTypes";
import PlannerHistoryDrawer from "./PlannerHistoryDrawer.vue";
import PlannerTopPanel from "./PlannerTopPanel.vue";

type HistoryDrawerMode = "grouping" | "seating" | null;

const props = defineProps<{
  workspaceSummary: ClassWorkspaceSummary;
  isLoadingWorkspace: boolean;
}>();

const emit = defineEmits<{
  (e: "back-to-landing"): void;
  (e: "edit-roster"): void;
  (e: "open-grouping", payload: { templateId: string | null }): void;
  (e: "open-seating", payload: { templateId: string | null }): void;
}>();

const workspaceMode = ref<"overview" | "grouping" | "seating">("overview");
const historyDrawerMode = ref<HistoryDrawerMode>(null);

const currentHistoryTitle = computed(() => {
  return historyDrawerMode.value === "grouping" ? "Grupper" : "Sittplatser";
});

const currentHistorySummaries = computed<PlanDraftSummary[]>(() => {
  if (historyDrawerMode.value === "grouping") {
    return props.workspaceSummary.grouping_history;
  }
  if (historyDrawerMode.value === "seating") {
    return props.workspaceSummary.seating_history;
  }
  return [];
});

const currentHistoryEmptyLabel = computed(() => {
  return historyDrawerMode.value === "grouping"
    ? "Ingen grupphistorik ännu."
    : "Ingen sittplatshistorik ännu.";
});

const overviewCards = computed(() => {
  return [
    {
      key: "students",
      eyebrow: "Elever",
      title: `${props.workspaceSummary.roster.student_count} elever`,
      description: "Öppna klassen och ändra roster",
      actionLabel: "Redigera klass",
    },
    {
      key: "grouping",
      eyebrow: "Grupper",
      title: props.workspaceSummary.active_grouping_draft
        ? "Aktiv gruppindelning"
        : "Ingen aktiv gruppindelning",
      description: props.workspaceSummary.active_grouping_draft
        ? `Senast uppdaterad ${formatDraftTimestamp(props.workspaceSummary.active_grouping_draft)}`
        : `${props.workspaceSummary.grouping_history.length} tidigare grupputkast`,
      actionLabel: props.workspaceSummary.active_grouping_draft ? "Fortsätt grupper" : "Öppna grupper",
      historyLabel: "Visa grupphistorik",
    },
    {
      key: "seating",
      eyebrow: "Sittplatser",
      title: props.workspaceSummary.active_seating_draft?.template_name ?? "Ingen aktiv sittplacering",
      description: props.workspaceSummary.active_seating_draft
        ? `Senast uppdaterad ${formatDraftTimestamp(props.workspaceSummary.active_seating_draft)}`
        : `${props.workspaceSummary.seating_history.length} tidigare sittutkast`,
      actionLabel: props.workspaceSummary.active_seating_draft ? "Fortsätt sittplatser" : "Öppna sittplatser",
      historyLabel: "Visa sittplatshistorik",
    },
  ];
});

function formatDraftTimestamp(summary: PlanDraftSummary | null | undefined): string | null {
  if (!summary) {
    return null;
  }

  return new Intl.DateTimeFormat("sv-SE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(summary.updated_at));
}

function selectWorkspaceMode(value: string): void {
  if (value === "overview") {
    workspaceMode.value = value;
    return;
  }

  if (value === "grouping") {
    emit("open-grouping", { templateId: null });
    workspaceMode.value = "overview";
    return;
  }

  if (value === "seating") {
    emit("open-seating", { templateId: null });
    workspaceMode.value = "overview";
  }
}

function activateOverviewCard(key: string): void {
  if (key === "students") {
    emit("edit-roster");
    return;
  }
  if (key === "grouping") {
    emit("open-grouping", { templateId: null });
    return;
  }
  if (key === "seating") {
    emit("open-seating", { templateId: null });
  }
}

function openHistoryDrawer(key: string): void {
  if (key === "grouping" || key === "seating") {
    historyDrawerMode.value = key;
  }
}
</script>

<template>
  <section class="space-y-4">
    <PlannerTopPanel
      :title="workspaceSummary.roster.name"
      context-label="Håll översikten neutral tills du vet om du ska arbeta med grupper eller sittplatser."
      :mode-value="workspaceMode"
      supporting-text="Översikten samlar klassens fasta information. Historik öppnas bara när du ber om den."
      status-label="Översikt"
      status-message="Välj arbetsyta direkt i väljaren ovan."
      status-tone="neutral"
      @update:mode-value="selectWorkspaceMode"
      @exit="emit('back-to-landing')"
    />

    <div
      v-if="isLoadingWorkspace"
      class="border border-navy bg-white px-4 py-12 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
    >
      Laddar klassarbetsytan...
    </div>

    <article
      v-else
      class="space-y-4 border border-navy bg-white p-4 shadow-brutal-sm"
    >
      <div class="space-y-1">
        <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Översikt
        </p>
        <h3 class="font-serif text-2xl text-navy">
          Välj arbetsyta
        </h3>
        <p class="max-w-[40rem] text-sm leading-relaxed text-navy/70">
          Använd väljaren ovan för att fokusera på grupper eller sittplatser. Historik hålls undan tills du ber om den.
        </p>
      </div>

      <div class="grid gap-3 md:grid-cols-3">
        <article
          v-for="card in overviewCards"
          :key="card.key"
          class="space-y-3 border border-navy/20 bg-canvas p-3"
        >
          <div class="space-y-2">
            <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              {{ card.eyebrow }}
            </p>
            <p class="text-xl font-semibold text-navy">
              {{ card.title }}
            </p>
            <p class="text-sm text-navy/70">
              {{ card.description }}
            </p>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 border-t border-navy/15 pt-3">
            <button
              type="button"
              class="btn-ghost border-navy/30 bg-white shadow-none"
              @click="activateOverviewCard(card.key)"
            >
              {{ card.actionLabel }}
            </button>

            <button
              v-if="card.key === 'grouping' || card.key === 'seating'"
              type="button"
              class="text-xs font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/65 underline-offset-2 hover:text-navy hover:underline"
              @click="openHistoryDrawer(card.key)"
            >
              {{ card.historyLabel }}
            </button>
          </div>
        </article>
      </div>
    </article>

    <PlannerHistoryDrawer
      :open="historyDrawerMode !== null"
      :title="currentHistoryTitle"
      :summaries="currentHistorySummaries"
      :empty-label="currentHistoryEmptyLabel"
      @close="historyDrawerMode = null"
    />
  </section>
</template>
