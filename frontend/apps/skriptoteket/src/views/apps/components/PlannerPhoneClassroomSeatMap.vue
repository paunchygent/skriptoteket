<script setup lang="ts">
/**
 * Phone classroom seat map.
 *
 * Purpose:
 *   Renders the shared simplified classroom map used by phone rules and
 *   seating workspaces while preserving canonical template seat identities.
 *
 * Relationships:
 *   - consumed by `PlannerPhoneFixedSeatRulePanel.vue`
 *   - consumed by the phone branch of `PlannerSeatingWorkspacePane.vue`
 */

import { computed, onBeforeUnmount, ref, type Component } from "vue";

import { IconKeepApart, IconKeepNear, IconLock, IconTeacherAnchor } from "../../../components/icons";
import type {
  FixedSeatRule,
  RelationshipRule,
  RoomFixture,
  RoomTemplate,
  SeatAssignment,
  Student,
  StudentSeatingPreference,
} from "../classroomPlannerTypes";
import { formatSeatDisplayLabel } from "../classroomPlannerSmartRulePresentation";
import {
  buildSeatRuleMarkersBySeatId,
  type SmartRuleMarkerKind,
} from "../classroomPlannerSeatRuleMarkers";
import {
  isWallFixtureType,
  normalizeRoomGrid,
  resolveWallSideFromFixture,
  ROOM_GRID_UNIT,
} from "../roomFixtureLayout";

const props = withDefaults(defineProps<{
  template?: RoomTemplate | null;
  studentsById?: Record<string, Student | undefined>;
  seatAssignments?: SeatAssignment[];
  selectedSeatId?: string | null;
  fixedSeatRules?: FixedSeatRule[];
  relationshipRules?: RelationshipRule[];
  seatingPreferences?: StudentSeatingPreference[];
  pendingFixedSeatStudentId?: string | null;
  pendingFixedSeatSeatId?: string | null;
  editableAssignments?: boolean;
}>(), {
  template: null,
  studentsById: () => ({}),
  seatAssignments: () => [],
  selectedSeatId: null,
  fixedSeatRules: () => [],
  relationshipRules: () => [],
  seatingPreferences: () => [],
  pendingFixedSeatStudentId: null,
  pendingFixedSeatSeatId: null,
  editableAssignments: false,
});

const emit = defineEmits<{
  (e: "seat-selected", seatId: string): void;
  (e: "student-dragstart", event: DragEvent, studentId: string): void;
  (e: "student-dropped", studentId: string, seatId: string): void;
  (e: "student-removed", studentId: string): void;
  (e: "swap-requested", studentIdA: string, studentIdB: string): void;
}>();

const markerIconByKind: Record<SmartRuleMarkerKind, Component> = {
  "fixed-seat": IconLock,
  "keep-apart": IconKeepApart,
  "keep-near": IconKeepNear,
  "near-teacher": IconTeacherAnchor,
};
const PHONE_LONG_PRESS_MS = 450;
type PhoneSeatStudentName = {
  firstName: string;
  lastInitials: string | null;
};
const longPressTimer = ref<ReturnType<typeof window.setTimeout> | null>(null);
const touchDragStudentId = ref<string | null>(null);
const touchDragSourceSeatId = ref<string | null>(null);
const suppressClickSeatId = ref<string | null>(null);
const roomGrid = computed(() => normalizeRoomGrid(props.template));
const mapGridStyle = computed(() => ({
  "--phone-map-cols": String(roomGrid.value.cols),
  "--phone-map-rows": String(roomGrid.value.rows),
  gridTemplateColumns: `repeat(${roomGrid.value.cols}, var(--planner-phone-seat-cell-size))`,
  gridTemplateRows: `repeat(${roomGrid.value.rows}, var(--planner-phone-seat-cell-size))`,
}));
const seatCountLabel = computed(() => {
  const count = props.template?.seats.length ?? 0;
  return count === 1 ? "1" : String(count);
});
const studentBySeatId = computed<Record<string, Student | null>>(() => {
  const bySeatId: Record<string, Student | null> = {};
  for (const seat of props.template?.seats ?? []) {
    bySeatId[seat.id] = null;
  }
  for (const assignment of props.seatAssignments) {
    if (bySeatId[assignment.seat_id] !== undefined) {
      bySeatId[assignment.seat_id] = props.studentsById[assignment.student_id] ?? null;
    }
  }
  return bySeatId;
});
const studentNameBySeatId = computed<Record<string, PhoneSeatStudentName | null>>(() => {
  const bySeatId: Record<string, PhoneSeatStudentName | null> = {};
  for (const [seatId, student] of Object.entries(studentBySeatId.value)) {
    bySeatId[seatId] = student ? formatPhoneSeatStudentName(student.display_name) : null;
  }
  return bySeatId;
});
const fixedRuleBySeatId = computed<Record<string, FixedSeatRule | undefined>>(() => {
  return Object.fromEntries(props.fixedSeatRules.map((rule) => [rule.seat_id, rule]));
});
const mapFixtures = computed(() => {
  return props.template?.fixtures.filter((fixture) => {
    return (
      fixture.type === "whiteboard"
      || fixture.type === "window"
      || fixture.type === "door"
      || fixture.type === "teacher_desk"
    );
  }) ?? [];
});
const ruleMarkersBySeatId = computed(() => buildSeatRuleMarkersBySeatId({
  template: props.template,
  studentsById: props.studentsById,
  seatAssignments: props.seatAssignments,
  fixedSeatRules: props.fixedSeatRules,
  relationshipRules: props.relationshipRules,
  seatingPreferences: props.seatingPreferences,
  pendingFixedSeatStudentId: props.pendingFixedSeatStudentId,
  pendingFixedSeatSeatId: props.pendingFixedSeatSeatId,
}));

