<script setup lang="ts">
defineProps<{
  runtimeBootError: string | null;
  canStart: boolean;
  canPause: boolean;
  canRestart: boolean;
  canToggleMute: boolean;
  startLabel: string;
  pauseLabel: string;
  muteLabel: string;
  isSettingsOpen: boolean;
}>();

defineEmits<{
  (e: "retry-runtime"): void;
  (e: "start"): void;
  (e: "pause-toggle"): void;
  (e: "restart"): void;
  (e: "toggle-mute"): void;
  (e: "toggle-settings"): void;
}>();
</script>

<template>
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
        @click="$emit('retry-runtime')"
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
        @click="$emit('start')"
      >
        {{ startLabel }}
      </button>
      <button
        class="fof-action"
        type="button"
        :disabled="!canPause"
        @click="$emit('pause-toggle')"
      >
        {{ pauseLabel }}
      </button>
      <button
        class="fof-action"
        type="button"
        :disabled="!canRestart"
        @click="$emit('restart')"
      >
        Starta om
      </button>
      <button
        class="fof-action"
        type="button"
        :disabled="!canToggleMute"
        @click="$emit('toggle-mute')"
      >
        {{ muteLabel }}
      </button>
    </div>

    <button
      data-test="settings-toggle"
      class="fof-action fof-action--ghost"
      type="button"
      :aria-expanded="isSettingsOpen"
      @click="$emit('toggle-settings')"
    >
      Inställningar
    </button>
  </aside>
</template>
