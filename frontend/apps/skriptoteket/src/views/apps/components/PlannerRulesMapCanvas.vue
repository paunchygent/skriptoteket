<script setup lang="ts">
/**
 * Rules-workspace map canvas.
 *
 * This component renders the two rule-authoring views:
 * `Planeringskarta` as a stable abstract alphabetical planning layout and
 * `Sittschema` as the classroom-faithful seating projection. Rule selection
 * stays keyed by `studentId`, while persistence and mutation remain in the
 * planner store.
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import type { RoomTemplate, SeatAssignment, Student } from "../classroomPlannerTypes";
import UiSegmentedToggle, {
  type UiSegmentedToggleOption,
} from "../../../components/ui/UiSegmentedToggle.vue";
import { sortStudentsAlphabetically } from "../classroomPlannerSmartRulePresentation";
import { getRoomSurfaceMetrics } from "../roomFixturePresentation";
import { normalizeRoomGrid } from "../roomFixtureLayout";
import { useRoomViewportZoom } from "../useRoomViewportZoom";
import { ROOM_VIEWPORT_FRAME_PADDING } from "../roomBuilderViewport";
import RoomSceneSurface from "./RoomSceneSurface.vue";
import PlannerRulesSeatNode from "./PlannerRulesSeatNode.vue";

type RulesMapView = "planning_map" | "seating_arrangement";

const props = withDefaults(defineProps<{
  mapView: RulesMapView;
  rosterName?: string | null;
  canShowSeatingArrangement?: boolean;
  seatingArrangementUnavailableMessage?: string | null;
  template?: RoomTemplate | null;
  students?: Student[];
  studentsById?: Record<string, Student | undefined>;
  seatAssignments?: SeatAssignment[];
  selectedStudentId?: string | null;
  pendingSelectedStudentIds?: string[];
  smartRuleMarkersByStudentId?: Record<string, string[]>;
}>(), {
  rosterName: null,
  canShowSeatingArrangement: false,
  seatingArrangementUnavailableMessage: null,
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
  (e: "update:mapView", value: RulesMapView): void;
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

const isPlanningMap = computed(() => props.mapView === "planning_map");
const isNoClassroomState = computed(() => props.template === null);
const orderedPlanningStudents = computed(() => sortStudentsAlphabetically(props.students));
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
const surfaceStudents = computed(() => {
  if (isPlanningMap.value) {
    return orderedPlanningStudents.value;
  }

  const placedStudentIds = new Set(props.seatAssignments.map((assignment) => assignment.student_id));
  return sortStudentsAlphabetically(
    props.students.filter((student) => !placedStudentIds.has(student.id)),
  );
});
const selectedUnplacedStudentsCount = computed(() => {
  return surfaceStudents.value.filter((student) => isStudentSelected(student.id)).length;
});
const surfaceHeadingLabel = computed(() => {
  if (isPlanningMap.value) {
    return props.rosterName ?? "Klass";
  }
  return "Ej på karta";
});
const shouldCenterSurface = computed(() => {
  const paddedWidth = Number.parseFloat(scaledSurfaceStyle.value.width ?? "0")
    + (ROOM_VIEWPORT_FRAME_PADDING * 2);
  return viewportWidth.value <= 0 || paddedWidth <= viewportWidth.value;
});
const mapViewOptions = computed<UiSegmentedToggleOption[]>(() => {
  return [
    {
      value: "planning_map",
      label: "Planeringsvy",
      dataTest: "rules-map-view-planning",
    },
    {
      value: "seating_arrangement",
      label: "Klassrumsvy",
      dataTest: "rules-map-view-seating",
      disabled: !props.canShowSeatingArrangement,
      title: !props.canShowSeatingArrangement
        ? props.seatingArrangementUnavailableMessage ?? undefined
        : undefined,
    },
  ];
});

function syncViewportSize(): void {
  const element = canvasViewport.value;
  if (!element) {
    setViewportSize({ width: 0, height: 0 });
    viewportWidth.value = 0;
    return;
  }

  setViewportSize({
    width: element.clientWidth,
    height: element.clientHeight,
  });
  viewportWidth.value = element.clientWidth;
}

let canvasViewportObserver: ResizeObserver | null = null;

function bindCanvasViewportObserver(): void {
  canvasViewportObserver?.disconnect();
  canvasViewportObserver = null;
  syncViewportSize();
  if (typeof ResizeObserver === "undefined" || !canvasViewport.value) {
    return;
  }

  canvasViewportObserver = new ResizeObserver(() => {
    syncViewportSize();
  });

  canvasViewportObserver.observe(canvasViewport.value);
}

onMounted(() => {
  void nextTick(() => {
    bindCanvasViewportObserver();
  });
});

watch(
  [canvasViewport, () => props.mapView, () => props.template?.id ?? null],
  () => {
    void nextTick(() => {
      bindCanvasViewportObserver();
    });
  },
  { flush: "post" },
);

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

function updateMapView(value: string): void {
  if (value !== "planning_map" && value !== "seating_arrangement") {
    return;
  }
  if (value === props.mapView) {
    return;
  }
  emit("update:mapView", value);
}
</script>

<template>
  <section
    class="border border-navy bg-panel p-3 shadow-brutal-sm"
    data-test="rules-map-panel"
  >
    <div
      class="flex flex-wrap items-center justify-between gap-2 border-b border-navy/20 pb-2"
      data-test="rules-map-toolbar"
    >
      <UiSegmentedToggle
        :model-value="mapView"
        :options="mapViewOptions"
        aria-label="Välj kartvy för regler"
        density="compact"
        variant="subrail"
        width="auto"
        equalize-option-width
        :columns="2"
        data-test="rules-map-view-switch"
        @update:model-value="updateMapView"
      />

      <div class="flex flex-wrap items-center gap-2">
        <span
          data-test="rules-zoom-percent"
          class="border border-navy/20 bg-white px-2 py-1 text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60"
        >
          {{ scalePercent }}%
        </span>
        <button
          type="button"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-compact"
          data-test="rules-zoom-out"
          :disabled="isPlanningMap"
          @click="zoomOut"
        >
          −
        </button>
        <button
          type="button"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-compact"
          data-test="rules-zoom-in"
          :disabled="isPlanningMap"
          @click="zoomIn"
        >
          +
        </button>
        <button
          type="button"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-compact"
          data-test="rules-zoom-fit"
          :disabled="isPlanningMap"
          @click="resetZoom"
        >
          Anpassa
        </button>
      </div>
    </div>

    <div class="rules-map-view-stage">
      <Transition name="rules-map-view-swap">
        <div
          :key="mapView"
          class="rules-map-view-surface"
        >
          <div
            v-if="isNoClassroomState"
            class="mt-3 border border-dashed border-navy/30 bg-canvas px-5 py-6 text-center text-sm leading-relaxed text-navy/70"
            data-test="rules-map-empty-state"
          >
            Välj ett klassrum i arbetsytan Sittplatser och placera ut eleverna om du vill arbeta
            med regler direkt utifrån klassrummets möblering.
          </div>

          <div
            v-else-if="!isPlanningMap && template"
            ref="canvasViewport"
            data-test="rules-map-canvas"
            class="mt-3 min-h-[480px] overflow-auto border border-navy/20 bg-panel p-3"
          >
            <div
              data-test="rules-map-scroll-frame"
              class="flex min-h-full min-w-full items-start"
              :data-overflow-anchor="shouldCenterSurface ? 'center' : 'start'"
              :class="shouldCenterSurface ? 'justify-center' : 'justify-start'"
            >
              <div
                class="shrink-0 px-6 py-6"
                data-test="rules-map-surface-shell"
              >
                <div
                  class="relative"
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
                          :student="seatingStudentsBySeatId[seat.id]"
                          :selected="
                            seatingStudentsBySeatId[seat.id] !== null
                              && isStudentSelected(seatingStudentsBySeatId[seat.id]?.id ?? '')
                          "
                          :selection-order="
                            seatingStudentsBySeatId[seat.id] !== null
                              ? selectionOrder(seatingStudentsBySeatId[seat.id]?.id ?? '')
                              : null
                          "
                          :markers="
                            smartRuleMarkersByStudentId[seatingStudentsBySeatId[seat.id]?.id ?? ''] ?? []
                          "
                          :interactive="seatingStudentsBySeatId[seat.id] !== null"
                          @student-selected="emit('student-selected', $event)"
                        />
                      </template>
                    </RoomSceneSurface>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="surfaceStudents.length > 0"
            class="rules-unplaced-panel mt-3 border border-navy/20 bg-canvas px-3 py-3"
            data-test="rules-map-unplaced"
          >
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-navy/15 pb-2">
              <div class="space-y-1">
                <p
                  class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/70"
                  data-test="rules-map-surface-heading"
                >
                  {{ surfaceHeadingLabel }}
                </p>
                <p
                  class="text-xs font-medium text-navy/55"
                  data-test="rules-map-unplaced-count"
                >
                  {{ surfaceStudents.length }} elever
                </p>
              </div>
              <p
                v-if="selectedUnplacedStudentsCount > 0"
                class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-action"
                data-test="rules-map-unplaced-selected-count"
              >
                {{ selectedUnplacedStudentsCount }} valda
              </p>
            </div>
            <div
              class="rules-unplaced-grid mt-3"
              data-test="rules-map-unplaced-grid"
            >
              <button
                v-for="student in surfaceStudents"
                :key="student.id"
                type="button"
                class="rules-unplaced-student border text-left"
                :class="
                  isStudentSelected(student.id)
                    ? 'planner-choice-button-active-raised'
                    : 'planner-choice-button-idle'
                "
                :data-test="`rules-unplaced-student-${student.id}`"
                :aria-pressed="isStudentSelected(student.id) ? 'true' : 'false'"
                @click="emit('student-selected', student.id)"
              >
                <span class="rules-unplaced-student-name">
                  {{ student.display_name }}
                </span>
                <span
                  v-if="selectionOrder(student.id)"
                  class="rules-unplaced-student-order"
                  :data-test="`rules-unplaced-student-order-${student.id}`"
                >
                  {{ selectionOrder(student.id) }}
                </span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </section>
</template>

<style scoped>
.rules-map-view-stage {
  position: relative;
}

.rules-map-view-swap-enter-active,
.rules-map-view-swap-leave-active {
  transition: opacity var(--huleedu-duration-fast, 150ms) var(--huleedu-ease-default, ease);
}

.rules-map-view-swap-enter-from,
.rules-map-view-swap-leave-to {
  opacity: 0;
}

.rules-map-view-surface.rules-map-view-swap-leave-active {
  position: absolute;
  inset: 0;
  width: 100%;
  pointer-events: none;
}

.rules-unplaced-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.65rem;
}

.rules-unplaced-student {
  display: flex;
  min-height: 3.25rem;
  width: 100%;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 0.875rem;
}

.rules-unplaced-student-name {
  min-width: 0;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.35;
  text-wrap: balance;
}

.rules-unplaced-student-order {
  display: inline-flex;
  min-height: 1.5rem;
  min-width: 1.5rem;
  align-items: center;
  justify-content: center;
  border: 1px solid currentColor;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1;
  flex-shrink: 0;
}

@media (prefers-reduced-motion: reduce) {
  .rules-map-view-swap-enter-active,
  .rules-map-view-swap-leave-active {
    transition: none;
  }
}
</style>
