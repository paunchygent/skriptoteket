<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch, withDefaults } from "vue";

type ChatMessageContentProps = {
  content: string;
  reveal?: "instant" | "type";
};

const props = withDefaults(defineProps<ChatMessageContentProps>(), {
  reveal: "instant",
});

const stableText = ref("");
const fadeText = ref("");
const fadeKey = ref(0);

const shouldReveal = computed(() => props.reveal === "type");

const CHARS_PER_SECOND = 90;
const MAX_CHUNK_SIZE = 18;

let rafId: number | null = null;
let lastTickMs = 0;
let pendingCharBudget = 0;

function stopTick(): void {
  if (rafId === null) {
    return;
  }
  window.cancelAnimationFrame(rafId);
  rafId = null;
  lastTickMs = 0;
  pendingCharBudget = 0;
}

function currentText(): string {
  return stableText.value + fadeText.value;
}

function resetInstant(text: string): void {
  stableText.value = text;
  fadeText.value = "";
  fadeKey.value += 1;
}

function ensureTickScheduled(): void {
  if (rafId !== null) {
    return;
  }
  rafId = window.requestAnimationFrame(tick);
}

function tick(now: number): void {
  rafId = null;

  if (!shouldReveal.value) {
    resetInstant(props.content);
    return;
  }

  const target = props.content ?? "";
  const current = currentText();
  if (current.length >= target.length) {
    return;
  }

  if (lastTickMs <= 0) {
    lastTickMs = now;
  }

  const elapsedMs = Math.max(0, now - lastTickMs);
  lastTickMs = now;
  pendingCharBudget += (elapsedMs / 1000) * CHARS_PER_SECOND;

  let chunkSize = Math.floor(pendingCharBudget);
  if (chunkSize <= 0) {
    ensureTickScheduled();
    return;
  }
  chunkSize = Math.min(chunkSize, MAX_CHUNK_SIZE);
  pendingCharBudget -= chunkSize;

  const start = current.length;
  const end = Math.min(target.length, start + chunkSize);
  const nextChunk = target.slice(start, end);

  stableText.value = stableText.value + fadeText.value;
  fadeText.value = nextChunk;
  fadeKey.value += 1;

  if (end < target.length) {
    ensureTickScheduled();
  }
}

watch(
  () => [props.content, props.reveal] as const,
  () => {
    const target = props.content ?? "";
    if (!shouldReveal.value) {
      stopTick();
      resetInstant(target);
      return;
    }

    const current = currentText();
    if (!target.startsWith(current)) {
      stableText.value = "";
      fadeText.value = "";
      fadeKey.value += 1;
      lastTickMs = 0;
      pendingCharBudget = 0;
    }

    if (currentText().length >= target.length) {
      return;
    }

    if (currentText().length === 0) {
      pendingCharBudget = Math.max(pendingCharBudget, 8);
    }
    ensureTickScheduled();
  },
  { immediate: true },
);

onBeforeUnmount(() => stopTick());
</script>

<template>
  <span>{{ stableText }}</span>
  <span
    v-if="fadeText"
    :key="fadeKey"
    class="chat-reveal-chunk"
  >
    {{ fadeText }}
  </span>
</template>

<style scoped>
.chat-reveal-chunk {
  opacity: 0;
  animation: chat-reveal-fade 160ms var(--huleedu-ease-default, ease) forwards;
  will-change: opacity;
}

@keyframes chat-reveal-fade {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .chat-reveal-chunk {
    animation: none;
    opacity: 1;
  }
}
</style>
