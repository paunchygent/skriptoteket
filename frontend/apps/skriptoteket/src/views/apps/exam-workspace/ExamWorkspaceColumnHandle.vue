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
 *   the tracks and is the one minimum authority (`--xw-<column>-min` and
 *   `--xw-editor-min` on the closest `.xw-root` ancestor, parsed as px; any
 *   missing minimum gives null bounds). The only measurement is transient:
 *   bounds are read from the closest `.ws__body` ancestor's computed
 *   gridTemplateColumns on mount (after nextTick), on focus, after every
 *   emitted key/double-click set, reset and toggle-collapse (nextTick, then
 *   read again), when the `collapsed` prop changes, and on every track
 *   change: one ResizeObserver per handle observes the closest `.ws__body`
 *   and each of its element children (the list, editor and side panels),
 *   re-syncing the observed children on every callback because panels mount
 *   and unmount. The observer callback only updates the separator values;
 *   it never emits set/reset. A pointer drag holds
 *   its pointerdown bounds until pointerup, so the live drag value is never
 *   clobbered by a re-read. There are no window or
 *   document listeners. The staging walk proves the rendered drag.
 *
 *   With `collapsed` (the list rail) the separator announces the rail:
 *   aria-valuenow/min are the rail track width, aria-valuemax is the normal
 *   max, and aria-valuetext is "Dold". Drag and key behaviour stay as now:
 *   the first step clamps to the list minimum, which expands the list.
 *
 * Relationships:
 *   - Geometry comes from `examWorkspaceHandleBounds` (tracks plus
 *     `parsePx` for the CSS minimums); keyboard mapping from
 *     `examWorkspaceSeparatorKeyAction` (arrows mirrored for the side edge,
 *     so ArrowLeft widens a right-edge panel). Emits feed
 *     `useExamWorkspaceColumnSizes` in the later wiring unit.
 */

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import type { ExamWorkspaceColumn } from "./useExamWorkspaceColumnSizes";
import {
  examWorkspaceHandleBounds,
  parseGridTracks,
  parsePx,
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
    collapsed?: boolean;
  }>(),
  { collapsible: true, collapsed: false },
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

const valueText = computed<string | undefined>(() => {
  if (props.collapsed) {
    return "Dold";
  }
  if (current.value === null) {
    return undefined;
  }
  return `${current.value} px`;
});

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
  const root = handle.value?.closest(".xw-root");
  if (!(body instanceof HTMLElement) || !(root instanceof HTMLElement)) {
    return null;
  }
  const tracks = parseGridTracks(window.getComputedStyle(body).gridTemplateColumns);
  if (tracks === null) {
    return null;
  }
  const rootStyle = window.getComputedStyle(root);
  const own = parsePx(rootStyle.getPropertyValue(`--xw-${props.column}-min`));
  const editor = parsePx(rootStyle.getPropertyValue("--xw-editor-min"));
  if (own === null || editor === null) {
    return null;
  }
  return examWorkspaceHandleBounds(tracks, props.edge, { own, editor });
}

function applyBounds(bounds: ExamWorkspaceHandleBounds): void {
  current.value = bounds.value;
  lower.value = props.collapsed ? bounds.value : bounds.min;
  upper.value = bounds.max;
}

async function refreshBounds(): Promise<void> {
  await nextTick();
  const bounds = readBounds();
  if (bounds !== null) {
    applyBounds(bounds);
  }
}

let trackObserver: ResizeObserver | null = null;
const observedTargets = new Set<Element>();

function trackTargets(): Element[] {
  const body = handle.value?.closest(".ws__body");
  if (!(body instanceof HTMLElement)) {
    return [];
  }
  return [body, ...Array.from(body.children)];
}

function syncObservedTargets(): void {
  if (trackObserver === null) {
    return;
  }
  const wanted = new Set(trackTargets());
  for (const target of wanted) {
    if (!observedTargets.has(target)) {
      observedTargets.add(target);
      trackObserver.observe(target);
    }
  }
  for (const target of Array.from(observedTargets)) {
    if (!wanted.has(target)) {
      observedTargets.delete(target);
      trackObserver.unobserve(target);
    }
  }
}

function onTrackChange(): void {
  const bounds = readBounds();
  if (bounds !== null) {
    applyBounds(bounds);
  }
  syncObservedTargets();
}

onMounted(() => {
  if (typeof ResizeObserver !== "undefined") {
    trackObserver = new ResizeObserver(onTrackChange);
    syncObservedTargets();
  }
  void refreshBounds();
});

onUnmounted(() => {
  trackObserver?.disconnect();
  trackObserver = null;
  observedTargets.clear();
});

watch(
  () => props.collapsed,
  () => {
    void refreshBounds();
  },
);

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

async function onKeydown(event: KeyboardEvent): Promise<void> {
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
  await nextTick();
  const fresh = readBounds();
  if (fresh !== null) {
    applyBounds(fresh);
  }
}

async function onDblclick(): Promise<void> {
  if (readBounds() === null) {
    return;
  }
  emit("reset");
  await nextTick();
  const fresh = readBounds();
  if (fresh !== null) {
    applyBounds(fresh);
  }
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
    :aria-valuetext="valueText"
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
/* Inside the panel edge: the panel root scrolls horizontally, so a handle
   outside its box would be clipped and would add scrollable overflow. */
.xw-column-handle--list {
  right: 0;
}
.xw-column-handle--side {
  left: 0;
}
.xw-column-handle::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--huleedu-action);
  opacity: 0;
}
.xw-column-handle--list::after {
  right: 0;
}
.xw-column-handle--side::after {
  left: 0;
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
