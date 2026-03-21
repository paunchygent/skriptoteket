<script setup lang="ts">
/**
 * Planner selection gate.
 *
 * This component renders the pre-planning asset selection flow for
 * Klassrumskartan. It keeps class list and classroom selection, CRUD entry
 * points, and responsive onboarding copy outside the live planner workspace.
 */

import { computed } from "vue";

import type { ResumablePlanDraft, RoomTemplate, Roster } from "../classroomPlannerTypes";

const props = defineProps<{
  availableRosters: Roster[];
  availableTemplates: RoomTemplate[];
  selectedRosterId: string | null;
  selectedTemplateId: string | null;
  resumableDraft: ResumablePlanDraft | null;
  isLoadingCatalog: boolean;
  canStartPlanning: boolean;
}>();

const emit = defineEmits<{
  (e: "select-roster", rosterId: string): void;
  (e: "select-template", templateId: string): void;
  (e: "create-roster"): void;
  (e: "edit-roster", roster: Roster): void;
  (e: "create-template"): void;
  (e: "edit-template", template: RoomTemplate): void;
  (e: "start-planning"): void;
  (e: "resume-draft"): void;
  (e: "discard-resumable-draft"): void;
}>();

const selectedRoster = computed(() => {
  return props.availableRosters.find((roster) => roster.id === props.selectedRosterId) ?? null;
});

const selectedTemplate = computed(() => {
  return props.availableTemplates.find((template) => template.id === props.selectedTemplateId) ?? null;
});

function capacityLabel(template: RoomTemplate): string | null {
  if (!selectedRoster.value) {
    return null;
  }

  const seatCount = template.seats.length;
  const studentCount = selectedRoster.value.students.length;
  if (seatCount >= studentCount) {
    return `${studentCount} elever passar i ${seatCount} platser`;
  }
  return `${studentCount} elever men bara ${seatCount} platser`;
}
</script>

