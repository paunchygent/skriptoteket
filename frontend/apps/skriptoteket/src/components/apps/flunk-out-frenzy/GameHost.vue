<script setup lang="ts">
/**
 * Flunk-Out Frenzy game host.
 *
 * This component owns the dedicated runtime mounting surface and the
 * shell-to-runtime seam. Vue mirrors read-only HUD and view snapshots while
 * the browser-owned runtime advances the prototype-alpha table behind this
 * host surface.
 */

import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { GameRuntime } from "./game/core/GameRuntime";
import { createInitialHudSnapshot, type GameViewSnapshot } from "./game/core/runtimeTypes";
import { KeyboardInputController } from "./game/input/KeyboardInputController";
import type { MachineEvent } from "./game/physics/physicsTypes";
import { PROTOTYPE_ALPHA_TABLE } from "./game/table/prototypeAlphaTable";
import type { GameHostApi, GameHudSnapshot } from "./gameHostTypes";

const props = defineProps<{
  title: string;
}>();

const referencePlayfieldUrl = new URL(
  "../../../assets/flunk-out-frenzy/reference-playfield-crop.jpg",
  import.meta.url,
).href;

const emit = defineEmits<{
  hudChange: [hud: GameHudSnapshot];
}>();

const hostElement = ref<HTMLDivElement | null>(null);
const hudSnapshot = ref<GameHudSnapshot>(createInitialHudSnapshot());
const viewSnapshot = ref<GameViewSnapshot>(createInitialViewSnapshot());
const runtimeBooting = ref(true);
let runtime: GameRuntime | null = null;
let keyboardController: KeyboardInputController | null = null;
let unsubscribeHud: (() => void) | null = null;
let unsubscribeView: (() => void) | null = null;
let disposed = false;

interface FlunkOutFrenzyDebugHandle {
  injectMachineEvents(events: MachineEvent[]): void;
  hud(): GameHudSnapshot;
}

declare global {
  interface Window {
    __FOF_DEBUG__?: FlunkOutFrenzyDebugHandle;
  }
}

const statusLabel = computed(() => {
  if (hudSnapshot.value.status === "running") {
    return "Pågående runda";
  }
  if (hudSnapshot.value.status === "paused") {
    return "Pausad";
  }
  if (hudSnapshot.value.status === "game-over") {
    return "Game over";
  }
  return "Väntar på start";
});

const hasBall = computed(() => viewSnapshot.value.ball !== null);

const ballStyle = computed(() => {
  const ball = viewSnapshot.value.ball;
  if (!ball) {
    return {};
  }

  return {
    left: toPercent(ball.x, viewSnapshot.value.board.width),
    top: toPercent(ball.y, viewSnapshot.value.board.height),
    width: toPercent(ball.radius * 2, viewSnapshot.value.board.width),
    height: toPercent(ball.radius * 2, viewSnapshot.value.board.height),
  };
});

const bumperMarkers = PROTOTYPE_ALPHA_TABLE.bumpers;

function startGame(): void {
  runtime?.start();
}

function pauseGame(): void {
  runtime?.pause();
}

function resumeGame(): void {
  runtime?.resume();
}

function restartGame(): void {
  runtime?.restart();
}

function setMuted(nextMuted: boolean): void {
  runtime?.setMuted(nextMuted);
}

function flipperStyle(side: "left" | "right"): Record<string, string> {
  const flipper = viewSnapshot.value.flippers[side];
  const anchorShift = side === "left" ? "0%" : "-100%";
  const displayAngleDeg = toDisplayFlipperAngle(side, flipper.angleDeg);

  return {
    left: toPercent(flipper.pivotX, viewSnapshot.value.board.width),
    top: toPercent(flipper.pivotY, viewSnapshot.value.board.height),
    width: toPercent(flipper.length, viewSnapshot.value.board.width),
    height: toPercent(flipper.thickness, viewSnapshot.value.board.height),
    transform: `translate(${anchorShift}, -50%) rotate(${displayAngleDeg}deg)`,
    transformOrigin: side === "left" ? "0% 50%" : "100% 50%",
  };
}

function rolloverStyle(rollover: GameViewSnapshot["rollovers"][number]): Record<string, string> {
  return {
    left: toPercent(rollover.x, viewSnapshot.value.board.width),
    top: toPercent(rollover.y, viewSnapshot.value.board.height),
  };
}

function bumperStyle(x: number, y: number, radius: number): Record<string, string> {
  return {
    left: toPercent(x, viewSnapshot.value.board.width),
    top: toPercent(y, viewSnapshot.value.board.height),
    width: toPercent(radius * 2.25, viewSnapshot.value.board.width),
    height: toPercent(radius * 2.25, viewSnapshot.value.board.height),
  };
}

