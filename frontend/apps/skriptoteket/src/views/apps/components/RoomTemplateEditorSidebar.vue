<script setup lang="ts">
/**
 * Room-template editor sidebar.
 *
 * This component renders the editor's name field, room-size controls, tool
 * palette, and teacher-facing usage help while leaving placement state in the
 * extracted editor composable.
 */

import { computed } from "vue";

import type { BuilderTool } from "../roomTemplateEditorDomain";
import type { RoomFixturePaletteEntry, RoomGridDimensions } from "../roomFixtureLayout";

const props = defineProps<{
  name: string;
  selectedTool: BuilderTool;
  seatCount: number;
  roomGrid: RoomGridDimensions;
  canShrinkCols: boolean;
  canShrinkRows: boolean;
  roomFixturePalette: RoomFixturePaletteEntry[];
}>();

const emit = defineEmits<{
  (e: "update:name", value: string): void;
  (e: "update:selectedTool", value: BuilderTool): void;
  (e: "resize-room", payload: { axis: "cols" | "rows"; delta: 1 | -1 }): void;
  (e: "clear-room"): void;
}>();

type RoomEditorToolEntry = {
  id: BuilderTool;
  label: string;
  helpText: string;
};

const toolEntries = computed<RoomEditorToolEntry[]>(() => [
  {
    id: "seat",
    label: "Sittplats",
    helpText: "Klicka i rutnätet för att lägga till eller ta bort en sittplats.",
  },
  ...props.roomFixturePalette.map((fixture) => ({
    id: fixture.type,
    label: fixture.label,
    helpText: fixture.placementKind === "wall"
      ? "Peka mot en vägg och klicka för att placera objektet där förhandsvisningen visar."
      : "Peka i rutnätet och klicka för att placera objektet där det får plats.",
  })),
  {
    id: "erase",
    label: "Sudda",
    helpText: "Klicka på en sittplats eller ett objekt för att ta bort det från klassrummet.",
  },
]);
const selectedToolEntry = computed<RoomEditorToolEntry>(() => {
  return toolEntries.value.find((tool) => tool.id === props.selectedTool) ?? toolEntries.value[0]!;
});

function updateNameFromEvent(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }
  emit("update:name", target.value);
}
</script>

<template>
  <aside
    class="space-y-5 xl:sticky xl:top-4 xl:self-start xl:max-h-[calc(100svh-10rem)] xl:overflow-y-auto"
    data-test="room-template-editor-sidebar"
  >
    <div class="space-y-1">
      <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
        Klassrummets namn
      </label>
      <input
        :value="name"
        type="text"
        placeholder="Till exempel Sal 304"
        class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
        @input="updateNameFromEvent"
      >
    </div>

    <div class="border border-navy bg-panel p-4 shadow-brutal-sm">
      <div class="mb-3 flex items-end justify-between gap-3">
        <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
          Storlek
        </h3>
        <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          {{ roomGrid.cols }} × {{ roomGrid.rows }}
        </span>
      </div>

      <div class="grid gap-3">
        <div class="flex items-center justify-between gap-3">
          <span class="text-sm text-navy/70">Bredd</span>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="btn-ghost planner-btn-ghost-canvas planner-btn-ghost-compact planner-btn-disabled-soft"
              :disabled="!canShrinkCols"
              @click="emit('resize-room', { axis: 'cols', delta: -1 })"
            >
              −
            </button>
            <button
              type="button"
              class="btn-ghost planner-btn-ghost-canvas planner-btn-ghost-compact"
              @click="emit('resize-room', { axis: 'cols', delta: 1 })"
            >
              +
            </button>
          </div>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="text-sm text-navy/70">Höjd</span>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="btn-ghost planner-btn-ghost-canvas planner-btn-ghost-compact planner-btn-disabled-soft"
              :disabled="!canShrinkRows"
              @click="emit('resize-room', { axis: 'rows', delta: -1 })"
            >
              −
            </button>
            <button
              type="button"
              class="btn-ghost planner-btn-ghost-canvas planner-btn-ghost-compact"
              @click="emit('resize-room', { axis: 'rows', delta: 1 })"
            >
              +
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="border border-navy bg-panel p-4 shadow-brutal-sm">
      <div class="mb-3 flex items-end justify-between gap-3">
        <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
          Verktyg
        </h3>
        <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          {{ seatCount }} sittplatser
        </span>
      </div>

      <div
        class="grid gap-2"
        data-test="room-template-tool-buttons"
      >
        <button
          v-for="tool in toolEntries"
          :key="tool.id"
          type="button"
          class="btn-ghost planner-btn-ghost justify-start"
          :class="selectedTool === tool.id ? 'planner-choice-button-active' : 'planner-choice-button-idle'"
          :data-test="`room-template-tool-${tool.id}`"
          @click="emit('update:selectedTool', tool.id)"
        >
          {{ tool.label }}
        </button>
      </div>

      <div class="planner-tool-rail-section">
        <p
          class="planner-tool-rail-meta"
          data-test="room-template-selected-tool-meta"
        >
          Aktivt verktyg · {{ selectedToolEntry.label }}
        </p>
        <p
          class="mt-2 text-xs leading-relaxed text-navy/70"
          data-test="room-template-selected-tool-help"
        >
          {{ selectedToolEntry.helpText }}
        </p>
        <button
          type="button"
          data-test="builder-clear-room"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-sm mt-2.5 w-full justify-center"
          @click="emit('clear-room')"
        >
          Rensa
        </button>
      </div>
    </div>

    <div class="border border-navy bg-canvas p-4 shadow-brutal-sm">
      <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
        Så här gör du
      </h3>
      <p class="mt-2 text-sm leading-relaxed text-navy/70">
        Välj ett verktyg och för pekaren över rutnätet för att se hur objektet hamnar innan du klickar. Möbler och andra objekt kan inte överlappa sittplatser eller varandra.
      </p>
    </div>
  </aside>
</template>
