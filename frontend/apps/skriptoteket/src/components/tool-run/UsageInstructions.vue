<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { components } from "../../api/openapi";
import { apiPost } from "../../api/client";
import UiMarkdown from "../ui/UiMarkdown.vue";

type MarkUsageInstructionsSeenResponse =
  components["schemas"]["MarkUsageInstructionsSeenResponse"];

const props = defineProps<{
  toolId: string;
  instructions: string;
  isSeen: boolean;
}>();

const isOpen = ref(false);
const hasMarkedSeen = ref(false);
const isMarkingSeen = ref(false);

const contentId = computed(() => `tool-${props.toolId}-usage-instructions`);

async function markSeen(): Promise<void> {
  if (hasMarkedSeen.value || isMarkingSeen.value) return;
  isMarkingSeen.value = true;

  try {
    await apiPost<MarkUsageInstructionsSeenResponse>(
      `/api/v1/tools/${encodeURIComponent(props.toolId)}/usage-instructions/seen`,
    );
    hasMarkedSeen.value = true;
  } catch {
    // If this fails, the UX still works; we'll try again on next open.
  } finally {
    isMarkingSeen.value = false;
  }
}

function openIfUnseen(): void {
  if (props.isSeen) return;
  isOpen.value = true;
  void markSeen();
}

function toggle(): void {
  isOpen.value = !isOpen.value;
  if (isOpen.value && !props.isSeen) {
    void markSeen();
  }
}

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function onEnter(el: Element, done: () => void): void {
  const element = el as HTMLElement;
  if (prefersReducedMotion()) {
    done();
    return;
  }

  element.style.overflow = "hidden";
  element.style.height = "0";
  element.style.opacity = "0";

  void element.offsetHeight;

  const targetHeight = element.scrollHeight;
  element.style.transition = "height 200ms ease, opacity 200ms ease";
  element.style.height = `${targetHeight}px`;
  element.style.opacity = "1";

  window.setTimeout(() => {
    element.style.transition = "";
    element.style.height = "";
    element.style.overflow = "";
    element.style.opacity = "";
    done();
  }, 220);
}

function onLeave(el: Element, done: () => void): void {
  const element = el as HTMLElement;
  if (prefersReducedMotion()) {
    done();
    return;
  }

  element.style.overflow = "hidden";
  element.style.height = `${element.scrollHeight}px`;
  element.style.opacity = "1";

  void element.offsetHeight;

  element.style.transition = "height 200ms ease, opacity 200ms ease";
  element.style.height = "0";
  element.style.opacity = "0";

  window.setTimeout(() => {
    element.style.transition = "";
    element.style.height = "";
    element.style.overflow = "";
    element.style.opacity = "";
    done();
  }, 220);
}

watch(
  () => props.toolId,
  () => {
    hasMarkedSeen.value = props.isSeen;
    isOpen.value = false;
    openIfUnseen();
  },
  { immediate: true },
);

watch(
  () => props.isSeen,
  (isSeen, prevSeen) => {
    if (isSeen) {
      hasMarkedSeen.value = true;
      return;
    }

    if (prevSeen && !isSeen) {
      hasMarkedSeen.value = false;
      openIfUnseen();
    }
  },
);
</script>

<template>
  <div class="border-b border-navy/20">
    <button
      type="button"
      class="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-canvas/50 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40"
      :aria-expanded="isOpen"
      :aria-controls="contentId"
      @click="toggle"
    >
      <span class="text-xs font-semibold uppercase tracking-wide text-navy">
        Så här gör du
      </span>
      <span
        class="font-mono text-navy/60 transition-transform"
        :class="{ 'rotate-180': isOpen }"
      >
        ▾
      </span>
    </button>

    <Transition
      :css="false"
      @enter="onEnter"
      @leave="onLeave"
    >
      <div
        v-if="isOpen"
        :id="contentId"
        class="px-4 pb-4"
      >
        <UiMarkdown :markdown="props.instructions" />
      </div>
    </Transition>
  </div>
</template>