onMounted(() => {
  if (!hostElement.value) {
    return;
  }

  const mountedHost = hostElement.value;
  disposed = false;

  void GameRuntime.create()
    .then((createdRuntime) => {
      if (disposed || hostElement.value !== mountedHost) {
        createdRuntime.dispose();
        return;
      }

      runtime = createdRuntime;
      runtime.mount(mountedHost);
      unsubscribeHud = runtime.subscribeHud((nextHud) => {
        hudSnapshot.value = nextHud;
        emit("hudChange", nextHud);
      });
      unsubscribeView = runtime.subscribeView((nextView) => {
        viewSnapshot.value = nextView;
      });

      keyboardController = new KeyboardInputController(runtime);
      keyboardController.attach();

      if (import.meta.env.DEV) {
        window.__FOF_DEBUG__ = {
          injectMachineEvents(events: MachineEvent[]) {
            createdRuntime.injectMachineEventsForDebug(events);
          },
          hud() {
            return hudSnapshot.value;
          },
        };
      }

      runtimeBooting.value = false;
    })
    .catch((error: unknown) => {
      runtimeBooting.value = false;
      console.error("Failed to initialize Flunk-Out Frenzy runtime.", error);
    });
});

onBeforeUnmount(() => {
  disposed = true;
  keyboardController?.detach();
  keyboardController = null;
  unsubscribeHud?.();
  unsubscribeHud = null;
  unsubscribeView?.();
  unsubscribeView = null;
  runtime?.dispose();
  runtime = null;
  runtimeBooting.value = true;

  if (import.meta.env.DEV) {
    delete window.__FOF_DEBUG__;
  }
});

defineExpose<GameHostApi>({
  startGame,
  pauseGame,
  resumeGame,
  restartGame,
  setMuted,
});

function createInitialViewSnapshot(): GameViewSnapshot {
  return {
    board: {
      width: PROTOTYPE_ALPHA_TABLE.board.width,
      height: PROTOTYPE_ALPHA_TABLE.board.height,
    },
    ball: null,
    flippers: {
      left: {
        side: "left",
        pivotX: PROTOTYPE_ALPHA_TABLE.flippers.left.pivot.x,
        pivotY: PROTOTYPE_ALPHA_TABLE.flippers.left.pivot.y,
        length: PROTOTYPE_ALPHA_TABLE.flippers.left.length,
        thickness: PROTOTYPE_ALPHA_TABLE.flippers.left.thickness,
        angleDeg: PROTOTYPE_ALPHA_TABLE.flippers.left.restAngleDeg,
      },
      right: {
        side: "right",
        pivotX: PROTOTYPE_ALPHA_TABLE.flippers.right.pivot.x,
        pivotY: PROTOTYPE_ALPHA_TABLE.flippers.right.pivot.y,
        length: PROTOTYPE_ALPHA_TABLE.flippers.right.length,
        thickness: PROTOTYPE_ALPHA_TABLE.flippers.right.thickness,
        angleDeg: PROTOTYPE_ALPHA_TABLE.flippers.right.restAngleDeg,
      },
    },
    rollovers: PROTOTYPE_ALPHA_TABLE.rollovers.map((rollover) => ({
      tag: rollover.tag,
      label: rollover.label,
      x: rollover.x,
      y: rollover.y,
      lit: false,
    })),
  };
}

function toPercent(value: number, total: number): string {
  return `${(value / total) * 100}%`;
}

function toDisplayFlipperAngle(side: "left" | "right", worldAngleDeg: number): number {
  if (side === "left") {
    return normalizeDisplayAngle(worldAngleDeg);
  }

  // The right flipper extends leftward from its pivot in DOM space, so the
  // mirrored display angle is the right-world angle relative to 180deg.
  return normalizeDisplayAngle(worldAngleDeg - 180);
}

function normalizeDisplayAngle(angleDeg: number): number {
  const wrapped = ((angleDeg + 180) % 360 + 360) % 360 - 180;
  return Math.abs(wrapped) < 0.0001 ? 0 : Number(wrapped.toFixed(3));
}
</script>

<template>
  <section class="fof-host">
    <div
      ref="hostElement"
      :aria-label="`${props.title} playfield`"
      data-test="runtime-host-placeholder"
      class="fof-host__playfield"
    >
      <img
        class="fof-host__image"
        :src="referencePlayfieldUrl"
        alt="Illustrerad referens för Flunk-Out Frenzys pinball-playfield"
      >
      <div class="fof-host__glass" />
      <div class="fof-host__scanline" />

      <div class="fof-host__edge fof-host__edge--top">
        <span>Prototype alpha</span>
        <span>{{ statusLabel }}</span>
      </div>

      <div class="fof-host__surface">
        <div
          v-for="bumper in bumperMarkers"
          :key="bumper.tag"
          class="fof-host__bumper"
          :style="bumperStyle(bumper.x, bumper.y, bumper.radius)"
        />

        <div
          v-for="rollover in viewSnapshot.rollovers"
          :key="rollover.tag"
          :class="['fof-host__rollover', { 'fof-host__rollover--lit': rollover.lit }]"
          :style="rolloverStyle(rollover)"
        >
          <span>{{ rollover.label }}</span>
        </div>

        <div
          data-test="runtime-flipper-left"
          class="fof-host__flipper fof-host__flipper--left"
          :style="flipperStyle('left')"
        />
        <div
          data-test="runtime-flipper-right"
          class="fof-host__flipper fof-host__flipper--right"
          :style="flipperStyle('right')"
        />

        <div
          v-if="hasBall"
          data-test="runtime-ball"
          class="fof-host__ball"
          :style="ballStyle"
        />

        <div
          v-if="hudSnapshot.status === 'game-over'"
          class="fof-host__message"
        >
          <p>Game over</p>
          <span>Starta om för nästa omgång.</span>
        </div>

        <div
          v-else-if="runtimeBooting"
          class="fof-host__message fof-host__message--subtle"
        >
          <p>Startar fysiken</p>
          <span>Laddar flippers, kula och spelregler.</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.fof-host {
  width: 100%;
}