function gridStartFromCoordinate(value: number): number {
  return Math.max(1, Math.round(value / ROOM_GRID_UNIT) + 1);
}

function gridSpanFromSize(value: number): number {
  return Math.max(1, Math.round(value / ROOM_GRID_UNIT));
}

function seatGridStyle(seat: { x: number; y: number }): Record<string, string> {
  return {
    gridColumn: `${gridStartFromCoordinate(seat.x)} / span 1`,
    gridRow: `${gridStartFromCoordinate(seat.y)} / span 1`,
  };
}

function fixtureGridStyle(fixture: RoomFixture): Record<string, string> {
  const wallSide = props.template && isWallFixtureType(fixture.type)
    ? resolveWallSideFromFixture(fixture, roomGrid.value)
    : null;
  if (wallSide === "top" || wallSide === "bottom") {
    return {
      gridColumn: `${gridStartFromCoordinate(fixture.x)} / span ${gridSpanFromSize(fixture.width)}`,
      gridRow: `${wallSide === "top" ? 1 : roomGrid.value.rows} / span 1`,
    };
  }
  if (wallSide === "left" || wallSide === "right") {
    return {
      gridColumn: `${wallSide === "left" ? 1 : roomGrid.value.cols} / span 1`,
      gridRow: `${gridStartFromCoordinate(fixture.y)} / span ${gridSpanFromSize(fixture.height)}`,
    };
  }
  return {
    gridColumn: `${gridStartFromCoordinate(fixture.x)} / span ${gridSpanFromSize(fixture.width)}`,
    gridRow: `${gridStartFromCoordinate(fixture.y)} / span ${gridSpanFromSize(fixture.height)}`,
  };
}

function fixtureLabel(fixture: RoomFixture): string {
  if (fixture.type === "teacher_desk") {
    return "Kateder";
  }
  if (fixture.type === "door") {
    return "Dörr";
  }
  if (fixture.type === "window") {
    return "Fönster";
  }
  return "Tavla";
}

function fixtureVisibleLabel(fixture: RoomFixture): string {
  return isWallFixtureType(fixture.type) ? "" : fixtureLabel(fixture);
}

function fixtureClass(fixture: RoomFixture): string[] {
  const wallSide = props.template && isWallFixtureType(fixture.type)
    ? resolveWallSideFromFixture(fixture, roomGrid.value)
    : null;
  return [
    `planner-phone-fixed-seat-map-fixture-${fixture.type}`,
    wallSide ? `planner-phone-fixed-seat-map-fixture-wall-${wallSide}` : "",
  ].filter(Boolean);
}

function formatPhoneSeatStudentName(displayName: string): PhoneSeatStudentName | null {
  const parts = displayName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return null;
  }
  const lastInitials = parts
    .slice(1)
    .map((part) => part[0]?.toLocaleUpperCase("sv-SE") ?? "")
    .filter(Boolean)
    .join("");
  return {
    firstName: parts[0] ?? displayName.trim(),
    lastInitials: lastInitials.length > 0 ? lastInitials : null,
  };
}

