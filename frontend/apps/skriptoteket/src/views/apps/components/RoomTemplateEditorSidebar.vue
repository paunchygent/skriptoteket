<script setup lang="ts">
/**
 * Room-template editor sidebar.
 *
 * This component renders the editor's name field, room-size controls, tool
 * palette, and teacher-facing usage help while leaving placement state in the
 * extracted editor composable.
 */

import type { BuilderTool } from "../roomTemplateEditorDomain";
import type { RoomFixturePaletteEntry, RoomGridDimensions } from "../roomFixtureLayout";

defineProps<{
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
</script>

<template>
  <aside class="space-y-5">
    <div class="space-y-1">
      <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
        Klassrummets namn
      </label>
      <input
        :value="name"
        type="text"
        placeholder="Till exempel Sal 304"
        class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
        @input="emit('update:name', ($event.target as HTMLInputElement).value)"
      >
    </div>

    <div class="border border-navy bg-white p-4 shadow-brutal-sm">
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

    <div class="border border-navy bg-canvas p-4 shadow-brutal-sm">
      <div class="mb-3 flex items-end justify-between gap-3">
        <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
          Verktyg
        </h3>
        <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          {{ seatCount }} sittplatser
        </span>
      </div>

      <div class="grid gap-2">
        <button
          type="button"
          class="btn-ghost planner-btn-ghost justify-start"
          :class="selectedTool === 'seat' ? 'planner-tool-select-active' : 'planner-tool-select-idle'"
          @click="emit('update:selectedTool', 'seat')"
        >
          Placera plats
        </button>
        <button
          v-for="fixture in roomFixturePalette"
          :key="fixture.type"
          type="button"
          class="btn-ghost planner-btn-ghost justify-start"
          :class="selectedTool === fixture.type ? 'planner-tool-select-active' : 'planner-tool-select-idle'"
          @click="emit('update:selectedTool', fixture.type)"
        >
          {{ fixture.label }}
        </button>
        <button
          type="button"
          class="btn-ghost planner-btn-ghost justify-start"
          :class="selectedTool === 'erase' ? 'planner-tool-select-active' : 'planner-tool-select-idle'"
          @click="emit('update:selectedTool', 'erase')"
        >
          Sudda
        </button>
        <button
          type="button"
          data-test="builder-clear-room"
          class="btn-ghost planner-btn-ghost justify-start"
          @click="emit('clear-room')"
        >
          Rensa
        </button>
      </div>
    </div>

    <div class="border border-navy bg-white p-4 shadow-brutal-sm">
      <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
        Så här gör du
      </h3>
      <p class="mt-2 text-sm leading-relaxed text-navy/70">
        Välj ett verktyg och för pekaren över rutnätet för att se hur objektet hamnar innan du klickar. Möbler och andra objekt kan inte överlappa sittplatser eller varandra.
      </p>
    </div>
  </aside>
</template>
