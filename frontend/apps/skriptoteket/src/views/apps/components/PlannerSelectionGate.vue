<script setup lang="ts">
/**
 * Planner selection gate.
 *
 * This component renders the class-first landing surface for Klassrumskartan.
 * It keeps the top-level resumable CTA, class selection, and secondary roster
 * and classroom management outside the class workspace and live planner shell.
 */

import type { ResumablePlanDraft, RoomTemplate, Roster } from "../classroomPlannerTypes";

defineProps<{
  availableRosters: Roster[];
  availableTemplates: RoomTemplate[];
  selectedRosterId: string | null;
  resumableDraft: ResumablePlanDraft | null;
  isLoadingCatalog: boolean;
}>();

const emit = defineEmits<{
  (e: "select-roster", rosterId: string): void;
  (e: "create-roster"): void;
  (e: "edit-roster", roster: Roster): void;
  (e: "create-template"): void;
  (e: "edit-template", template: RoomTemplate): void;
  (e: "resume-draft"): void;
  (e: "dismiss-resumable-draft"): void;
}>();
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
            Välj klass först
          </h2>
        </div>
        <div class="text-sm text-navy/70">
          Fortsätt senaste utkastet direkt eller öppna en klassarbetsyta för att välja nästa steg.
        </div>
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
            {{ resumableDraft.roster_name }} · {{ resumableDraft.template_name ?? "Utan klassrum" }}
          </div>
        </div>
        <div class="flex flex-wrap gap-2 md:justify-end">
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-white shadow-none"
            aria-label="Stäng senaste utkastet"
            @click="emit('dismiss-resumable-draft')"
          >
            Stäng
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
              1. Klasser
            </p>
            <h2 class="font-serif text-2xl text-navy">
              Öppna en klass
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
                  {{ roster.students.length }} elever · öppna klassarbetsytan
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
              Hantera klassrum
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
            class="border border-navy/20 bg-white p-4 transition-shadow hover:shadow-brutal-sm"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div class="min-w-0 text-left">
                <h3 class="truncate text-lg font-semibold text-navy">
                  {{ template.name }}
                </h3>
                <p class="mt-1 text-sm text-navy/70">
                  {{ template.seats.length }} sittplatser
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
