<script setup lang="ts">
/**
 * Shared room-fixture artwork renderer.
 *
 * This component draws one classroom object consistently across the builder,
 * preview, and live seating canvas so recognizability, labels, and bench
 * coalescing stay aligned on every surface.
 */

import { computed, type CSSProperties } from "vue";

import {
  getBenchNeighbors,
  getCanonicalFixtureLabel,
  getFixtureWallSide,
  type FixtureRenderSurface,
  type PresentedRoomFixture,
} from "../roomFixturePresentation";
import type { RoomGridDimensions } from "../roomFixtureLayout";

const props = withDefaults(defineProps<{
  fixture: PresentedRoomFixture;
  fixtures?: readonly PresentedRoomFixture[];
  grid: RoomGridDimensions;
  surface?: FixtureRenderSurface;
}>(), {
  fixtures: () => [],
  surface: "absolute",
});

const wallSide = computed(() => getFixtureWallSide(props.fixture, props.grid));
const displayLabel = computed(() => {
  return props.fixture.displayLabel ?? props.fixture.label ?? getCanonicalFixtureLabel(props.fixture.type);
});
const showLabel = computed(() => {
  return props.fixture.labelVisible ?? Boolean(displayLabel.value);
});
const benchNeighbors = computed(() => getBenchNeighbors(props.fixture, props.fixtures));

const labelClass = computed(() => {
  return props.fixture.tone === "strong" || props.fixture.type === "teacher_desk"
    ? "text-white"
    : "text-navy";
});

const labelStyle = computed<CSSProperties>(() => {
  const verticalLabel = (
    props.fixture.labelOrientation === "vertical"
    || (
      props.fixture.labelOrientation === undefined
      && (wallSide.value === "left" || wallSide.value === "right")
    )
  );
  switch (wallSide.value) {
    case "top":
      return { left: "50%", top: "-20px", transform: "translateX(-50%)" };
    case "bottom":
      return { left: "50%", top: "calc(100% + 6px)", transform: "translateX(-50%)" };
    case "left":
      return {
        right: "calc(100% + 6px)",
        top: "50%",
        transform: "translateY(-50%)",
        writingMode: verticalLabel ? "vertical-lr" : undefined,
        textOrientation: verticalLabel ? "mixed" : undefined,
      };
    case "right":
      return {
        left: "calc(100% + 6px)",
        top: "50%",
        transform: "translateY(-50%)",
        writingMode: verticalLabel ? "vertical-rl" : undefined,
        textOrientation: verticalLabel ? "mixed" : undefined,
      };
    default:
      return { left: "50%", top: "50%", transform: "translate(-50%, -50%)" };
  }
});

const wallBodyClass = computed(() => {
  switch (props.fixture.type) {
    case "whiteboard":
      return "bg-white border border-navy shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8)]";
    case "window":
      return "bg-white border border-navy";
    case "door":
      return "bg-white border border-navy";
    default:
      return "bg-white border border-navy/40";
  }
});

const wallDividerClass = computed(() => {
  if (props.fixture.type !== "window") {
    return "";
  }
  if (wallSide.value === "left" || wallSide.value === "right") {
    return "absolute inset-x-[2px] top-1/2 h-px -translate-y-1/2 bg-navy/50";
  }
  return "absolute inset-y-[2px] left-1/2 w-px -translate-x-1/2 bg-navy/50";
});

const doorSwingClass = computed(() => {
  if (props.fixture.type !== "door") {
    return "";
  }
  switch (wallSide.value) {
    case "left":
      return "absolute inset-y-[2px] right-[2px] w-[8px] rounded-r-full border-r border-t border-b border-navy/60";
    case "right":
      return "absolute inset-y-[2px] left-[2px] w-[8px] rounded-l-full border-l border-t border-b border-navy/60";
    case "bottom":
      return "absolute inset-x-[2px] top-[2px] h-[8px] rounded-t-full border-l border-r border-t border-navy/60";
    case "top":
    default:
      return "absolute inset-x-[2px] bottom-[2px] h-[8px] rounded-b-full border-l border-r border-b border-navy/60";
  }
});

const benchStyle = computed<CSSProperties>(() => {
  if (props.fixture.type !== "bench") {
    return {};
  }

  const mergeOffset = props.surface === "builder-grid" ? "4px" : "0px";
  return {
    left: benchNeighbors.value.left ? `-${mergeOffset}` : "8px",
    right: benchNeighbors.value.right ? `-${mergeOffset}` : "8px",
  };
});

const benchClass = computed(() => {
  const roundedLeft = benchNeighbors.value.left ? "" : "rounded-l-md";
  const roundedRight = benchNeighbors.value.right ? "" : "rounded-r-md";
  return `absolute top-1/2 h-6 -translate-y-1/2 border border-navy/70 bg-navy/20 shadow-[inset_0_1px_0_rgba(255,255,255,0.35)] ${roundedLeft} ${roundedRight}`;
});
</script>

<template>
  <div class="relative h-full w-full overflow-visible">
    <template v-if="fixture.type === 'whiteboard' || fixture.type === 'window' || fixture.type === 'door'">
      <div
        class="absolute inset-0 rounded-sm"
        :class="wallBodyClass"
      />
      <div
        v-if="fixture.type === 'whiteboard'"
        class="absolute inset-x-1 bottom-[1px] h-[3px] rounded bg-navy/40"
      />
      <div
        v-if="fixture.type === 'window'"
        :class="wallDividerClass"
      />
      <div
        v-if="fixture.type === 'door'"
        :class="doorSwingClass"
      />
    </template>

    <template v-else-if="fixture.type === 'teacher_desk'">
      <div class="absolute inset-0 rounded-sm border-2 border-navy bg-navy/85 shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]" />
      <div class="absolute inset-x-2 top-2 h-2 rounded bg-white/25" />
    </template>

    <template v-else-if="fixture.type === 'round_table'">
      <div class="absolute inset-0 rounded-full border-2 border-navy bg-white shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]" />
      <div class="absolute inset-[10%] rounded-full border border-navy/30 bg-white" />
    </template>

    <template v-else-if="fixture.type === 'square_table'">
      <div class="absolute inset-0 border-2 border-navy bg-white shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]" />
      <div class="absolute inset-[10%] border border-navy/30 bg-white" />
    </template>

    <template v-else-if="fixture.type === 'bench'">
      <div
        :class="benchClass"
        :style="benchStyle"
      />
    </template>

    <div
      v-if="showLabel"
      class="pointer-events-none absolute text-center text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)]"
      :class="labelClass"
      :style="labelStyle"
    >
      {{ displayLabel }}
    </div>
  </div>
</template>
