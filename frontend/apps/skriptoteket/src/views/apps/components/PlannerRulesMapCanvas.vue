<script setup lang="ts">
/**
 * Rules-workspace map canvas.
 *
 * This component renders the classroom geometry for both `Planeringskarta`
 * and `Sittschema`, mapping rule selection by `studentId` while leaving all
 * persistence and rule mutation logic to the planner store.
 */

import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import type { RoomTemplate, SeatAssignment, Student } from "../classroomPlannerTypes";
import {
  sortSeatsByReadingOrder,
  sortStudentsAlphabetically,
} from "../classroomPlannerSmartRulePresentation";
import { getRoomSurfaceMetrics } from "../roomFixturePresentation";
import { normalizeRoomGrid } from "../roomFixtureLayout";
import { useRoomViewportZoom } from "../useRoomViewportZoom";
import RoomSceneSurface from "./RoomSceneSurface.vue";
import PlannerRulesSeatNode from "./PlannerRulesSeatNode.vue";

type RulesMapView = "planning_map" | "seating_arrangement";

const props = withDefaults(defineProps<{
  mapView: RulesMapView;
  template?: RoomTemplate | null;
  students?: Student[];
  studentsById?: Record<string, Student | undefined>;
  seatAssignments?: SeatAssignment[];
  selectedStudentId?: string | null;
  pendingSelectedStudentIds?: string[];
  smartRuleMarkersByStudentId?: Record<string, string[]>;
}>(), {
  template: null,
  students: () => [],
  studentsById: () => ({}),
  seatAssignments: () => [],
  selectedStudentId: null,
  pendingSelectedStudentIds: () => [],
  smartRuleMarkersByStudentId: () => ({}),
});

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
}>();

const roomGrid = computed(() => normalizeRoomGrid(props.template));
const roomSurfaceMetrics = computed(() => getRoomSurfaceMetrics(roomGrid.value));
const {
  scale: canvasScale,
  scaledSurfaceStyle,
  scalePercent,
  setViewportSize,
  zoomOut,
  zoomIn,
  resetZoom,
} = useRoomViewportZoom(roomSurfaceMetrics, {
  resetSource: computed(() => `${props.mapView}:${props.template?.id ?? "no-template"}`),
});
const canvasViewport = ref<HTMLElement | null>(null);
const viewportWidth = ref(0);

const orderedSeats = computed(() => sortSeatsByReadingOrder(props.template?.seats ?? []));
const orderedPlanningStudents = computed(() => sortStudentsAlphabetically(props.students));
const planningStudentsBySeatId = computed<Record<string, Student | null>>(() => {
  const projected: Record<string, Student | null> = {};
  orderedSeats.value.forEach((seat, index) => {
    projected[seat.id] = orderedPlanningStudents.value[index] ?? null;
  });
  return projected;
});
const seatingStudentsBySeatId = computed<Record<string, Student | null>>(() => {
  const projected: Record<string, Student | null> = {};
  for (const seat of props.template?.seats ?? []) {
    projected[seat.id] = null;
  }
  for (const assignment of props.seatAssignments) {
    const student = props.studentsById[assignment.student_id] ?? null;
    if (student && projected[assignment.seat_id] !== undefined) {
      projected[assignment.seat_id] = student;
    }
  }
  return projected;
});
const projectedStudentsBySeatId = computed<Record<string, Student | null>>(() => {
  return props.mapView === "planning_map"
    ? planningStudentsBySeatId.value
    : seatingStudentsBySeatId.value;
});
const unplacedStudents = computed(() => {
  if (props.mapView === "planning_map") {
    return orderedPlanningStudents.value.slice(orderedSeats.value.length);
  }

  const placedStudentIds = new Set(props.seatAssignments.map((assignment) => assignment.student_id));
  return props.students.filter((student) => !placedStudentIds.has(student.id));
});
const shouldCenterSurface = computed(() => {
  const scaledWidth = Number.parseFloat(scaledSurfaceStyle.value.width ?? "0");
  return viewportWidth.value <= 0 || scaledWidth <= viewportWidth.value;
});

function syncViewportSize(): void {
  const element = canvasViewport.value;
  if (!element) {
    setViewportSize({ width: 0, height: 0 });
    return;
  }

  setViewportSize({
    width: element.clientWidth,
    height: element.clientHeight,
  });
  viewportWidth.value = element.clientWidth;
}

let canvasViewportObserver: ResizeObserver | null = null;

onMounted(() => {
  syncViewportSize();
  if (typeof ResizeObserver === "undefined") {
    return;
  }

  canvasViewportObserver = new ResizeObserver(() => {
    syncViewportSize();
  });

  if (canvasViewport.value) {
    canvasViewportObserver.observe(canvasViewport.value);
  }
});

