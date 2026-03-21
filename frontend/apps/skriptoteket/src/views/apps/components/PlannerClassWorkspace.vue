<script setup lang="ts">
/**
 * Class-first planner workspace.
 *
 * This component renders the intermediate class workspace between the landing
 * page and the live planner shell. It keeps grouping and seating separated as
 * distinct task cards while using the compact backend summary contract from
 * `PR-0086`.
 */

import { computed } from "vue";

import type {
  ClassWorkspaceSummary,
  PlanDraftSummary,
  RoomTemplate,
} from "../classroomPlannerTypes";

const props = defineProps<{
  availableTemplates: RoomTemplate[];
  selectedTemplateId: string | null;
  workspaceSummary: ClassWorkspaceSummary;
  isLoadingWorkspace: boolean;
}>();

const emit = defineEmits<{
  (e: "back-to-landing"): void;
  (e: "select-template", templateId: string): void;
  (e: "open-grouping"): void;
  (e: "open-seating"): void;
}>();

const activeSeatingTemplate = computed(() => {
  return (
    props.availableTemplates.find((template) => template.id === props.selectedTemplateId) ?? null
  );
});

const seatingRequiresClassroom = computed(() => {
  return props.workspaceSummary.task_entry_options.some((option) => {
    return option.draft_kind === "seating" && option.classroom_selection_mode === "required";
  });
});

const groupingSupportsNoClassroom = computed(() => {
  return props.workspaceSummary.task_entry_options.some((option) => {
    return option.draft_kind === "grouping" && option.classroom_selection_mode === "optional";
  });
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
</script>

<template>
  <section class="space-y-6">
    <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
      <div class="flex flex-col gap-4 border-b border-navy/20 pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div class="space-y-1">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Klassarbetsyta
          </p>
          <h2 class="font-serif text-3xl text-navy">
            {{ workspaceSummary.roster.name }}
          </h2>
          <p class="max-w-[42rem] text-sm leading-relaxed text-navy/70">
            Välj om du vill arbeta med grupper eller sittplatser. Historik och finare uppdelning hålls tillbaka tills du faktiskt behöver dem.
          </p>
        </div>

        <button
          type="button"
          class="btn-ghost border-navy/30 bg-canvas shadow-none"
          @click="emit('back-to-landing')"
        >
          Välj annan klass
        </button>
      </div>

      <div class="grid gap-3 md:grid-cols-3">
        <div class="border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy">
          <span class="font-semibold">Elever:</span>
          {{ workspaceSummary.roster.student_count }}
        </div>
        <div class="border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy/70">
          <span class="font-semibold text-navy">Grupper:</span>
          {{ groupingSupportsNoClassroom ? "kan startas utan klassrum" : "kräver klassrum" }}
        </div>
        <div class="border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy/70">
          <span class="font-semibold text-navy">Sittplatser:</span>
          {{ seatingRequiresClassroom ? "kräver klassrum" : "kan startas direkt" }}
        </div>
      </div>
    </article>

    <div
      v-if="isLoadingWorkspace"
      class="border border-navy bg-white px-4 py-12 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
    >
      Laddar klassarbetsytan...
    </div>

    <div
      v-else
      class="grid gap-6 xl:grid-cols-2"
    >
      <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
        <div class="space-y-1 border-b border-navy/20 pb-3">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Grupper
          </p>
          <h3 class="font-serif text-2xl text-navy">
            Grupparbete för {{ workspaceSummary.roster.name }}
          </h3>
        </div>

        <div
          v-if="workspaceSummary.active_grouping_draft"
          class="space-y-2 border border-success/30 bg-success/10 p-4 text-sm text-navy"
        >
          <p class="font-semibold">
            Aktiv gruppindelning finns redan
          </p>
          <p class="text-navy/70">
            Senast uppdaterad {{ formatDraftTimestamp(workspaceSummary.active_grouping_draft) }}
          </p>
        </div>
        <div
          v-else
          class="space-y-2 border border-navy/20 bg-canvas p-4 text-sm text-navy/70"
        >
          <p class="font-semibold text-navy">
            Ingen aktiv gruppindelning ännu
          </p>
          <p>
            Starta från klassens roster och lägg till klassrum först när du verkligen behöver det.
          </p>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-navy/20 pt-3 text-sm text-navy/65">
          <span>{{ workspaceSummary.grouping_history.length }} tidigare grupputkast</span>
          <button
            type="button"
            class="btn-cta"
            @click="emit('open-grouping')"
          >
            {{ workspaceSummary.active_grouping_draft ? "Fortsätt grupper" : "Starta grupper" }}
          </button>
        </div>
      </article>

      <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
        <div class="space-y-1 border-b border-navy/20 pb-3">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Sittplatser
          </p>
          <h3 class="font-serif text-2xl text-navy">
            Sittplacering för {{ workspaceSummary.roster.name }}
          </h3>
        </div>

        <div
          v-if="workspaceSummary.active_seating_draft"
          class="space-y-2 border border-success/30 bg-success/10 p-4 text-sm text-navy"
        >
          <p class="font-semibold">
            Aktiv sittplacering finns redan
          </p>
          <p class="text-navy/70">
            {{ workspaceSummary.active_seating_draft.template_name ?? "Utan klassrum" }} · senast uppdaterad
            {{ formatDraftTimestamp(workspaceSummary.active_seating_draft) }}
          </p>
        </div>
        <div
          v-else
          class="space-y-3 border border-navy/20 bg-canvas p-4 text-sm text-navy"
        >
          <label class="space-y-1">
            <span class="block font-semibold text-navy">Välj klassrum</span>
            <select
              class="w-full border border-navy/20 bg-white px-3 py-2 text-sm text-navy"
              :value="selectedTemplateId ?? ''"
              @change="emit('select-template', ($event.target as HTMLSelectElement).value)"
            >
              <option value="">
                Välj rumsmall
              </option>
              <option
                v-for="template in availableTemplates"
                :key="template.id"
                :value="template.id"
              >
                {{ template.name }} · {{ template.seats.length }} platser
              </option>
            </select>
          </label>
          <p class="text-navy/70">
            Sittplatser kräver ett klassrum, så välj det här i arbetsytan i stället för redan på startsidan.
          </p>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-navy/20 pt-3 text-sm text-navy/65">
          <span>
            {{
              workspaceSummary.active_seating_draft
                ? workspaceSummary.seating_history.length + " tidigare sittutkast"
                : activeSeatingTemplate
                  ? activeSeatingTemplate.name
                  : "Välj klassrum för att öppna sittplatser"
            }}
          </span>
          <button
            type="button"
            class="btn-cta"
            :disabled="!workspaceSummary.active_seating_draft && !selectedTemplateId"
            @click="emit('open-seating')"
          >
            {{
              workspaceSummary.active_seating_draft
                ? "Fortsätt sittplatser"
                : "Öppna sittplatser"
            }}
          </button>
        </div>
      </article>
    </div>
  </section>
</template>
