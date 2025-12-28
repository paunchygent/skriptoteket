<script setup lang="ts">
import { computed } from "vue";

import type { DraftLockState } from "../../composables/editor/useDraftLock";

type DraftLockBannerProps = {
  state: DraftLockState;
  message: string | null;
  expiresAt: string | null;
  canForce: boolean;
  isBusy: boolean;
};

const props = defineProps<DraftLockBannerProps>();

const emit = defineEmits<{ (event: "force"): void }>();

const isVisible = computed(() => props.state !== "inactive");
const canForceTakeover = computed(() => props.state === "locked" && props.canForce);

const variantClass = computed(() => {
  switch (props.state) {
    case "owner":
      return "border-success bg-success/10 text-success";
    case "locked":
      return "border-burgundy bg-burgundy/10 text-burgundy";
    case "acquiring":
      return "border-navy/30 bg-canvas/40 text-navy/70";
    default:
      return "border-navy/30 bg-canvas/40 text-navy/70";
  }
});

const fallbackMessage = computed(() => {
  if (props.state === "owner") {
    return "Du har redigeringslåset. Förnyas automatiskt.";
  }
  if (props.state === "locked") {
    return "Utkastet är låst av en annan användare. Du kan läsa men inte spara eller testköra.";
  }
  if (props.state === "acquiring") {
    return "Säkrar redigeringslås...";
  }
  return null;
});

const expiresLabel = computed(() => {
  if (!props.expiresAt) return null;
  const parsed = new Date(props.expiresAt);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return new Intl.DateTimeFormat("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
  }).format(parsed);
});

const messageText = computed(() => props.message ?? fallbackMessage.value);
</script>

<template>
  <div
    v-if="isVisible && messageText"
    class="flex flex-col gap-3 border p-3 shadow-brutal-sm text-sm"
    :class="variantClass"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="space-y-1">
        <p class="font-semibold">
          {{ messageText }}
        </p>
        <p
          v-if="expiresLabel && state === 'locked'"
          class="text-xs opacity-80"
        >
          Låset går ut {{ expiresLabel }}.
        </p>
      </div>

      <button
        v-if="canForceTakeover"
        type="button"
        class="btn-cta btn-sm"
        :disabled="isBusy"
        @click="emit('force')"
      >
        {{ isBusy ? "Tar över..." : "Ta över lås" }}
      </button>
    </div>
  </div>
</template>