onBeforeUnmount(() => {
  canvasViewportObserver?.disconnect();
  canvasViewportObserver = null;
});

function selectionOrder(studentId: string): number | null {
  const index = props.pendingSelectedStudentIds.indexOf(studentId);
  return index >= 0 ? index + 1 : null;
}

function isStudentSelected(studentId: string): boolean {
  return props.selectedStudentId === studentId || props.pendingSelectedStudentIds.includes(studentId);
}
</script>

<template>
  <section class="border border-navy bg-white p-4 shadow-brutal-sm">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-navy/20 pb-3">
      <p class="text-sm text-navy/70">
        {{
          mapView === "planning_map"
            ? "Planeringskarta använder alfabetisk placering på klassrummets riktiga geometri."
            : "Sittschema visar den aktuella sittplaceringen utan att ändra den på kartan."
        }}
      </p>
      <div class="flex flex-wrap items-center gap-2">
        <span class="border border-navy/20 bg-white px-2 py-1 text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          {{ scalePercent }}%
        </span>
        <button
          type="button"
          class="btn-ghost border-navy/30 bg-white px-3 py-1 shadow-none"
          data-test="rules-zoom-out"
          @click="zoomOut"
        >
          −
        </button>
        <button
          type="button"
          class="btn-ghost border-navy/30 bg-white px-3 py-1 shadow-none"
          data-test="rules-zoom-in"
          @click="zoomIn"
        >
          +
        </button>
        <button
          type="button"
          class="btn-ghost border-navy/30 bg-white px-3 py-1 shadow-none"
          data-test="rules-zoom-fit"
          @click="resetZoom"
        >
          Anpassa
        </button>
      </div>
    </div>

    <div
      v-if="!template"
      class="mt-4 border border-dashed border-navy/30 bg-canvas px-6 py-8 text-center text-sm leading-relaxed text-navy/70"
      data-test="rules-map-empty-state"
    >
      Välj ett klassrum i sittplatser om du vill arbeta med regler direkt på klassrummets geometri.
    </div>

    <div
      v-else
      ref="canvasViewport"
      data-test="rules-map-canvas"
      class="mt-4 min-h-[560px] overflow-auto border border-navy/20 bg-white p-4"
    >
      <div
        class="flex min-h-full min-w-full items-start"
        :class="shouldCenterSurface ? 'justify-center' : 'justify-start'"
      >
        <div
          class="relative shrink-0"
          :style="scaledSurfaceStyle"
        >
          <div
            class="absolute left-0 top-0"
            :style="{
              transform: `scale(${canvasScale})`,
              transformOrigin: 'top left',
            }"
          >
            <RoomSceneSurface
              :grid="roomGrid"
              :seats="template.seats"
              :fixtures="template.fixtures"
              :show-backdrop-grid="true"
              :render-seat-tokens="false"
            >
              <template #floor-overlay>
                <PlannerRulesSeatNode
                  v-for="seat in template.seats"
                  :key="seat.id"
                  :seat="seat"
                  :student="projectedStudentsBySeatId[seat.id]"
                  :selected="
                    projectedStudentsBySeatId[seat.id] !== null
                    && isStudentSelected(projectedStudentsBySeatId[seat.id]?.id ?? '')
                  "
                  :selection-order="
                    projectedStudentsBySeatId[seat.id] !== null
                      ? selectionOrder(projectedStudentsBySeatId[seat.id]?.id ?? '')
                      : null
                  "
                  :markers="
                    smartRuleMarkersByStudentId[projectedStudentsBySeatId[seat.id]?.id ?? ''] ?? []
                  "
                  :interactive="projectedStudentsBySeatId[seat.id] !== null"
                  @student-selected="emit('student-selected', $event)"
                />
              </template>
            </RoomSceneSurface>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="unplacedStudents.length > 0"
      class="mt-4 border border-navy/20 bg-canvas px-3 py-3"
      data-test="rules-map-unplaced"
    >
      <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
        Ej på kartan
      </p>
      <div class="mt-2 flex flex-wrap gap-2">
        <button
          v-for="student in unplacedStudents"
          :key="student.id"
          type="button"
          class="border px-2 py-1 text-[11px] font-semibold"
          :class="
            isStudentSelected(student.id)
              ? 'border-burgundy bg-burgundy/10 text-burgundy'
              : 'border-navy/20 bg-white text-navy/70'
          "
          :data-test="`rules-unplaced-student-${student.id}`"
          @click="emit('student-selected', student.id)"
        >
          {{ student.display_name }}
        </button>
      </div>
    </div>
  </section>
</template>
