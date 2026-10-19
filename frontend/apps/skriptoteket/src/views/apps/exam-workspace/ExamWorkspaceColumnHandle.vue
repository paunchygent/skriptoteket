<script setup lang="ts">
/**
 * Exam workspace column resize handle.
 *
 * Domain purpose:
 *   The standard drag handle for one desktop panel border of the exam
 *   workspace. It works by pointer drag, keyboard and double-click, reports
 *   widths through events, and exposes window-splitter separator semantics
 *   (role=separator with aria-valuenow/min/max in px and a Swedish label).
 *   The parent panel positions the handle on its border; a later unit wires
 *   the emitted widths into the column sizes.
 *
 *   The drag is the documented layout-geometry exception: JS handles the
 *   drag and reports the requested width, while CSS owns the clamping of
 *   the tracks. The only measurement is transient: bounds are read from
 *   the closest .ws__body ancestor's computed gridTemplateColumns on focus
 *   and on pointerdown, with no ResizeObserver and no listeners at rest.
 *   The staging walk proves the rendered drag.
 *
 * Relationships:
 *   - Geometry comes from `examWorkspaceHandleBounds`; the per-column
 *     minimum from `EXAM_WORKSPACE_COLUMN_MIN`; keyboard mapping from
 *     `examWorkspaceSeparatorKeyAction` (arrows mirrored for the side edge,
 *     so ArrowLeft widens a right-edge panel). Emits feed
 *     `useExamWorkspaceColumnSizes` in the later wiring unit.
 */

import { ref } from "vue";

import {
  EXAM_WORKSPACE_COLUMN_MIN,
  type ExamWorkspaceColumn,
} from "./useExamWorkspaceColumnSizes";
import {
  examWorkspaceHandleBounds,
  parseGridTracks,
  type ExamWorkspaceHandleBounds,
  type ExamWorkspaceHandleEdge,
} from "./examWorkspaceHandleBounds";
import { examWorkspaceSeparatorKeyAction } from "./examWorkspaceSeparatorKeys";

const props = withDefaults(
  defineProps<{
    edge: ExamWorkspaceHandleEdge;
    column: ExamWorkspaceColumn;
    controls: string;
    label: string;
    collapsible?: boolean;
  }>(),
  { collapsible: true },
);

const emit = defineEmits<{
  set: [px: number];
  reset: [];
  "toggle-collapse": [];
}>();

const handle = ref<HTMLElement | null>(null);
const current = ref<number | null>(null);
const lower = ref<number | null>(null);
const upper = ref<number | null>(null);

type DragState = {
  startX: number;
  value: number;
  min: number;
  max: number;
};

let drag: DragState | null = null;

function clampWidth(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function readBounds(): ExamWorkspaceHandleBounds | null {
  const body = handle.value?.closest(".ws__body");
  if (!(body instanceof HTMLElement)) {
    return null;
  }
  const tracks = parseGridTracks(window.getComputedStyle(body).gridTemplateColumns);
  if (tracks === null) {
    return null;
  }
  return examWorkspaceHandleBounds(tracks, props.edge, EXAM_WORKSPACE_COLUMN_MIN[props.column]);
}

function applyBounds(bounds: ExamWorkspaceHandleBounds): void {
  current.value = bounds.value;
  lower.value = bounds.min;
  upper.value = bounds.max;
}

function onFocus(): void {
  const bounds = readBounds();
  if (bounds !== null) {
    applyBounds(bounds);
  }
}

function onPointerDown(event: PointerEvent): void {
  if (event.button !== 0) {
    return;
  }
  const bounds = readBounds();
  if (bounds === null) {
    return;
  }
  applyBounds(bounds);
  drag = { startX: event.clientX, ...bounds };
  handle.value?.setPointerCapture(event.pointerId);
}

function onPointerMove(event: PointerEvent): void {
  if (drag === null) {
    return;
  }
  const dx = event.clientX - drag.startX;
  const raw = props.edge === "list" ? drag.value + dx : drag.value - dx;
  const px = Math.round(clampWidth(raw, drag.min, drag.max));
  current.value = px;
  emit("set", px);
}

function stopDrag(event: PointerEvent): void {
  if (drag === null) {
    return;
  }
  drag = null;
  handle.value?.releasePointerCapture(event.pointerId);
}

function onKeydown(event: KeyboardEvent): void {
  const bounds = readBounds();
  if (bounds === null) {
    return;
  }
  let key = event.key;
  if (props.edge === "side" && (key === "ArrowLeft" || key === "ArrowRight")) {
    key = key === "ArrowLeft" ? "ArrowRight" : "ArrowLeft";
  }
  const action = examWorkspaceSeparatorKeyAction({ key, shiftKey: event.shiftKey }, bounds);
  if (action === null) {
    return;
  }
  if (action.kind === "toggle-collapse" && !props.collapsible) {
    return;
  }
  event.preventDefault();
  applyBounds(bounds);
  if (action.kind === "set") {
    current.value = action.value;
    emit("set", action.value);
  } else if (action.kind === "reset") {
    emit("reset");
  } else {
    emit("toggle-collapse");
  }
}

function onDblclick(): void {
  if (readBounds() === null) {
    return;
  }
  emit("reset");
}
</script>

<template>
  <div
    ref="handle"
    role="separator"
    tabindex="0"
    aria-orientation="vertical"
    :aria-controls="controls"
    :aria-label="label"
    :aria-valuenow="current ?? undefined"
    :aria-valuemin="lower ?? undefined"
    :aria-valuemax="upper ?? undefined"
    :aria-valuetext="current === null ? undefined : `${current} px`"
    :data-test="`exam-workspace-column-handle-${edge}`"
    :class="[
      'xw-column-handle',
      edge === 'list' ? 'xw-column-handle--list' : 'xw-column-handle--side',
    ]"
    @focus="onFocus"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="stopDrag"
    @pointercancel="stopDrag"
    @keydown="onKeydown"
    @dblclick="onDblclick"
  />
</template>

<style scoped>
.xw-column-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 8px;
  z-index: 5;
  cursor: col-resize;
  touch-action: none;
}
.xw-column-handle--list {
  right: -4px;
}
.xw-column-handle--side {
  left: -4px;
}
.xw-column-handle::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: 3px;
  width: 2px;
  background: var(--huleedu-action);
  opacity: 0;
}
.xw-column-handle:hover::after,
.xw-column-handle:focus-visible::after {
  opacity: 1;
}
.xw-column-handle:focus-visible {
  outline: 2px solid var(--huleedu-action-40);
  outline-offset: -2px;
}
</style>
