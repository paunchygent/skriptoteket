<script setup lang="ts">
/**
 * Flunk-Out Frenzy game host.
 *
 * This component owns the dedicated runtime mounting surface and the shell-to-
 * runtime seam. Vue mirrors HUD state and overlay messaging only, while the
 * runtime mounts its renderer and audio adapters behind this host surface.
 */

import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { GameRuntime } from "./game/core/GameRuntime";
import { createInitialHudSnapshot } from "./game/core/runtimeTypes";
import { KeyboardInputController } from "./game/input/KeyboardInputController";
import type { MachineEvent } from "./game/physics/physicsTypes";
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
const runtimeBooting = ref(true);
let runtime: GameRuntime | null = null;
let keyboardController: KeyboardInputController | null = null;
let unsubscribeHud: (() => void) | null = null;
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
        <span>Laddar renderare, ljud och spelregler.</span>
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
.fof-host__scanline {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.fof-host__glass {
  background:
    linear-gradient(130deg, rgba(255, 255, 255, 0.16), transparent 18%),
    linear-gradient(180deg, rgba(7, 9, 8, 0.05), rgba(7, 9, 8, 0.34));
}

.fof-host__scanline {
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
  z-index: 2;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(246, 239, 225, 0.88);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.24);
  pointer-events: none;
}

.fof-host__edge--top {
  top: clamp(0.85rem, 1.4vw, 1rem);
}

.fof-host__message {
  position: absolute;
  left: 50%;
  bottom: 11.5%;
  z-index: 2;
  transform: translateX(-50%);
  display: grid;
  gap: 0.16rem;
  padding: 0.72rem 1rem 0.78rem;
  border-radius: 999px;
  background: rgba(20, 27, 22, 0.78);
  border: 1px solid rgba(255, 243, 221, 0.16);
  backdrop-filter: blur(8px);
  text-align: center;
  pointer-events: none;
}

.fof-host__message--subtle {
  background: rgba(20, 27, 22, 0.58);
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
