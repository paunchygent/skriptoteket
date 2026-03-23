<script setup lang="ts">
/**
 * Class-first planner workspace.
 *
 * This component keeps the class workspace neutral on entry and relies on the
 * segmented toggle as the only way to enter groups or seating. The overview
 * therefore becomes a compact command surface for class and classroom
 * management instead of duplicating draft-history controls that belong to the
 * active planner workspace.
 */

import { computed, ref } from "vue";

import type { ClassWorkspaceSummary, RoomTemplate, Roster } from "../classroomPlannerTypes";
import { ROOM_GRID_UNIT, normalizeRoomGrid } from "../roomFixtureLayout";
import PlannerTopPanel from "./PlannerTopPanel.vue";

const CLASS_PREVIEW_NAME_LIMIT = 33;
const OVERVIEW_PREVIEW_HEIGHT_CLASS = "h-[20rem]";
const OVERVIEW_HEADER_HEIGHT_CLASS = "h-[6rem]";
const OVERVIEW_SELECTOR_HEIGHT_CLASS = "h-[4rem]";

const props = defineProps<{
  workspaceSummary: ClassWorkspaceSummary;
  availableRosters: Roster[];
  availableTemplates: RoomTemplate[];
  selectedRosterId: string | null;
  selectedTemplateId: string | null;
  isLoadingWorkspace: boolean;
}>();

const emit = defineEmits<{
  (e: "back-to-landing"): void;
  (e: "create-roster"): void;
  (e: "edit-roster"): void;
  (e: "delete-current-roster"): void;
  (e: "select-roster", rosterId: string): void;
  (e: "create-template"): void;
  (e: "select-template", templateId: string | null): void;
  (e: "edit-current-template"): void;
  (e: "delete-current-template"): void;
  (e: "open-grouping", payload: { templateId: string | null }): void;
  (e: "open-seating", payload: { templateId: string | null }): void;
}>();

const workspaceMode = ref<"overview" | "grouping" | "seating">("overview");
const selectedRoster = computed(() => {
  return props.availableRosters.find((roster) => roster.id === props.selectedRosterId) ?? null;
});
const selectedTemplate = computed(() => {
  return props.availableTemplates.find((template) => template.id === props.selectedTemplateId) ?? null;
});
const selectedRosterPreviewNames = computed(() => {
  const roster = selectedRoster.value;
  if (!roster) {
    return [];
  }

  const sortedNames = [...roster.students]
    .map((student) => student.display_name.trim())
    .filter((displayName) => displayName.length > 0)
    .sort((left, right) => {
      const leftFirstName = left.split(/\s+/)[0] ?? left;
      const rightFirstName = right.split(/\s+/)[0] ?? right;
      const firstNameComparison = leftFirstName.localeCompare(rightFirstName, "sv");
      if (firstNameComparison !== 0) {
        return firstNameComparison;
      }
      return left.localeCompare(right, "sv");
    });

  if (sortedNames.length <= CLASS_PREVIEW_NAME_LIMIT) {
    return sortedNames;
  }

  return [...sortedNames.slice(0, CLASS_PREVIEW_NAME_LIMIT), "..."];
});
const classPanelDescription = computed(() => {
  return "Förhandsgranska och hantera klasslistan här innan du går vidare till grupper eller sittplatser.";
});
const classroomPanelDescription = computed(() => {
  if (!selectedTemplate.value) {
    return "Välj ett klassrum här så att sittplatserna får tydlig kontext när du går vidare.";
  }
  return "Förhandsgranska och hantera klassrummet här innan du går vidare till sittplatser.";
});
const workspaceContextLabel = computed(() => {
  if (!selectedTemplate.value) {
    return "Klassöversikt · Inget klassrum valt";
  }
  return `Klassöversikt · Klassrum: ${selectedTemplate.value.name}`;
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
    emit("open-seating", { templateId: props.selectedTemplateId });
    workspaceMode.value = "overview";
  }
}

function selectRoster(event: Event): void {
  const nextRosterId = (event.target as HTMLSelectElement).value;
  if (nextRosterId && nextRosterId !== props.selectedRosterId) {
    emit("select-roster", nextRosterId);
  }
}