.fof-host__playfield {
  position: relative;
  overflow: hidden;
  aspect-ratio: 0.76;
  border-radius: clamp(1.25rem, 2vw, 1.8rem);
  border: 1px solid rgba(255, 245, 225, 0.12);
  background: #100f0c;
  box-shadow:
    inset 0 1px 0 rgba(255, 243, 222, 0.12),
    0 18px 34px rgba(12, 8, 5, 0.3);
}

.fof-host__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  filter: saturate(0.98) contrast(1.05) brightness(0.78);
}

.fof-host__glass,
.fof-host__scanline,
.fof-host__surface {
  position: absolute;
  inset: 0;
}

.fof-host__surface {
  pointer-events: none;
}

.fof-host__glass {
  pointer-events: none;
  background:
    linear-gradient(130deg, rgba(255, 255, 255, 0.16), transparent 18%),
    linear-gradient(180deg, rgba(7, 9, 8, 0.05), rgba(7, 9, 8, 0.34));
}

.fof-host__scanline {
  pointer-events: none;
  background:
    repeating-linear-gradient(180deg, transparent, transparent 17px, rgba(255, 255, 255, 0.018) 18px);
  mix-blend-mode: screen;
  opacity: 0.46;
}

.fof-host__edge {
  position: absolute;
  left: clamp(0.9rem, 1.5vw, 1.2rem);
  right: clamp(0.9rem, 1.5vw, 1.2rem);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(246, 239, 225, 0.88);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.24);
}

.fof-host__edge--top {
  top: clamp(0.85rem, 1.4vw, 1rem);
}

.fof-host__bumper,
.fof-host__rollover,
.fof-host__ball,
.fof-host__flipper,
.fof-host__message {
  position: absolute;
}

.fof-host__message--subtle {
  background: rgba(20, 27, 22, 0.58);
}

.fof-host__bumper {
  transform: translate(-50%, -50%);
  border-radius: 999px;
  background:
    radial-gradient(circle, rgba(105, 255, 125, 0.42), transparent 52%);
  filter: blur(10px);
  opacity: 0.7;
}

.fof-host__rollover {
  display: grid;
  place-items: center;
  width: 7.4%;
  aspect-ratio: 1;
  transform: translate(-50%, -50%);
  border-radius: 999px;
  border: 1px solid rgba(255, 239, 141, 0.3);
  background: rgba(25, 26, 21, 0.54);
  color: rgba(255, 239, 141, 0.84);
  font-size: clamp(0.68rem, 1.2vw, 1.15rem);
  font-weight: 900;
  letter-spacing: 0.04em;
  box-shadow: 0 0 0 1px rgba(15, 18, 15, 0.22);
}

.fof-host__rollover--lit {
  background:
    radial-gradient(circle at 50% 50%, rgba(255, 239, 141, 0.82), rgba(255, 198, 62, 0.36));
  color: #261b0d;
  border-color: rgba(255, 239, 141, 0.86);
  box-shadow:
    0 0 18px rgba(255, 239, 141, 0.34),
    0 0 0 1px rgba(15, 18, 15, 0.22);
}

.fof-host__flipper {
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgba(255, 89, 147, 0.98), rgba(201, 31, 95, 0.98));
  border: 1px solid rgba(255, 232, 240, 0.26);
  box-shadow:
    0 10px 20px rgba(55, 8, 24, 0.26),
    inset 0 1px 0 rgba(255, 224, 236, 0.24);
}

.fof-host__ball {
  transform: translate(-50%, -50%);
  border-radius: 999px;
  background:
    radial-gradient(circle at 35% 32%, rgba(255, 255, 255, 0.95), rgba(226, 232, 240, 0.96) 38%, rgba(93, 103, 122, 0.96) 82%);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.26),
    0 6px 16px rgba(0, 0, 0, 0.24);
}

.fof-host__message {
  left: 50%;
  bottom: 11.5%;
  transform: translateX(-50%);
  display: grid;
  gap: 0.16rem;
  padding: 0.72rem 1rem 0.78rem;
  border-radius: 999px;
  background: rgba(20, 27, 22, 0.78);
  border: 1px solid rgba(255, 243, 221, 0.16);
  backdrop-filter: blur(8px);
  text-align: center;
}

.fof-host__message p,
.fof-host__message span {
  margin: 0;
}

.fof-host__message p {
  font-size: 0.76rem;
  font-weight: 900;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #f6efe1;
}

.fof-host__message span {
  font-size: 0.84rem;
  color: rgba(246, 239, 225, 0.8);
}
</style>
