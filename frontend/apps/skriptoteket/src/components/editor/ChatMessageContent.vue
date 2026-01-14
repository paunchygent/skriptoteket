<script setup lang="ts">
import { ref, watch } from "vue";

type ChatMessageContentProps = {
  content: string;
};

const props = defineProps<ChatMessageContentProps>();

const stableText = ref("");
const fadeText = ref("");
const fadeKey = ref(0);

function currentText(): string {
  return stableText.value + fadeText.value;
}

function resetTo(text: string): void {
  stableText.value = text;
  fadeText.value = "";
  fadeKey.value += 1;
}

watch(
  () => props.content,
  (next) => {
    const target = next ?? "";
    const current = currentText();

    if (!target) {
      stableText.value = "";
      fadeText.value = "";
      fadeKey.value += 1;
      return;
    }

    if (!target.startsWith(current)) {
      resetTo(target);
      return;
    }

    if (target.length === current.length) {
      return;
    }

    const delta = target.slice(current.length);
    stableText.value = stableText.value + fadeText.value;
    fadeText.value = delta;
    fadeKey.value += 1;
  },
  { immediate: true },
);
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