function seatTitle(seatId: string): string {
  const studentName = studentBySeatId.value[seatId]?.display_name;
  const baseLabel = formatSeatDisplayLabel(seatId);
  const markerLabels = ruleMarkersBySeatId.value[seatId]?.map((marker) => marker.label) ?? [];
  const title = studentName && props.editableAssignments
    ? `${baseLabel}: ${studentName}. Tryck för att ta bort eleven från platsen.`
    : studentName ? `${baseLabel}: ${studentName}` : baseLabel;
  return markerLabels.length > 0 ? `${title}. ${markerLabels.join(" ")}` : title;
}

function markerPreview(seatId: string) {
  return (ruleMarkersBySeatId.value[seatId] ?? []).slice(0, 3);
}

function markerOverflowCount(seatId: string): number {
  return Math.max(0, (ruleMarkersBySeatId.value[seatId]?.length ?? 0) - 3);
}

function clearLongPressTimer(): void {
  if (longPressTimer.value === null) {
    return;
  }
  window.clearTimeout(longPressTimer.value);
  longPressTimer.value = null;
}

function resetTouchDrag(): void {
  clearLongPressTimer();
  touchDragStudentId.value = null;
  touchDragSourceSeatId.value = null;
}

function releasePointerCapture(event: PointerEvent): void {
  const target = event.currentTarget;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  try {
    target.releasePointerCapture(event.pointerId);
  } catch {
    // The pointer may already be released by the browser after a cancellation.
  }
}

function seatIdFromPointer(event: PointerEvent): string | null {
  const target = document.elementFromPoint(event.clientX, event.clientY);
  if (!(target instanceof Element)) {
    return null;
  }
  return target.closest<HTMLElement>("[data-phone-seat-id]")?.dataset.phoneSeatId ?? null;
}

function handlePointerDown(event: PointerEvent, seatId: string): void {
  if (!props.editableAssignments || (event.pointerType !== "touch" && event.pointerType !== "pen")) {
    return;
  }
  const student = studentBySeatId.value[seatId];
  if (!student) {
    return;
  }
  clearLongPressTimer();
  (event.currentTarget as HTMLElement | null)?.setPointerCapture?.(event.pointerId);
  longPressTimer.value = window.setTimeout(() => {
    touchDragStudentId.value = student.id;
    touchDragSourceSeatId.value = seatId;
    suppressClickSeatId.value = seatId;
  }, PHONE_LONG_PRESS_MS);
}

function handlePointerUp(event: PointerEvent): void {
  clearLongPressTimer();
  const sourceStudentId = touchDragStudentId.value;
  const sourceSeatId = touchDragSourceSeatId.value;
  resetTouchDrag();
  releasePointerCapture(event);
  if (!sourceStudentId || !sourceSeatId || !props.editableAssignments) {
    return;
  }
  event.preventDefault();
  const targetSeatId = seatIdFromPointer(event);
  if (!targetSeatId || targetSeatId === sourceSeatId) {
    return;
  }
  const targetStudent = studentBySeatId.value[targetSeatId];
  if (targetStudent && targetStudent.id !== sourceStudentId) {
    emit("swap-requested", sourceStudentId, targetStudent.id);
    return;
  }
  emit("student-dropped", sourceStudentId, targetSeatId);
}

function handlePointerCancel(event: PointerEvent): void {
  resetTouchDrag();
  releasePointerCapture(event);
}

function handleDragStart(event: DragEvent, seatId: string): void {
  const student = studentBySeatId.value[seatId];
  if (!student || !props.editableAssignments) {
    return;
  }
  emit("student-dragstart", event, student.id);
}

function handleDrop(event: DragEvent, seatId: string): void {
  if (!props.editableAssignments) {
    return;
  }
  event.preventDefault();
  const sourceStudentId = event.dataTransfer?.getData("studentId");
  if (!sourceStudentId) {
    return;
  }
  const targetStudent = studentBySeatId.value[seatId];
  if (targetStudent && targetStudent.id !== sourceStudentId) {
    emit("swap-requested", sourceStudentId, targetStudent.id);
    return;
  }
  emit("student-dropped", sourceStudentId, seatId);
}

function handleDragOver(event: DragEvent): void {
  if (!props.editableAssignments) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
}

function handleSeatClick(seatId: string): void {
  if (suppressClickSeatId.value === seatId) {
    suppressClickSeatId.value = null;
    return;
  }
  const student = studentBySeatId.value[seatId];
  if (props.editableAssignments && student) {
    emit("student-removed", student.id);
    return;
  }
  emit("seat-selected", seatId);
}

