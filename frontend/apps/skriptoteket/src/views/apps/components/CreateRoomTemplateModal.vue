<script setup lang="ts">
/**
 * Room template create/edit modal.
 *
 * This modal manages reusable classroom layouts for the planner. It lets the
 * teacher place seats and room fixtures on a coarse grid so the live planner
 * canvas, future PDF exports, and classroom snapshots share one visual source
 * of truth.
 */

import { computed, ref, watch } from "vue";

import { apiDelete, apiPost, apiPut } from "../../../api/client";
import {
  roomFixturePalette,
  type RoomFixture,
  type RoomFixtureType,
  type RoomTemplate,
  type Seat,
} from "../classroomPlannerTypes";

type BuilderTool = "seat" | "erase" | RoomFixtureType;

type FixturePlacement = {
  id: string;
  type: RoomFixtureType;
  col: number;
  row: number;
  width: number;
  height: number;
  label: string;
};

const GRID_COLS = 14;
const GRID_ROWS = 9;
const GRID_UNIT = 96;

const props = defineProps<{
  template?: RoomTemplate | null;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "saved", template: RoomTemplate): void;
  (e: "deleted", templateId: string): void;
}>();

const name = ref("");
const selectedTool = ref<BuilderTool>("seat");
const seatCells = ref<string[]>([]);
const fixtures = ref<FixturePlacement[]>([]);
const isSubmitting = ref(false);
const isDeleting = ref(false);
const error = ref<string | null>(null);

const isEditing = computed(() => Boolean(props.template));

function seatKey(row: number, col: number): string {
  return `${row}:${col}`;
}

function isSeatAt(row: number, col: number): boolean {
  return seatCells.value.includes(seatKey(row, col));
}

function findFixtureAt(row: number, col: number): FixturePlacement | null {
  return (
    fixtures.value.find((fixture) => {
      return (
        row >= fixture.row &&
        row < fixture.row + fixture.height &&
        col >= fixture.col &&
        col < fixture.col + fixture.width
      );
    }) ?? null
  );
}

function fixturePaletteEntry(type: RoomFixtureType) {
  return roomFixturePalette.find((entry) => entry.type === type);
}

function buildFixtureLabel(type: RoomFixtureType): string {
  return fixturePaletteEntry(type)?.label ?? type;
}

function fixtureFits(row: number, col: number, width: number, height: number): boolean {
  if (col + width > GRID_COLS || row + height > GRID_ROWS) {
    return false;
  }
  for (let currentRow = row; currentRow < row + height; currentRow += 1) {
    for (let currentCol = col; currentCol < col + width; currentCol += 1) {
      if (isSeatAt(currentRow, currentCol) || findFixtureAt(currentRow, currentCol)) {
        return false;
      }
    }
  }
  return true;
}

function removeFixtureById(fixtureId: string): void {
  fixtures.value = fixtures.value.filter((fixture) => fixture.id !== fixtureId);
}

function toggleGridCell(row: number, col: number): void {
  error.value = null;
  const occupiedFixture = findFixtureAt(row, col);

  if (selectedTool.value === "erase") {
    if (occupiedFixture) {
      removeFixtureById(occupiedFixture.id);
      return;
    }
    seatCells.value = seatCells.value.filter((value) => value !== seatKey(row, col));
    return;
  }

  if (selectedTool.value === "seat") {
    if (occupiedFixture) {
      error.value = "Ta bort fixturen först om du vill lägga en plats där.";
      return;
    }
    const key = seatKey(row, col);
    seatCells.value = isSeatAt(row, col)
      ? seatCells.value.filter((value) => value !== key)
      : [...seatCells.value, key];
    return;
  }

  const paletteItem = fixturePaletteEntry(selectedTool.value);
  if (!paletteItem) {
    return;
  }
  if (!fixtureFits(row, col, paletteItem.width, paletteItem.height)) {
    error.value = "Fixturen får inte plats där eller krockar med befintlig möblering.";
    return;
  }

  fixtures.value = [
    ...fixtures.value,
    {
      id: `${selectedTool.value}-${crypto.randomUUID().slice(0, 8)}`,
      type: selectedTool.value,
      row,
      col,
      width: paletteItem.width,
      height: paletteItem.height,
      label: paletteItem.label,
    },
  ];
}

watch(
  () => props.template,
  (template) => {
    name.value = template?.name ?? "";
    seatCells.value =
      template?.seats.map((seat) => seatKey(Math.round(seat.y / GRID_UNIT), Math.round(seat.x / GRID_UNIT))) ??
      [];
    fixtures.value =
      template?.fixtures.map((fixture) => ({
        id: fixture.id,
        type: fixture.type,
        row: Math.round(fixture.y / GRID_UNIT),
        col: Math.round(fixture.x / GRID_UNIT),
        width: Math.max(1, Math.round(fixture.width / GRID_UNIT)),
        height: Math.max(1, Math.round(fixture.height / GRID_UNIT)),
        label: fixture.label ?? buildFixtureLabel(fixture.type),
      })) ?? [];
    error.value = null;
    selectedTool.value = "seat";
  },
  { immediate: true },
);

