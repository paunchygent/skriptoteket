<script setup lang="ts">
/**
 * Class-first planner workspace.
 *
 * This component keeps the class workspace neutral on entry and relies on the
 * segmented toggle as the only way to enter groups or seating. The overview
 * therefore stays class-focused instead of duplicating mode-entry or
 * draft-history actions that belong to the active workspace.
 */

import { computed, ref } from "vue";

import type { ClassWorkspaceSummary } from "../classroomPlannerTypes";
import PlannerTopPanel from "./PlannerTopPanel.vue";

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

const overviewCards = computed(() => {
  return [
    {
      key: "students",
      eyebrow: "Elever",
      title: `${props.workspaceSummary.roster.student_count} elever`,
      description: "Arbeta vidare med roster och elevlistan för den här klassen.",
      actionLabel: "Redigera klass",
    },
  ];
});

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
  }
}
</script>

<template>
  <section class="space-y-4">
    <PlannerTopPanel
      :title="workspaceSummary.roster.name"
      context-label="Klassöversikt"
      :mode-value="workspaceMode"
      supporting-text="Välj Grupper eller Sittplatser i väljaren ovan när du vill fortsätta arbetet."
      status-label="Översikt"
      status-message="Redigera klassen här eller öppna en arbetsyta i väljaren ovan."
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
          Klassöversikt
        </h3>
        <p class="max-w-[40rem] text-sm leading-relaxed text-navy/70">
          Här kan du redigera klassen. Öppna Grupper eller Sittplatser i väljaren ovan när du vill fortsätta planeringen.
        </p>
      </div>

      <div class="grid gap-3 md:max-w-[24rem]">
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
          </div>
        </article>
      </div>
    </article>
  </section>
</template>