<template>
  <section class="space-y-6">
    <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
      <div class="flex flex-col gap-3 border-b border-navy/20 pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Startyta
          </p>
          <h2 class="font-serif text-2xl text-navy">
            Välj klass och klassrum
          </h2>
        </div>
        <div class="text-sm text-navy/70">
          Planeringen öppnas så snart du har valt båda.
        </div>
      </div>

      <div
        v-if="selectedRoster && selectedTemplate"
        class="grid gap-3 border border-success/30 bg-success/10 p-4 text-sm text-navy md:grid-cols-[minmax(0,1fr)_auto]"
      >
        <div class="space-y-1">
          <div class="font-semibold">
            {{ selectedRoster.name }} · {{ selectedTemplate.name }}
          </div>
          <div class="text-navy/70">
            {{ selectedRoster.students.length }} elever · {{ selectedTemplate.seats.length }} platser
          </div>
        </div>
        <button
          type="button"
          class="btn-cta"
          :disabled="!canStartPlanning"
          @click="emit('start-planning')"
        >
          Öppna planeringen
        </button>
      </div>

      <div
        v-if="resumableDraft"
        class="grid gap-3 border border-navy/20 bg-canvas p-4 text-sm text-navy md:grid-cols-[minmax(0,1fr)_auto]"
      >
        <div class="space-y-1">
          <div class="font-semibold">
            Fortsätt senaste utkastet
          </div>
          <div class="text-navy/70">
            {{ resumableDraft.roster_name }} · {{ resumableDraft.template_name }}
          </div>
        </div>
        <div class="flex flex-wrap gap-2 md:justify-end">
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-white shadow-none"
            @click="emit('discard-resumable-draft')"
          >
            Avsluta utkast
          </button>
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-white shadow-none"
            @click="emit('resume-draft')"
          >
            Fortsätt
          </button>
        </div>
      </div>
    </article>

    <div class="grid gap-6 xl:grid-cols-2">
      <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
        <div class="flex flex-col gap-3 border-b border-navy/20 pb-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              1. Klasslistor
            </p>
            <h2 class="font-serif text-2xl text-navy">
              Välj klass
            </h2>
          </div>
          <button
            type="button"
            class="btn-primary"
            @click="emit('create-roster')"
          >
            Ny klasslista
          </button>
        </div>

        <div
          v-if="isLoadingCatalog"
          class="border border-dashed border-navy/30 bg-canvas px-4 py-8 text-center text-sm text-navy/60"
        >
          Hämtar klasslistor...
        </div>

        <div
          v-else-if="availableRosters.length === 0"
          class="border border-dashed border-navy/30 bg-canvas px-4 py-8 text-center text-sm text-navy/60"
        >
          Inga klasslistor ännu.
        </div>

        <div
          v-else
          class="grid gap-3"
        >
          <article
            v-for="roster in availableRosters"
            :key="roster.id"
            class="cursor-pointer border p-4 transition-shadow"
            :class="selectedRosterId === roster.id ? 'border-burgundy bg-burgundy/10 shadow-brutal-sm' : 'border-navy/20 bg-white hover:shadow-brutal-sm'"
            role="button"
            tabindex="0"
            @click="emit('select-roster', roster.id)"
            @keydown.enter.prevent="emit('select-roster', roster.id)"
            @keydown.space.prevent="emit('select-roster', roster.id)"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div class="min-w-0 text-left">
                <h3 class="truncate text-lg font-semibold text-navy">
                  {{ roster.name }}
                </h3>
                <p class="mt-1 text-sm text-navy/70">
                  {{ roster.students.length }} elever
                </p>
              </div>
              <button
                type="button"
                class="btn-ghost border-navy/30 bg-canvas shadow-none"
                @click.stop="emit('edit-roster', roster)"
              >
                Redigera
              </button>
            </div>
          </article>
        </div>
      </article>

      <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
        <div class="flex flex-col gap-3 border-b border-navy/20 pb-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              2. Klassrum
            </p>
            <h2 class="font-serif text-2xl text-navy">
              Välj rumsmall
            </h2>
          </div>
          <button
            type="button"
            class="btn-primary"
            @click="emit('create-template')"
          >
            Nytt klassrum
          </button>
        </div>

        <div
          v-if="isLoadingCatalog"
          class="border border-dashed border-navy/30 bg-canvas px-4 py-8 text-center text-sm text-navy/60"
        >
          Hämtar klassrum...
        </div>

        <div
          v-else-if="availableTemplates.length === 0"
          class="border border-dashed border-navy/30 bg-canvas px-4 py-8 text-center text-sm text-navy/60"
        >
          Inga klassrum ännu.
        </div>

        <div
          v-else
          class="grid gap-3"
        >
          <article
            v-for="template in availableTemplates"
            :key="template.id"
            class="cursor-pointer border p-4 transition-shadow"
            :class="selectedTemplateId === template.id ? 'border-burgundy bg-burgundy/10 shadow-brutal-sm' : 'border-navy/20 bg-white hover:shadow-brutal-sm'"
            role="button"
            tabindex="0"
            @click="emit('select-template', template.id)"
            @keydown.enter.prevent="emit('select-template', template.id)"
            @keydown.space.prevent="emit('select-template', template.id)"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div class="min-w-0 text-left">
                <h3 class="truncate text-lg font-semibold text-navy">
                  {{ template.name }}
                </h3>
                <p class="mt-1 text-sm text-navy/70">
                  {{ template.seats.length }} platser · {{ template.fixtures.length }} fixturer
                </p>
                <p
                  v-if="capacityLabel(template)"
                  class="mt-1 text-xs font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55"
                >
                  {{ capacityLabel(template) }}
                </p>
              </div>
              <button
                type="button"
                class="btn-ghost border-navy/30 bg-canvas shadow-none"
                @click.stop="emit('edit-template', template)"
              >
                Redigera
              </button>
            </div>
          </article>
        </div>
      </article>
    </div>
  </section>
</template>
