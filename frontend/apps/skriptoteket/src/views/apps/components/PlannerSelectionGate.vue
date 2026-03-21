<script setup lang="ts">
/**
 * Planner selection gate.
 *
 * This component renders the pre-planning asset selection flow for
 * Klassrumskartan. It keeps class list and classroom selection, CRUD entry
 * points, and responsive onboarding copy outside the live planner workspace.
 */

import type { LessonMode, RoomTemplate, Roster } from "../classroomPlannerTypes";

defineProps<{
  lessonModes: LessonMode[];
  availableRosters: Roster[];
  availableTemplates: RoomTemplate[];
  selectedLessonModeId: string | null;
  selectedRosterId: string | null;
  selectedTemplateId: string | null;
  isLoadingCatalog: boolean;
  canStartPlanning: boolean;
}>();

const emit = defineEmits<{
  (e: "select-lesson-mode", lessonModeId: string): void;
  (e: "select-roster", rosterId: string): void;
  (e: "select-template", templateId: string): void;
  (e: "create-roster"): void;
  (e: "edit-roster", roster: Roster): void;
  (e: "create-template"): void;
  (e: "edit-template", template: RoomTemplate): void;
  (e: "start-planning"): void;
}>();
</script>

<template>
  <section class="space-y-6">
    <div class="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
        <div class="border-b border-navy/20 pb-3">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Startyta
          </p>
          <h2 class="font-serif text-2xl text-navy">
            Välj planeringsläge
          </h2>
        </div>

        <div class="flex flex-wrap gap-3">
          <button
            v-for="mode in lessonModes"
            :key="mode.id"
            type="button"
            class="btn-ghost"
            :class="selectedLessonModeId === mode.id ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-canvas shadow-none'"
            @click="emit('select-lesson-mode', mode.id)"
          >
            {{ mode.name }}
          </button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <div class="border border-navy/20 bg-canvas p-3">
            <div class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Slumpa
            </div>
            <div class="mt-1 text-sm leading-relaxed text-navy/80">
              Första utkast via slumpmässig grupp- och sittplatsfördelning.
            </div>
          </div>
          <div class="border border-navy/20 bg-canvas p-3">
            <div class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Regelmotor
            </div>
            <div class="mt-1 text-sm leading-relaxed text-navy/80">
              Aktivera eller stäng av elevmetadata, parregler, zonpreferenser och historikregler per utkast.
            </div>
          </div>
        </div>
      </article>

      <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
        <div class="border-b border-navy/20 pb-3">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Slice 2
          </p>
          <h2 class="font-serif text-2xl text-navy">
            Responsiv whiteboard-planering
          </h2>
        </div>
        <div class="grid gap-3 md:grid-cols-2">
          <div class="border border-navy/20 bg-canvas p-3 text-sm leading-relaxed text-navy/80">
            Klassrumsmallar stöder nu whiteboard, lärarbord, fönster och dörr för snyggare visuella planer.
          </div>
          <div class="border border-navy/20 bg-canvas p-3 text-sm leading-relaxed text-navy/80">
            Klasslistor och klassrum kan skapas, redigeras och raderas direkt från startytan.
          </div>
        </div>
      </article>
    </div>

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
            class="border p-4 transition-shadow"
            :class="selectedRosterId === roster.id ? 'border-burgundy bg-burgundy/10 shadow-brutal-sm' : 'border-navy/20 bg-white hover:shadow-brutal-sm'"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <button
                type="button"
                class="min-w-0 text-left"
                @click="emit('select-roster', roster.id)"
              >
                <h3 class="truncate text-lg font-semibold text-navy">
                  {{ roster.name }}
                </h3>
                <p class="mt-1 text-sm text-navy/70">
                  {{ roster.students.length }} elever
                </p>
              </button>
              <button
                type="button"
                class="btn-ghost border-navy/30 bg-canvas shadow-none"
                @click="emit('edit-roster', roster)"
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
            class="border p-4 transition-shadow"
            :class="selectedTemplateId === template.id ? 'border-burgundy bg-burgundy/10 shadow-brutal-sm' : 'border-navy/20 bg-white hover:shadow-brutal-sm'"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <button
                type="button"
                class="min-w-0 text-left"
                @click="emit('select-template', template.id)"
              >
                <h3 class="truncate text-lg font-semibold text-navy">
                  {{ template.name }}
                </h3>
                <p class="mt-1 text-sm text-navy/70">
                  {{ template.seats.length }} platser · {{ template.fixtures.length }} fixturer
                </p>
              </button>
              <button
                type="button"
                class="btn-ghost border-navy/30 bg-canvas shadow-none"
                @click="emit('edit-template', template)"
              >
                Redigera
              </button>
            </div>
          </article>
        </div>
      </article>
    </div>

    <div class="flex justify-center border-t border-navy/20 pt-4">
      <button
        type="button"
        class="btn-cta px-8 py-4 text-sm"
        :disabled="!canStartPlanning"
        @click="emit('start-planning')"
      >
        Öppna planeringsytan
      </button>
    </div>
  </section>
</template>