function selectTemplate(event: Event): void {
  const nextTemplateId = (event.target as HTMLSelectElement).value;
  emit("select-template", nextTemplateId.length > 0 ? nextTemplateId : null);
}

function buildSeatPreviewStyle(template: RoomTemplate, seatId: string): Record<string, string> {
  const grid = normalizeRoomGrid(template);
  const seat = template.seats.find((entry) => entry.id === seatId);
  if (!seat) {
    return {};
  }
  return {
    left: `${((seat.x + ROOM_GRID_UNIT / 2) / (grid.cols * ROOM_GRID_UNIT)) * 100}%`,
    top: `${((seat.y + ROOM_GRID_UNIT / 2) / (grid.rows * ROOM_GRID_UNIT)) * 100}%`,
  };
}

function buildFixturePreviewStyle(template: RoomTemplate, fixtureId: string): Record<string, string> {
  const grid = normalizeRoomGrid(template);
  const fixture = template.fixtures.find((entry) => entry.id === fixtureId);
  if (!fixture) {
    return {};
  }
  return {
    left: `${(fixture.x / (grid.cols * ROOM_GRID_UNIT)) * 100}%`,
    top: `${(fixture.y / (grid.rows * ROOM_GRID_UNIT)) * 100}%`,
    width: `${(fixture.width / (grid.cols * ROOM_GRID_UNIT)) * 100}%`,
    height: `${(fixture.height / (grid.rows * ROOM_GRID_UNIT)) * 100}%`,
  };
}
</script>