onBeforeUnmount(() => {
  clearLongPressTimer();
});
</script>

<template>
  <div
    v-if="template"
    class="planner-phone-fixed-seat-map"
    data-test="phone-classroom-seat-map"
  >
    <div class="planner-phone-fixed-seat-map-header">
      <span>Klassrum</span>
      <span data-test="phone-fixed-seat-map-count">{{ seatCountLabel }}</span>
    </div>
    <div
      class="planner-phone-fixed-seat-map-grid"
      :style="mapGridStyle"
    >
      <div
        v-for="fixture in mapFixtures"
        :key="fixture.id"
        class="planner-phone-fixed-seat-map-fixture"
        :class="fixtureClass(fixture)"
        :style="fixtureGridStyle(fixture)"
        :aria-label="fixtureLabel(fixture)"
      >
        {{ fixtureVisibleLabel(fixture) }}
      </div>
      <div
        v-for="seat in template.seats"
        :key="seat.id"
        class="planner-phone-fixed-seat-map-seat-wrapper"
        :class="{ 'planner-phone-fixed-seat-map-seat-wrapper-with-markers': ruleMarkersBySeatId[seat.id]?.length }"
        :style="seatGridStyle(seat)"
        :data-test="`phone-fixed-seat-map-seat-wrapper-${seat.id}`"
        @dragover="handleDragOver"
        @drop="handleDrop($event, seat.id)"
      >
        <button
          type="button"
          class="planner-phone-fixed-seat-map-seat"
          :class="{
            'planner-phone-fixed-seat-map-seat-selected': selectedSeatId === seat.id,
            'planner-phone-fixed-seat-map-seat-fixed': fixedRuleBySeatId[seat.id] !== undefined,
            'planner-phone-fixed-seat-map-seat-with-markers': ruleMarkersBySeatId[seat.id]?.length,
            'planner-phone-fixed-seat-map-seat-touch-dragging': touchDragSourceSeatId === seat.id,
          }"
          :title="seatTitle(seat.id)"
          :aria-label="seatTitle(seat.id)"
          :aria-pressed="selectedSeatId === seat.id"
          :draggable="editableAssignments && studentBySeatId[seat.id] !== null"
          :data-phone-seat-id="seat.id"
          :data-test="`phone-fixed-seat-map-seat-${seat.id}`"
          @click="handleSeatClick(seat.id)"
          @pointerdown="handlePointerDown($event, seat.id)"
          @pointerup="handlePointerUp"
          @pointercancel="handlePointerCancel"
          @dragstart="handleDragStart($event, seat.id)"
        >
          <span class="planner-phone-fixed-seat-map-seat-label">
            {{ formatSeatDisplayLabel(seat.id).replace("plats-", "") }}
          </span>
          <span
            v-if="studentNameBySeatId[seat.id]?.firstName"
            class="planner-phone-fixed-seat-map-seat-student-first"
            :data-test="`phone-fixed-seat-map-seat-first-name-${seat.id}`"
          >
            {{ studentNameBySeatId[seat.id]?.firstName }}
          </span>
          <span
            v-if="studentNameBySeatId[seat.id]?.lastInitials"
            class="planner-phone-fixed-seat-map-seat-student-initials"
            :data-test="`phone-fixed-seat-map-seat-last-initials-${seat.id}`"
          >
            {{ studentNameBySeatId[seat.id]?.lastInitials }}
          </span>
          <span
            v-if="ruleMarkersBySeatId[seat.id]?.length"
            class="planner-phone-fixed-seat-rule-markers"
            aria-hidden="true"
          >
            <span
              v-for="marker in markerPreview(seat.id)"
              :key="marker.id"
              class="planner-phone-fixed-seat-rule-marker"
              :class="`planner-phone-fixed-seat-rule-marker-${marker.tone}`"
              :title="marker.label"
              :data-test="`phone-seat-rule-marker-${seat.id}-${marker.kind}-${marker.tone}`"
            >
              <component
                :is="markerIconByKind[marker.kind]"
                :size="9"
              />
            </span>
            <span
              v-if="markerOverflowCount(seat.id) > 0"
              class="planner-phone-fixed-seat-rule-marker planner-phone-fixed-seat-rule-marker-overflow"
              :data-test="`phone-seat-rule-marker-overflow-${seat.id}`"
            >
              +{{ markerOverflowCount(seat.id) }}
            </span>
          </span>
        </button>
      </div>
    </div>
  </div>
</template>
