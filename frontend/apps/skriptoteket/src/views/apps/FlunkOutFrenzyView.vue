<script setup lang="ts">
/**
 * Flunk-Out Frenzy shell view.
 *
 * This bespoke route owns the app bootstrap and presents the first viewport as
 * a single game composition. The shell keeps bootstrap/loading/settings logic
 * at the route layer while delegating the future playfield runtime to
 * `GameHost.vue`.
 */

import { computed, nextTick, ref, watch } from "vue";

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
import { useCabinetFrameSizing } from "./composables/useCabinetFrameSizing";

// Components
import FofStatusCluster from "./components/FofStatusCluster.vue";
import FofServiceCluster from "./components/FofServiceCluster.vue";
import FofSettingsPanel from "./components/FofSettingsPanel.vue";

const props = defineProps<{
  runtimeFactory?: GameRuntimeFactory;
}>();

const { bootstrap, bootstrapError, isBootstrapping, loadBootstrap } = useFlunkOutFrenzyBootstrap();

const gameHost = ref<GameHostApi | null>(null);
const sceneElement = ref<HTMLElement | null>(null);
const isSettingsOpen = ref(false);
const runtimeBootError = ref<string | null>(null);
const runtimeLoadState = ref<GameRuntimeLoadState>("idle");
const runtimeHostKey = ref(0);
const hud = ref<GameHudSnapshot>(createInitialHudSnapshot());

const { hostFrameStyle, updateBoardFrame } = useCabinetFrameSizing(sceneElement);

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

watch(
  () => bootstrap.value,
  (nextBootstrap) => {
    if (!nextBootstrap) {
      return;
    }

    void nextTick(() => {
      updateBoardFrame();
    });
  },
);

watch(isGameplayFocusMode, () => {
  void nextTick(() => {
    updateBoardFrame();
  });
});
</script>

<template>
  <section class="fof-shell fof-game-container">
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
      >
        <FofStatusCluster
          :hud="hud"
          :session-status-label="sessionStatusLabel"
        />

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

        <FofServiceCluster
          :runtime-boot-error="runtimeBootError"
          :can-start="canStart"
          :can-pause="canPause"
          :can-restart="canRestart"
          :can-toggle-mute="canToggleMute"
          :start-label="startLabel"
          :pause-label="pauseLabel"
          :mute-label="muteLabel"
          :is-settings-open="isSettingsOpen"
          @retry-runtime="retryRuntimeHost"
          @start="onStart"
          @pause-toggle="onPauseToggle"
          @restart="onRestart"
          @toggle-mute="onToggleMute"
          @toggle-settings="isSettingsOpen = !isSettingsOpen"
        />
      </div>

      <FofSettingsPanel
        :is-settings-open="isSettingsOpen"
        :bootstrap="bootstrap"
        :feature-flag-rows="featureFlagRows"
        @close="isSettingsOpen = false"
      />
    </div>
  </section>
</template>

<style>
@import "./styles/fof-shell-layout.css";
@import "./styles/fof-shell-panels.css";
</style>