const parsedSeats = computed<Seat[]>(() => {
  return seatCells.value
    .map((value) => {
      const [row, col] = value.split(":").map(Number);
      return { row, col };
    })
    .sort((left, right) => (left.row - right.row) || (left.col - right.col))
    .map((cell, index) => ({
      id: `seat-${index + 1}`,
      x: cell.col * GRID_UNIT,
      y: cell.row * GRID_UNIT,
      zone: null,
    }));
});

const parsedFixtures = computed<RoomFixture[]>(() => {
  return fixtures.value.map((fixture) => ({
    id: fixture.id,
    type: fixture.type,
    x: fixture.col * GRID_UNIT,
    y: fixture.row * GRID_UNIT,
    width: fixture.width * GRID_UNIT,
    height: fixture.height * GRID_UNIT,
    label: fixture.label,
  }));
});

const isValid = computed(() => {
  return name.value.trim().length > 0 && parsedSeats.value.length > 0;
});

async function submit(): Promise<void> {
  if (!isValid.value) {
    return;
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    const payload = {
      name: name.value.trim(),
      seats: parsedSeats.value,
      fixtures: parsedFixtures.value,
    };
    const response = isEditing.value && props.template
      ? await apiPut<RoomTemplate>(
          `/api/v1/apps/classroom.group-seating-studio/templates/${props.template.id}`,
          payload,
        )
      : await apiPost<RoomTemplate>(
          "/api/v1/apps/classroom.group-seating-studio/templates",
          payload,
        );
    emit("saved", response);
  } catch (submitError: unknown) {
    error.value = submitError instanceof Error ? submitError.message : "Kunde inte spara klassrummet.";
  } finally {
    isSubmitting.value = false;
  }
}