<template>
  <section class="space-y-4">
    <PlannerTopPanel
      :title="workspaceSummary.roster.name"
      :context-label="workspaceContextLabel"
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
          Här hanterar du klass och klassrum i ett kompakt arbetsflöde. Öppna Grupper eller Sittplatser i väljaren ovan när du vill fortsätta planeringen.
        </p>
      </div>

      <div class="grid gap-4 xl:grid-cols-2">
        <article
          class="grid grid-rows-[6rem_4rem_20rem_auto] gap-3 border border-navy/20 bg-canvas p-4"
        >
          <div :class="['grid h-full content-start grid-rows-[auto_auto_1fr] gap-2', OVERVIEW_HEADER_HEIGHT_CLASS]">
            <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Klass
            </p>
            <div class="flex flex-wrap items-baseline gap-2">
              <p class="text-xl font-semibold text-navy">
                {{ workspaceSummary.roster.name }}
              </p>
              <span class="text-[0.8rem] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55">
                {{ workspaceSummary.roster.student_count }} elever
              </span>
            </div>
            <p class="text-sm text-navy/70">
              {{ classPanelDescription }}
            </p>
          </div>

          <label :class="['grid h-full content-start gap-2 text-sm text-navy', OVERVIEW_SELECTOR_HEIGHT_CLASS]">
            <span class="font-semibold">Byt klass</span>
            <select
              class="w-full border border-navy/25 bg-white px-3 py-2 text-sm text-navy"
              :disabled="isLoadingWorkspace"
              :value="selectedRosterId ?? workspaceSummary.roster.id"
              data-test="overview-roster-select"
              @change="selectRoster"
            >
              <option
                v-for="roster in availableRosters"
                :key="roster.id"
                :value="roster.id"
              >
                {{ roster.name }}
              </option>
            </select>
          </label>

          <div
            :class="['relative overflow-hidden border border-navy/20 bg-white', OVERVIEW_PREVIEW_HEIGHT_CLASS]"
            data-test="overview-roster-preview"
          >
            <div
              v-if="selectedRoster && selectedRosterPreviewNames.length > 0"
              class="grid h-full grid-cols-3 content-start gap-x-4 gap-y-1 overflow-hidden p-4 text-[0.8rem] leading-5 text-navy/72"
            >
              <span
                v-for="name in selectedRosterPreviewNames"
                :key="name"
                class="truncate"
              >
                {{ name }}
              </span>
            </div>
            <div
              v-else
              class="flex h-full items-center justify-center p-4 text-center text-sm text-navy/55"
            >
              Välj en klasslista för att visa en kompakt elevöversikt här.
            </div>
          </div>

          <div class="grid gap-2 border-t border-navy/15 pt-2.5 md:grid-cols-3">
            <button
              type="button"
              class="btn-primary w-full justify-center"
              @click="emit('create-roster')"
            >
              Ny klasslista
            </button>
            <button
              type="button"
              class="btn-ghost w-full justify-center border-navy/30 bg-white shadow-none"
              @click="emit('edit-roster')"
            >
              Redigera klass
            </button>
            <button
              type="button"
              class="btn-ghost w-full justify-center border-navy/30 bg-white text-burgundy shadow-none disabled:text-navy/40"
              :disabled="!selectedRoster"
              data-test="overview-delete-roster"
              @click="emit('delete-current-roster')"
            >
              Ta bort klasslista
            </button>
          </div>
        </article>

        <article class="grid grid-rows-[6rem_4rem_20rem_auto] gap-3 border border-navy/20 bg-canvas p-4">
          <div :class="['grid h-full content-start grid-rows-[auto_auto_1fr] gap-2', OVERVIEW_HEADER_HEIGHT_CLASS]">
            <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Klassrum
            </p>
            <div class="flex flex-wrap items-baseline gap-2">
              <p class="text-xl font-semibold text-navy">
                {{ selectedTemplate?.name ?? "Inget klassrum valt" }}
              </p>
              <span
                v-if="selectedTemplate"
                class="text-[0.8rem] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55"
              >
                {{ selectedTemplate.seats.length }} platser
              </span>
            </div>
            <p class="text-sm text-navy/70">
              {{ classroomPanelDescription }}
            </p>
          </div>

          <label :class="['grid h-full content-start gap-2 text-sm text-navy', OVERVIEW_SELECTOR_HEIGHT_CLASS]">
            <span class="font-semibold">Välj klassrum</span>
            <select
              class="w-full border border-navy/25 bg-white px-3 py-2 text-sm text-navy"
              :disabled="isLoadingWorkspace"
              :value="selectedTemplateId ?? ''"
              data-test="overview-template-select"
              @change="selectTemplate"
            >
              <option value="">
                Utan klassrum
              </option>
              <option
                v-for="template in availableTemplates"
                :key="template.id"
                :value="template.id"
              >
                {{ template.name }}
              </option>
            </select>
          </label>

          <div
            v-if="selectedTemplate"
            class="space-y-3"
          >
            <div
              :class="['relative overflow-hidden border border-navy/20 bg-white', OVERVIEW_PREVIEW_HEIGHT_CLASS]"
              data-test="overview-classroom-preview"
            >
              <div class="absolute inset-2 border border-dashed border-navy/10" />
              <div
                v-for="fixture in selectedTemplate.fixtures"
                :key="fixture.id"
                class="absolute border border-navy/25 bg-navy/10"
                :style="buildFixturePreviewStyle(selectedTemplate, fixture.id)"
              />
              <div
                v-for="seat in selectedTemplate.seats"
                :key="seat.id"
                class="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-burgundy/40 bg-burgundy/70"
                :style="buildSeatPreviewStyle(selectedTemplate, seat.id)"
              />
            </div>
          </div>

          <div
            v-else
            :class="['flex items-center justify-center border border-dashed border-navy/25 bg-white px-4 py-8 text-center text-sm text-navy/55', OVERVIEW_PREVIEW_HEIGHT_CLASS]"
            data-test="overview-classroom-empty"
          >
            Välj ett klassrum i listan nedan för att visa en kompakt förhandsgranskning här.
          </div>

          <div class="grid gap-2 border-t border-navy/15 pt-2.5 md:grid-cols-3">
            <button
              type="button"
              class="btn-primary w-full justify-center"
              @click="emit('create-template')"
            >
              Nytt klassrum
            </button>
            <button
              type="button"
              class="btn-ghost w-full justify-center border-navy/30 bg-white shadow-none"
              :disabled="!selectedTemplate"
              @click="emit('edit-current-template')"
            >
              Redigera klassrum
            </button>
            <button
              type="button"
              class="btn-ghost w-full justify-center border-navy/30 bg-white text-burgundy shadow-none disabled:text-navy/40"
              :disabled="!selectedTemplate"
              data-test="overview-delete-template"
              @click="emit('delete-current-template')"
            >
              Ta bort klassrum
            </button>
          </div>
        </article>
      </div>
    </article>
  </section>
</template>
