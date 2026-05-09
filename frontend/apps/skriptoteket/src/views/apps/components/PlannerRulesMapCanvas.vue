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

import type {
  FixedSeatRule,
  RelationshipRule,
  RoomTemplate,
  SeatAssignment,
  SeatingSmartTool,
  Student,
  StudentSeatingPreference,
} from "../classroomPlannerTypes";
import UiSegmentedToggle, {
  type UiSegmentedToggleOption,
} from "../../../components/ui/UiSegmentedToggle.vue";
import {
  formatSeatDisplayLabel,
  sortStudentsAlphabetically,
} from "../classroomPlannerSmartRulePresentation";
import { buildSeatRuleMarkersBySeatId } from "../classroomPlannerSeatRuleMarkers";
import { getRoomSurfaceMetrics } from "../roomFixturePresentation";
import { normalizeRoomGrid } from "../roomFixtureLayout";
import { useRoomViewportZoom } from "../useRoomViewportZoom";
import { ROOM_VIEWPORT_FRAME_PADDING } from "../roomBuilderViewport";
import RoomSceneSurface from "./RoomSceneSurface.vue";
import PlannerRulesSeatNode from "./PlannerRulesSeatNode.vue";
import PlannerRulesUnplacedStudentGrid from "./PlannerRulesUnplacedStudentGrid.vue";

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
  activeTool?: SeatingSmartTool | null;
  pendingFixedSeatStudentId?: string | null;
  pendingFixedSeatSeatId?: string | null;
  fixedSeatRules?: FixedSeatRule[];
  relationshipRules?: RelationshipRule[];
  seatingPreferences?: StudentSeatingPreference[];
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
  activeTool: null,
  pendingFixedSeatStudentId: null,
  pendingFixedSeatSeatId: null,
  fixedSeatRules: () => [],
  relationshipRules: () => [],
  seatingPreferences: () => [],
  smartRuleMarkersByStudentId: () => ({}),
});

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "seat-selected", seatId: string): void;
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
const surfaceStudentCountLabel = computed(() => {
  const count = surfaceStudents.value.length;
  return count === 1 ? "1 elev" : `${count} elever`;
});
const surfaceHeadingLabel = computed(() => {
  if (isPlanningMap.value) {
    return props.rosterName ?? "Klass";
  }
  return "Ej på karta";
});
const fixedSeatRuleBySeatId = computed<Record<string, FixedSeatRule | undefined>>(() => {
  return Object.fromEntries(props.fixedSeatRules.map((rule) => [rule.seat_id, rule]));
});
const seatRuleMarkersBySeatId = computed(() => buildSeatRuleMarkersBySeatId({
  template: props.template,
  studentsById: props.studentsById,
  seatAssignments: props.seatAssignments,
  fixedSeatRules: props.fixedSeatRules,
  relationshipRules: props.relationshipRules,
  seatingPreferences: props.seatingPreferences,
  pendingFixedSeatStudentId: props.pendingFixedSeatStudentId,
  pendingFixedSeatSeatId: props.pendingFixedSeatSeatId,
}));
const fixedSeatActive = computed(() => props.activeTool === "fixed_seat");
const shouldCenterSurface = computed(() => {
  const paddedWidth = Number.parseFloat(scaledSurfaceStyle.value.width ?? "0")
    + (ROOM_VIEWPORT_FRAME_PADDING * 2);
  return viewportWidth.value <= 0 || paddedWidth <= viewportWidth.value;
});
const mapViewOptions = computed<UiSegmentedToggleOption[]>(() => {
  return [
    {
      value: "seating_arrangement",
      label: "Klassrumsvy",
      dataTest: "rules-map-view-seating",
      disabled: !props.canShowSeatingArrangement,
      title: !props.canShowSeatingArrangement
        ? props.seatingArrangementUnavailableMessage ?? undefined
        : undefined,
    },
    {
      value: "planning_map",
      label: "Planeringskarta",
      dataTest: "rules-map-view-planning",
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
  return (
    props.selectedStudentId === studentId
    || props.pendingSelectedStudentIds.includes(studentId)
    || props.pendingFixedSeatStudentId === studentId
  );
}

function isSeatSelectedForFixedSeat(seatId: string): boolean {
  return props.activeTool === "fixed_seat" && props.pendingFixedSeatSeatId === seatId;
}

function fixedSeatTitle(rule: FixedSeatRule | undefined): string | null {
  if (!rule) {
    return null;
  }
  const studentName = props.studentsById[rule.student_id]?.display_name ?? "Elev";
  return `Fast plats: ${studentName} -> ${formatSeatDisplayLabel(rule.seat_id)}`;
}

function pendingFixedSeatPreviewTitle(seatId: string): string | null {
  if (props.activeTool !== "fixed_seat" || props.pendingFixedSeatSeatId !== seatId) {
    return null;
  }
  const studentId = props.pendingFixedSeatStudentId;
  if (!studentId) {
    return null;
  }
  const studentName = props.studentsById[studentId]?.display_name ?? "Elev";
  return `Fast plats: ${studentName} -> ${formatSeatDisplayLabel(seatId)}`;
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
                          :fixed="fixedSeatRuleBySeatId[seat.id] !== undefined"
                          :fixed-seat-title="fixedSeatTitle(fixedSeatRuleBySeatId[seat.id])"
                          :pending-fixed-seat-preview-title="pendingFixedSeatPreviewTitle(seat.id)"
                          :selected="
                            (
                              seatingStudentsBySeatId[seat.id] !== null
                              && isStudentSelected(seatingStudentsBySeatId[seat.id]?.id ?? '')
                            )
                              || fixedSeatRuleBySeatId[seat.id]?.student_id === pendingFixedSeatStudentId
                              || isSeatSelectedForFixedSeat(seat.id)
                          "
                          :selection-order="
                            seatingStudentsBySeatId[seat.id] !== null
                              ? selectionOrder(seatingStudentsBySeatId[seat.id]?.id ?? '')
                              : null
                          "
                          :markers="seatRuleMarkersBySeatId[seat.id] ?? []"
                          :fixed-seat-active="fixedSeatActive"
                          :pending-fixed-seat-student-id="pendingFixedSeatStudentId"
                          :pending-fixed-seat-seat-id="pendingFixedSeatSeatId"
                          :interactive="fixedSeatActive || seatingStudentsBySeatId[seat.id] !== null"
                          @student-selected="emit('student-selected', $event)"
                          @seat-selected="emit('seat-selected', $event)"
                        />
                      </template>
                    </RoomSceneSurface>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <PlannerRulesUnplacedStudentGrid
            :students="surfaceStudents"
            :heading-label="surfaceHeadingLabel"
            :student-count-label="surfaceStudentCountLabel"
            :selected-count="selectedUnplacedStudentsCount"
            :is-student-selected="isStudentSelected"
            :selection-order="selectionOrder"
            :pending-fixed-seat-student-id="pendingFixedSeatStudentId"
            @student-selected="emit('student-selected', $event)"
          />
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

@media (prefers-reduced-motion: reduce) {
  .rules-map-view-swap-enter-active,
  .rules-map-view-swap-leave-active {
    transition: none;
  }
}
</style>