async function removeTemplate(): Promise<void> {
  if (!props.template) {
    return;
  }

  isDeleting.value = true;
  error.value = null;

  try {
    await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/templates/${props.template.id}`);
    emit("deleted", props.template.id);
  } catch (deleteError: unknown) {
    error.value = deleteError instanceof Error ? deleteError.message : "Kunde inte radera klassrummet.";
  } finally {
    isDeleting.value = false;
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-y-auto p-4">
    <button
      type="button"
      aria-label="Stäng modal"
      class="fixed inset-0 bg-navy/70"
      @click="emit('close')"
    />
    <div class="relative flex min-h-full items-start justify-center py-4">
      <div class="flex max-h-[calc(100vh-2rem)] w-full max-w-6xl flex-col border border-navy bg-white shadow-brutal">
        <div class="flex flex-col gap-4 border-b border-navy/20 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div class="space-y-1 px-6 pt-6 md:px-8 md:pt-8">
            <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Klassrumsmallar
            </p>
            <h2 class="font-serif text-2xl text-navy">
              {{ isEditing ? "Redigera klassrum" : "Nytt klassrum" }}
            </h2>
            <p class="max-w-[40rem] text-sm leading-relaxed text-navy/70">
              Placera ut elevplatser och viktiga rumsdetaljer så planeringen får en tydlig whiteboard-liknande översikt redan nu och en bättre exportyta senare.
            </p>
          </div>
          <button
            type="button"
            class="mb-0 mr-6 mt-6 btn-ghost h-[32px] w-[32px] self-start px-0 py-0 shadow-none border-navy/30 bg-canvas md:mr-8 md:mt-8 lg:self-auto"
            @click="emit('close')"
          >
            ×
          </button>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto px-6 pb-6 pt-4 md:px-8 md:pb-8">
          <div
            v-if="error"
            class="system-message system-message-error"
          >
            <div class="system-message-content">
              {{ error }}
            </div>
          </div>

          <div class="mt-6 grid gap-6 xl:grid-cols-[260px_minmax(0,1fr)]">
            <aside class="space-y-5">
              <div class="space-y-1">
                <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Klassrummets namn
                </label>
                <input
                  v-model="name"
                  type="text"
                  placeholder="Till exempel Sal 304"
                  class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
                >
              </div>

              <div class="border border-navy bg-canvas p-4 shadow-brutal-sm">
                <div class="mb-3 flex items-end justify-between gap-3">
                  <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                    Verktyg
                  </h3>
                  <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                    {{ parsedSeats.length }} platser
                  </span>
                </div>

                <div class="grid gap-2">
                  <button
                    type="button"
                    class="btn-ghost justify-start shadow-none"
                    :class="selectedTool === 'seat' ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-white'"
                    @click="selectedTool = 'seat'"
                  >
                    Placera plats
                  </button>
                  <button
                    v-for="fixture in roomFixturePalette"
                    :key="fixture.type"
                    type="button"
                    class="btn-ghost justify-start shadow-none"
                    :class="selectedTool === fixture.type ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-white'"
                    @click="selectedTool = fixture.type"
                  >
                    {{ fixture.label }}
                  </button>
                  <button
                    type="button"
                    class="btn-ghost justify-start shadow-none"
                    :class="selectedTool === 'erase' ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-white'"
                    @click="selectedTool = 'erase'"
                  >
                    Sudda
                  </button>
                </div>
              </div>

              <div class="border border-navy bg-white p-4 shadow-brutal-sm">
                <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                  Lägesnotering
                </h3>
                <p class="mt-2 text-sm leading-relaxed text-navy/70">
                  Välj ett verktyg och klicka i rutnätet. Fixturer upptar flera rutor och kan inte överlappa platser eller andra fixturer.
                </p>
              </div>
            </aside>

            <section class="space-y-4">
              <div class="overflow-auto border border-navy bg-canvas p-4 shadow-brutal-sm">
                <div
                  class="relative grid gap-1"
                  :style="{ gridTemplateColumns: `repeat(${GRID_COLS}, minmax(0, 1fr))`, minWidth: `${GRID_COLS * 52}px` }"
                >
                  <template
                    v-for="row in GRID_ROWS"
                    :key="`row-${row}`"
                  >
                    <button
                      v-for="col in GRID_COLS"
                      :key="`cell-${row}-${col}`"
                      type="button"
                      class="relative aspect-square border text-[9px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] transition-colors"
                      :class="{
                        'border-navy/20 bg-white hover:border-navy/50': !isSeatAt(row - 1, col - 1) && !findFixtureAt(row - 1, col - 1),
                        'border-navy bg-navy text-canvas': isSeatAt(row - 1, col - 1),
                        'border-burgundy bg-burgundy/15 text-burgundy': findFixtureAt(row - 1, col - 1)?.type === 'teacher_desk',
                        'border-navy bg-warning/20 text-navy': findFixtureAt(row - 1, col - 1)?.type === 'whiteboard',
                        'border-navy bg-canvas text-navy/70': findFixtureAt(row - 1, col - 1)?.type === 'window',
                        'border-navy bg-success/20 text-navy': findFixtureAt(row - 1, col - 1)?.type === 'door',
                      }"
                      @click="toggleGridCell(row - 1, col - 1)"
                    >
                      <span v-if="findFixtureAt(row - 1, col - 1) && findFixtureAt(row - 1, col - 1)?.row === row - 1 && findFixtureAt(row - 1, col - 1)?.col === col - 1">
                        {{ findFixtureAt(row - 1, col - 1)?.label }}
                      </span>
                    </button>
                  </template>
                </div>
              </div>

              <details class="border border-navy bg-white p-4 shadow-brutal-sm">
                <summary class="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3">
                  <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                    Förhandsvisning
                  </h3>
                  <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                    {{ parsedFixtures.length }} fixturer
                  </span>
                </summary>

                <div class="relative mt-4 overflow-auto border border-navy/20 bg-canvas p-4">
                  <div
                    class="relative"
                    :style="{ width: `${GRID_COLS * GRID_UNIT}px`, height: `${GRID_ROWS * GRID_UNIT}px` }"
                  >
                    <div
                      class="absolute inset-0 opacity-15"
                      style="background-image: linear-gradient(var(--huleedu-navy) 1px, transparent 1px), linear-gradient(90deg, var(--huleedu-navy) 1px, transparent 1px); background-size: 24px 24px;"
                    />

                    <div
                      v-for="fixture in parsedFixtures"
                      :key="fixture.id"
                      class="absolute flex items-center justify-center border text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)]"
                      :class="{
                        'border-navy bg-warning/25 text-navy': fixture.type === 'whiteboard',
                        'border-burgundy bg-burgundy/10 text-burgundy': fixture.type === 'teacher_desk',
                        'border-navy bg-white text-navy/70': fixture.type === 'window',
                        'border-success bg-success/20 text-navy': fixture.type === 'door',
                      }"
                      :style="{ left: `${fixture.x}px`, top: `${fixture.y}px`, width: `${fixture.width}px`, height: `${fixture.height}px` }"
                    >
                      {{ fixture.label }}
                    </div>

                    <div
                      v-for="seat in parsedSeats"
                      :key="seat.id"
                      class="absolute flex h-[72px] w-[72px] items-center justify-center border border-navy bg-white text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] shadow-brutal-sm"
                      :style="{ left: `${seat.x + 12}px`, top: `${seat.y + 12}px` }"
                    >
                      {{ seat.id }}
                    </div>
                  </div>
                </div>
              </details>
            </section>
          </div>
        </div>
        <div class="sticky bottom-0 flex flex-col gap-3 border-t border-navy/20 bg-white px-6 py-4 sm:flex-row sm:items-center sm:justify-between md:px-8">
          <div>
            <button
              v-if="isEditing"
              type="button"
              class="btn-ghost border-burgundy/40 bg-white text-burgundy"
              :disabled="isDeleting"
              @click="removeTemplate"
            >
              {{ isDeleting ? "Raderar..." : "Radera klassrum" }}
            </button>
          </div>
          <div class="flex flex-wrap justify-end gap-3">
            <button
              type="button"
              class="btn-ghost border-navy/30 bg-canvas shadow-none"
              @click="emit('close')"
            >
              Avbryt
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="!isValid || isSubmitting"
              @click="submit"
            >
              {{ isSubmitting ? "Sparar..." : isEditing ? "Spara klassrum" : "Skapa klassrum" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
