<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    open: boolean;
    durationMs?: number;
  }>(),
  {
    durationMs: 200,
  },
);

const timeoutMs = computed(() => Math.max(0, props.durationMs + 20));

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
  element.style.transition = `height ${props.durationMs}ms var(--huleedu-ease-default, ease), opacity ${props.durationMs}ms var(--huleedu-ease-default, ease)`;
  element.style.height = `${targetHeight}px`;
  element.style.opacity = "1";

  window.setTimeout(() => {
    element.style.transition = "";
    element.style.height = "";
    element.style.overflow = "";
    element.style.opacity = "";
    done();
  }, timeoutMs.value);
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

  element.style.transition = `height ${props.durationMs}ms var(--huleedu-ease-default, ease), opacity ${props.durationMs}ms var(--huleedu-ease-default, ease)`;
  element.style.height = "0";
  element.style.opacity = "0";

  window.setTimeout(() => {
    element.style.transition = "";
    element.style.height = "";
    element.style.overflow = "";
    element.style.opacity = "";
    done();
  }, timeoutMs.value);
}
</script>

<template>
  <Transition
    :css="false"
    @enter="onEnter"
    @leave="onLeave"
  >
    <div v-if="props.open">
      <slot />
    </div>
  </Transition>
</template>
