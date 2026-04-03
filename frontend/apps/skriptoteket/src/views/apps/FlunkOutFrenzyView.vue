<script setup lang="ts">
/**
 * Flunk-Out Frenzy shell view.
 *
 * This bespoke route owns the app bootstrap and presents the first viewport as
 * a single game composition. The shell keeps bootstrap/loading/settings logic
 * at the route layer while delegating the future playfield runtime to
 * `GameHost.vue`.
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import GameHost from "../../components/apps/flunk-out-frenzy/GameHost.vue";
import {
  labelGameSessionStatus,
  type GameHostApi,
  type GameHudSnapshot,
  type GameRuntimeLoadState,
  type GameRuntimeFactory,
} from "../../components/apps/flunk-out-frenzy/gameHostTypes";
import { createInitialHudSnapshot } from "../../components/apps/flunk-out-frenzy/game/core/runtimeTypes";
import { useFlunkOutFrenzyBootstrap } from "./useFlunkOutFrenzyBootstrap";

const props = defineProps<{
  runtimeFactory?: GameRuntimeFactory;
}>();

const { bootstrap, bootstrapError, isBootstrapping, loadBootstrap } = useFlunkOutFrenzyBootstrap();

// The physics board is 600x1200, but the surrounding cabinet frame is
// intentionally wider so the shell reads as a full cabinet instead of a narrow
// portrait slit on laptop/desktop viewports.
const CABINET_FRAME_ASPECT_RATIO = 0.72;
const DESKTOP_BREAKPOINT_PX = 940;
const DESKTOP_HORIZONTAL_MARGIN_PX = 24;
const DESKTOP_BOTTOM_RESERVE_PX = 24;

const gameHost = ref<GameHostApi | null>(null);
const sceneElement = ref<HTMLElement | null>(null);
const isSettingsOpen = ref(false);
const runtimeBootError = ref<string | null>(null);
const runtimeLoadState = ref<GameRuntimeLoadState>("idle");
const runtimeHostKey = ref(0);
const hud = ref<GameHudSnapshot>(createInitialHudSnapshot());
const hostFrame = ref<{
  width: number | null;
  height: number | null;
}>({
  width: null,
  height: null,
});
let sceneResizeObserver: ResizeObserver | null = null;
let scheduledFrameReflowHandle: number | null = null;
let deferredFrameReflowHandle: number | null = null;

const featureFlagRows = computed(() => {
  if (!bootstrap.value) {
    return [];
  }

  return [
    {
      label: "Ljudmotor",
      value: bootstrap.value.feature_flags.audio_enabled ? "Aktiv i den lokala spelklienten" : "Avstängd",
    },
    {
      label: "Replay capture",
      value: bootstrap.value.feature_flags.replay_capture_enabled ? "Påslagen" : "Inte med i denna slice",
    },
    {
      label: "Officiella high scores",
      value: bootstrap.value.feature_flags.score_submission_enabled ? "Påslagna" : "Kommer senare",
    },
  ];
});

const sessionStatusLabel = computed(() => {
  return labelGameSessionStatus(hud.value.status);
});

const pauseLabel = computed(() => {
  return hud.value.status === "paused" ? "Fortsätt" : "Pausa";
});

const isGameplayFocusMode = computed(() => {
  if (runtimeBootError.value) {
    return false;
  }

  if (runtimeLoadState.value === "loading") {
    return true;
  }

  return hud.value.status !== "ready";
});

const canPause = computed(() => {
  if (runtimeBootError.value || runtimeLoadState.value !== "ready") {
    return false;
  }

  return hud.value.status === "running" || hud.value.status === "paused";
});

const hostFrameStyle = computed(() => {
  if (hostFrame.value.width === null || hostFrame.value.height === null) {
    return {};
  }

  return {
    width: `${hostFrame.value.width}px`,
    height: `${hostFrame.value.height}px`,
  };
});

const isAudioAvailable = computed(() => bootstrap.value?.feature_flags.audio_enabled ?? true);

const startLabel = computed(() => {
  return runtimeLoadState.value === "loading" ? "Laddar spelmotor…" : "Start";
});

const canStart = computed(() => {
  if (runtimeBootError.value) {
    return false;
  }

  return runtimeLoadState.value !== "loading" && hud.value.status !== "running";
});

const canRestart = computed(() => {
  return !runtimeBootError.value && runtimeLoadState.value === "ready";
});

const canToggleMute = computed(() => {
  return !runtimeBootError.value && isAudioAvailable.value && runtimeLoadState.value === "ready";
});

const muteLabel = computed(() => {
  if (!isAudioAvailable.value) {
    return "Ljud avstängt";
  }

  return hud.value.muted ? "Ljud av" : "Ljud på";
});

function onHudChange(nextHud: GameHudSnapshot): void {
  hud.value = nextHud;
}

function onRuntimeBootError(message: string | null): void {
  runtimeBootError.value = message;

  if (message) {
    runtimeLoadState.value = "error";
    hud.value = createInitialHudSnapshot();
  }
}

function onRuntimeLoadStateChange(nextState: GameRuntimeLoadState): void {
  runtimeLoadState.value = nextState;
}

function onStart(): void {
  if (runtimeBootError.value) {
    return;
  }

  void gameHost.value?.startGame();
}

function onPauseToggle(): void {
  if (!gameHost.value) {
    return;
  }

  if (hud.value.status === "paused") {
    gameHost.value.resumeGame();
    return;
  }

  gameHost.value.pauseGame();
}

function onRestart(): void {
  if (runtimeBootError.value) {
    return;
  }

  void gameHost.value?.restartGame();
}

function onToggleMute(): void {
  if (runtimeBootError.value || !isAudioAvailable.value) {
    return;
  }

  gameHost.value?.setMuted(!hud.value.muted);
}

function retryRuntimeHost(): void {
  runtimeBootError.value = null;
  runtimeLoadState.value = "idle";
  hud.value = createInitialHudSnapshot();
  runtimeHostKey.value += 1;
}

function updateBoardFrame(): void {
  const scene = sceneElement.value;
  if (!scene || typeof window === "undefined") {
    return;
  }

  if (window.innerWidth <= DESKTOP_BREAKPOINT_PX) {
    hostFrame.value = { width: null, height: null };
    return;
  }

  const sceneStyles = window.getComputedStyle(scene);
  const sceneRect = scene.getBoundingClientRect();
  const paddingX = parseFloat(sceneStyles.paddingLeft) + parseFloat(sceneStyles.paddingRight);

  const availableWidth = Math.max(
    scene.clientWidth - paddingX - DESKTOP_HORIZONTAL_MARGIN_PX,
    320,
  );
  const viewportHeightBudget = Math.max(
    window.innerHeight - sceneRect.top - DESKTOP_BOTTOM_RESERVE_PX,
    220,
  );
  const availableHeight = viewportHeightBudget;

  const width = Math.floor(
    Math.min(availableWidth, availableHeight * CABINET_FRAME_ASPECT_RATIO),
  );
  const height = Math.floor(width / CABINET_FRAME_ASPECT_RATIO);

  hostFrame.value = { width, height };
}

function clearScheduledBoardFrameUpdates(): void {
  if (typeof window === "undefined") {
    return;
  }

  if (scheduledFrameReflowHandle !== null) {
    window.cancelAnimationFrame(scheduledFrameReflowHandle);
    scheduledFrameReflowHandle = null;
  }

  if (deferredFrameReflowHandle !== null) {
    window.clearTimeout(deferredFrameReflowHandle);
    deferredFrameReflowHandle = null;
  }
}

function scheduleBoardFrameUpdate(): void {
  if (typeof window === "undefined") {
    return;
  }

  clearScheduledBoardFrameUpdates();

  scheduledFrameReflowHandle = window.requestAnimationFrame(() => {
    scheduledFrameReflowHandle = null;
    updateBoardFrame();

    // Breakpoint/layout transitions can settle one paint later; run one more
    // pass to avoid sticky shrunk playfield sizing after window resizes.
    deferredFrameReflowHandle = window.setTimeout(() => {
      deferredFrameReflowHandle = null;
      updateBoardFrame();
    }, 80);
  });
}

function reconnectSceneResizeObserver(): void {
  sceneResizeObserver?.disconnect();
  sceneResizeObserver = null;

  const scene = sceneElement.value;
  if (!scene || typeof ResizeObserver === "undefined") {
    return;
  }

  sceneResizeObserver = new ResizeObserver(() => {
    scheduleBoardFrameUpdate();
  });
  sceneResizeObserver.observe(scene);
}

onMounted(() => {
  reconnectSceneResizeObserver();
  scheduleBoardFrameUpdate();
  window.addEventListener("resize", scheduleBoardFrameUpdate);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", scheduleBoardFrameUpdate);
  clearScheduledBoardFrameUpdates();
  sceneResizeObserver?.disconnect();
  sceneResizeObserver = null;
});

watch(
  () => bootstrap.value,
  (nextBootstrap) => {
    if (!nextBootstrap) {
      return;
    }

    void nextTick(() => {
      reconnectSceneResizeObserver();
      scheduleBoardFrameUpdate();
    });
  },
);

watch(isGameplayFocusMode, () => {
  void nextTick(() => {
    scheduleBoardFrameUpdate();
  });
});

watch(sceneElement, () => {
  reconnectSceneResizeObserver();
  void nextTick(() => {
    scheduleBoardFrameUpdate();
  });
});
</script>

<template>
  <section class="fof-shell">
    <div class="fof-shell__haze" />

    <div
      v-if="isBootstrapping"
      data-test="bootstrap-loading"
      class="fof-shell__state fof-shell__state--loading"
    >
      <p class="fof-shell__eyebrow">
        Flunk-Out Frenzy
      </p>
      <h1 class="fof-shell__title">
        Laddar kvällspasset…
      </h1>
      <p class="fof-shell__copy">
        Hämtar bootstrap, ruleset och de första spelinställningarna innan vi
        släcker klassrummet och tänder spelmaskinen.
      </p>
    </div>

    <div
      v-else-if="bootstrapError"
      data-test="bootstrap-error"
      class="fof-shell__state fof-shell__state--error"
    >
      <p class="fof-shell__eyebrow">
        Startfel
      </p>
      <h1 class="fof-shell__title">
        Flunk-Out Frenzy kunde inte starta
      </h1>
      <p class="fof-shell__copy">
        {{ bootstrapError }}
      </p>
      <button
        class="fof-action fof-action--primary"
        type="button"
        @click="loadBootstrap"
      >
        Försök igen
      </button>
    </div>

    <div
      v-else-if="bootstrap"
      data-test="bootstrap-ready"
      class="fof-ready"
    >
      <header
        v-if="!isGameplayFocusMode"
        class="fof-ready__intro"
      >
        <p class="fof-marquee__eyebrow">
          Prototype alpha
        </p>
        <h1 class="fof-marquee__title">
          {{ bootstrap.title }}
        </h1>
        <p class="fof-marquee__summary">
          {{ bootstrap.summary }}
        </p>
      </header>

      <div
        ref="sceneElement"
        class="fof-machine-scene"
        :style="{
          '--fof-cabinet-aspect-ratio': String(CABINET_FRAME_ASPECT_RATIO),
        }"
      >
        <aside class="fof-status-cluster">
          <div class="fof-plaque">
            <span>Status</span>
            <strong>{{ sessionStatusLabel }}</strong>
          </div>
          <div class="fof-plaque">
            <span>Poäng</span>
            <strong>{{ hud.score.toLocaleString("sv-SE") }}</strong>
          </div>
          <div class="fof-plaque">
            <span>Bollar kvar</span>
            <strong>{{ hud.ballsRemaining }}</strong>
          </div>
          <div class="fof-plaque">
            <span>Multiplikator</span>
            <strong>x{{ hud.multiplier }}</strong>
          </div>
          <div class="fof-plaque">
            <span>Bonus</span>
            <strong>{{ hud.bonus.points.toLocaleString("sv-SE") }}</strong>
          </div>
          <div class="fof-plaque">
            <span>Jackpot</span>
            <strong>
              {{ hud.jackpot.points.toLocaleString("sv-SE") }}
              {{ hud.jackpot.lit ? "• Tänd" : "• Släckt" }}
            </strong>
          </div>
          <div class="fof-plaque">
            <span>Shoot again</span>
            <strong>{{ hud.ballLifecycle.shootAgainLit ? "Tänd" : "Släckt" }}</strong>
          </div>
        </aside>

        <div
          class="fof-machine-scene__host"
          :style="hostFrameStyle"
        >
          <GameHost
            :key="runtimeHostKey"
            ref="gameHost"
            :audio-enabled="bootstrap.feature_flags.audio_enabled"
            :title="bootstrap.title"
            :runtime-factory="props.runtimeFactory"
            @boot-error="onRuntimeBootError"
            @hud-change="onHudChange"
            @load-state-change="onRuntimeLoadStateChange"
          />
        </div>

        <aside class="fof-service-cluster">
          <div
            v-if="runtimeBootError"
            data-test="runtime-route-error"
            class="fof-runtime-error"
          >
            <p class="fof-runtime-error__title">
              Spelmotorn kunde inte starta
            </p>
            <p class="fof-runtime-error__body">
              {{ runtimeBootError }}
            </p>
            <button
              class="fof-action fof-action--primary"
              type="button"
              @click="retryRuntimeHost"
            >
              Försök igen
            </button>
          </div>

          <div class="fof-keyguide">
            <p class="fof-keyguide__eyebrow">
              Kontroller
            </p>
            <div class="fof-keyguide__row">
              <div class="fof-keycaps">
                <span class="fof-keycap">L Shift</span>
                <span class="fof-keycap">R Shift</span>
              </div>
              <span>Flippers</span>
            </div>
            <div class="fof-keyguide__row">
              <div class="fof-keycaps">
                <span class="fof-keycap">Space</span>
              </div>
              <span>Launch</span>
            </div>
          </div>

          <div class="fof-controls">
            <button
              class="fof-action fof-action--primary"
              type="button"
              :disabled="!canStart"
              @click="onStart"
            >
              {{ startLabel }}
            </button>
            <button
              class="fof-action"
              type="button"
              :disabled="!canPause"
              @click="onPauseToggle"
            >
              {{ pauseLabel }}
            </button>
            <button
              class="fof-action"
              type="button"
              :disabled="!canRestart"
              @click="onRestart"
            >
              Starta om
            </button>
            <button
              class="fof-action"
              type="button"
              :disabled="!canToggleMute"
              @click="onToggleMute"
            >
              {{ muteLabel }}
            </button>
          </div>

          <button
            data-test="settings-toggle"
            class="fof-action fof-action--ghost"
            type="button"
            :aria-expanded="isSettingsOpen"
            @click="isSettingsOpen = !isSettingsOpen"
          >
            Inställningar
          </button>
        </aside>
      </div>

      <Transition name="fof-settings">
        <div
          v-if="isSettingsOpen"
          class="fof-settings"
          @click.self="isSettingsOpen = false"
        >
          <aside
            data-test="settings-panel"
            class="fof-settings__panel"
          >
            <div class="fof-settings__header">
              <div>
                <p class="fof-settings__eyebrow">
                  System & bootstrap
                </p>
                <h2 class="fof-settings__title">
                  Spelinställningar
                </h2>
              </div>
              <button
                class="fof-action fof-action--ghost"
                type="button"
                @click="isSettingsOpen = false"
              >
                Stäng
              </button>
            </div>

            <dl class="fof-settings__meta">
              <div>
                <dt>Appversion</dt>
                <dd>{{ bootstrap.app_version }}</dd>
              </div>
              <div>
                <dt>Ruleset</dt>
                <dd data-test="ruleset-id">
                  {{ bootstrap.ruleset_id }}
                </dd>
              </div>
            </dl>

            <dl class="fof-settings__flags">
              <div
                v-for="flag in featureFlagRows"
                :key="flag.label"
                class="fof-settings__flag"
              >
                <dt>{{ flag.label }}</dt>
                <dd>{{ flag.value }}</dd>
              </div>
            </dl>
          </aside>
        </div>
      </Transition>
    </div>
  </section>
</template>

<style scoped>
.fof-shell {
  --fof-ink: #241611;
  --fof-paper: #f2e6d1;
  --fof-pine: #1f3228;
  --fof-pine-soft: #2f493b;
  --fof-brass: #ddb770;
  --fof-coral: #ff5d92;
  --fof-coral-deep: #de2f74;
  --fof-text: #f7f0e4;
  --fof-text-soft: rgba(247, 240, 228, 0.84);
  position: relative;
  min-height: 100%;
  height: 100%;
  padding: clamp(1rem, 2vw, 2rem);
  overflow: hidden;
  color: var(--fof-text);
  background:
    radial-gradient(circle at 18% 10%, rgba(161, 233, 179, 0.1), transparent 18%),
    radial-gradient(circle at 82% 18%, rgba(255, 136, 164, 0.08), transparent 22%),
    linear-gradient(180deg, #22352b 0%, #26392e 16%, #62422e 16%, #24150e 100%);
}

.fof-shell__haze {
  position: absolute;
  inset: -8% -8% auto;
  height: 26vh;
  background:
    radial-gradient(circle at 50% 0%, rgba(255, 93, 146, 0.14), transparent 38%),
    radial-gradient(circle at 32% 18%, rgba(161, 233, 179, 0.15), transparent 26%);
  filter: blur(44px);
  pointer-events: none;
}

.fof-shell__state {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 1rem;
  align-content: center;
  max-width: 42rem;
  min-height: calc(100dvh - 9rem);
  margin: 0 auto;
}

.fof-shell__state--error {
  justify-items: start;
}

.fof-ready {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 0.45rem;
  min-height: 0;
  height: 100%;
}

.fof-ready__intro {
  display: grid;
  gap: 0.35rem;
  width: min(34rem, 100%);
  padding: 0.35rem 0.9rem 0;
}

.fof-runtime-error {
  display: grid;
  gap: 0.7rem;
  padding: 1rem 1.05rem;
  border: 1px solid rgba(255, 162, 176, 0.3);
  border-radius: 1.1rem;
  background:
    linear-gradient(180deg, rgba(72, 18, 26, 0.92), rgba(38, 11, 16, 0.92));
  box-shadow:
    inset 0 1px 0 rgba(255, 219, 227, 0.12),
    0 14px 30px rgba(11, 6, 5, 0.26);
}

.fof-runtime-error__title,
.fof-runtime-error__body {
  margin: 0;
}

.fof-runtime-error__title {
  font-size: 0.92rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.fof-runtime-error__body {
  color: rgba(247, 240, 228, 0.82);
  line-height: 1.5;
}

.fof-shell__eyebrow,
.fof-settings__eyebrow,
.fof-marquee__eyebrow,
.fof-keyguide__eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.fof-shell__eyebrow,
.fof-settings__eyebrow,
.fof-keyguide__eyebrow {
  color: #9ef3b0;
}

.fof-shell__title {
  margin: 0;
  font-size: clamp(2.1rem, 5vw, 3.8rem);
  line-height: 0.96;
  letter-spacing: -0.04em;
  font-weight: 800;
  text-wrap: balance;
}

.fof-shell__copy {
  margin: 0;
  font-size: 0.98rem;
  line-height: 1.62;
  color: var(--fof-text-soft);
}

.fof-machine-scene {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  height: 100%;
  padding: clamp(0.85rem, 1.6vw, 1.25rem);
  border-radius: 1.85rem;
  background: linear-gradient(180deg, rgba(17, 22, 19, 0.85), rgba(17, 22, 19, 0.92));
  box-shadow:
    inset 0 1px 0 rgba(255, 247, 233, 0.14),
    0 24px 48px rgba(13, 8, 6, 0.36);
}

.fof-machine-scene::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 16%, rgba(109, 188, 136, 0.12), transparent 28%),
    radial-gradient(circle at 22% 76%, rgba(255, 112, 163, 0.1), transparent 24%),
    radial-gradient(circle at 80% 72%, rgba(108, 170, 255, 0.1), transparent 26%),
    linear-gradient(180deg, rgba(12, 16, 14, 0.22), rgba(12, 16, 14, 0.74)),
    linear-gradient(90deg, rgba(14, 18, 16, 0.68), rgba(14, 18, 16, 0.22) 24%, rgba(14, 18, 16, 0.22) 76%, rgba(14, 18, 16, 0.68));
}

.fof-machine-scene::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 44%, rgba(255, 255, 255, 0.06), transparent 22%),
    radial-gradient(circle at 50% 92%, rgba(255, 148, 177, 0.06), transparent 20%);
  pointer-events: none;
}

.fof-marquee,
.fof-status-cluster,
.fof-service-cluster,
.fof-machine-scene__host {
  position: relative;
  z-index: 1;
}

.fof-marquee {
  position: absolute;
  top: clamp(0.85rem, 1.8vw, 1.4rem);
  left: 50%;
  transform: translateX(-50%);
  display: grid;
  gap: 0.28rem;
  z-index: 2;
  width: min(23rem, calc(100% - 24rem));
  padding: 0.7rem 0.9rem 0.78rem;
  border-radius: 1rem;
  background:
    linear-gradient(180deg, rgba(28, 40, 33, 0.86), rgba(18, 27, 22, 0.84));
  border: 1px solid rgba(255, 243, 219, 0.1);
  box-shadow: inset 0 1px 0 rgba(255, 245, 225, 0.05);
  backdrop-filter: blur(10px);
  text-align: center;
}

.fof-marquee__eyebrow {
  color: var(--fof-brass);
}

.fof-marquee__title {
  margin: 0;
  font-size: clamp(1.95rem, 4vw, 3rem);
  line-height: 0.94;
  letter-spacing: -0.05em;
  font-weight: 900;
}

.fof-marquee__summary {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.45;
  color: var(--fof-text-soft);
}

.fof-machine-scene__host {
  width: min(
    calc((100dvh - 6rem) * var(--fof-cabinet-aspect-ratio, 0.76)),
    calc(100% - 1rem)
  );
  max-width: 100%;
  z-index: 1;
}

.fof-status-cluster,
.fof-service-cluster {
  display: grid;
  position: absolute;
  bottom: clamp(0.95rem, 1.8vw, 1.4rem);
  z-index: 2;
  width: min(8.7rem, 14vw);
}

.fof-status-cluster {
  gap: 0.7rem;
  left: clamp(0.95rem, 1.8vw, 1.4rem);
}

.fof-service-cluster {
  gap: 0.8rem;
  right: clamp(0.95rem, 1.8vw, 1.4rem);
}

.fof-plaque,
.fof-keyguide,
.fof-controls {
  border-radius: 1rem;
  background:
    linear-gradient(180deg, rgba(21, 31, 25, 0.72), rgba(15, 21, 18, 0.78));
  border: 1px solid rgba(255, 244, 222, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 247, 232, 0.05);
  backdrop-filter: blur(8px);
}

.fof-plaque {
  display: grid;
  gap: 0.3rem;
  padding: 0.78rem 0.88rem;
}

.fof-plaque span {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: rgba(247, 240, 228, 0.65);
}

.fof-plaque strong {
  font-size: clamp(1.02rem, 1.35vw, 1.28rem);
  line-height: 1.04;
  font-weight: 800;
}

.fof-keyguide {
  display: grid;
  gap: 0.7rem;
  padding: 0.9rem;
}

.fof-keyguide__row {
  display: grid;
  gap: 0.45rem;
}

.fof-keyguide__row > span:last-child {
  font-size: 0.84rem;
  font-weight: 700;
  color: var(--fof-text-soft);
}

.fof-keycaps {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.fof-keycap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.15rem;
  padding: 0.48rem 0.72rem;
  border-radius: 0.7rem;
  background:
    linear-gradient(180deg, rgba(245, 234, 214, 0.98), rgba(215, 198, 171, 0.98));
  color: var(--fof-ink);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.fof-controls {
  display: grid;
  gap: 0.6rem;
  padding: 0.72rem;
}

.fof-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3rem;
  padding: 0.78rem 1rem;
  border: 1px solid rgba(255, 244, 222, 0.12);
  border-radius: 0.85rem;
  background:
    linear-gradient(180deg, rgba(39, 54, 45, 0.98), rgba(22, 31, 26, 0.98));
  color: var(--fof-text);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  cursor: pointer;
  transition:
    transform 140ms ease,
    border-color 140ms ease,
    background-color 140ms ease;
}

.fof-action:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(255, 244, 222, 0.24);
}

.fof-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.fof-action--primary {
  border-color: rgba(255, 198, 221, 0.24);
  background: linear-gradient(180deg, var(--fof-coral), var(--fof-coral-deep));
  color: #240d16;
}

.fof-action--ghost {
  width: 100%;
  background:
    linear-gradient(180deg, rgba(95, 66, 44, 0.95), rgba(63, 42, 29, 0.95));
}

.fof-settings {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  justify-content: flex-end;
  padding: 1.5rem;
  background: rgba(10, 12, 11, 0.48);
  backdrop-filter: blur(12px);
}

.fof-settings__panel {
  width: min(27rem, 100%);
  display: grid;
  gap: 1.3rem;
  align-content: start;
  padding: 1.35rem;
  border-radius: 1.2rem;
  background:
    linear-gradient(180deg, rgba(29, 42, 35, 0.98), rgba(19, 27, 23, 0.98));
  border: 1px solid rgba(255, 244, 222, 0.12);
  box-shadow: 0 22px 44px rgba(0, 0, 0, 0.32);
}

.fof-settings__header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.fof-settings__title {
  margin: 0.2rem 0 0;
  font-size: 1.75rem;
  line-height: 1;
}

.fof-settings__meta,
.fof-settings__flags {
  display: grid;
  gap: 0.75rem;
}

.fof-settings__meta > div,
.fof-settings__flag {
  display: grid;
  gap: 0.2rem;
  padding: 0.9rem 1rem;
  border-radius: 0.95rem;
  background: rgba(255, 247, 232, 0.06);
}

.fof-settings__meta dt,
.fof-settings__flag dt {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(247, 240, 228, 0.6);
}

.fof-settings__meta dd,
.fof-settings__flag dd {
  margin: 0;
  font-size: 0.94rem;
  line-height: 1.5;
  color: var(--fof-text);
}

.fof-settings-enter-active,
.fof-settings-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.fof-settings-enter-from,
.fof-settings-leave-to {
  opacity: 0;
}

.fof-settings-enter-from .fof-settings__panel,
.fof-settings-leave-to .fof-settings__panel {
  transform: translateX(1.5rem);
}

@media (max-width: 1180px) {
  .fof-status-cluster,
  .fof-service-cluster {
    width: min(8rem, 19vw);
  }
}

@media (max-width: 940px) {
  .fof-ready {
    grid-template-rows: auto minmax(0, 1fr);
  }

  .fof-ready__intro {
    width: 100%;
    padding: 0;
  }

  .fof-machine-scene {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    align-items: start;
    justify-items: stretch;
    padding: 1rem;
    gap: 1rem;
  }

  .fof-status-cluster,
  .fof-service-cluster {
    position: relative;
    inset: auto;
    width: 100%;
    transform: none;
  }

  .fof-machine-scene__host {
    width: 100%;
    height: auto;
  }

  .fof-status-cluster,
  .fof-service-cluster {
    bottom: auto;
  }
}

@media (max-width: 767px) {
  .fof-shell {
    padding: 0.75rem;
  }

  .fof-shell__state,
  .fof-ready,
  .fof-machine-scene {
    min-height: 0;
    height: 100%;
  }

  .fof-keycaps {
    gap: 0.35rem;
  }

  .fof-settings {
    padding: 0.75rem;
  }
}
</style>
