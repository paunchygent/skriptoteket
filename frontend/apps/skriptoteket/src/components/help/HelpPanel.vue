<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import HelpIndex from "./HelpIndex.vue";
import { prefetchHelpTopics, resolveHelpTopicComponent } from "./helpTopics";
import { resolveHelpTopic, useHelp } from "./useHelp";

const route = useRoute();
const { isOpen, activeTopic, close, showIndex, showTopic } = useHelp();
const hasPrefetched = ref(false);

const routeTopic = computed(() => resolveHelpTopic(route.name));
const activeTopicComponent = computed(() => resolveHelpTopicComponent(activeTopic.value));

function syncToRoute(): void {
  if (routeTopic.value) {
    showTopic(routeTopic.value);
  } else {
    showIndex();
  }
}

function prefetchDefaultTopics(): void {
  if (hasPrefetched.value) {
    return;
  }
  hasPrefetched.value = true;
  prefetchHelpTopics(["home", "browse_professions", "browse_categories", "browse_tools"]);
}

onMounted(() => {
  if (isOpen.value) {
    syncToRoute();
    prefetchDefaultTopics();
  }
});

watch(
  () => isOpen.value,
  (open) => {
    if (open) {
      syncToRoute();
      prefetchDefaultTopics();
    }
  },
);

watch(
  () => route.fullPath,
  () => {
    if (isOpen.value) {
      syncToRoute();
    }
  },
);
</script>

<template>
  <Teleport to="body">
    <Transition name="help-backdrop">
      <div
        v-if="isOpen"
        class="help-backdrop fixed inset-0 bg-navy/40"
        @click="close"
      />
    </Transition>

    <Transition name="help-panel">
      <aside
        v-if="isOpen"
        id="help-panel"
        class="help-panel border border-navy bg-canvas shadow-brutal flex flex-col text-navy"
        role="dialog"
        aria-modal="false"
        aria-labelledby="help-panel-title"
      >
        <header class="flex items-center justify-between gap-3 p-4 border-b border-navy/20">
          <h2
            id="help-panel-title"
            class="text-lg font-semibold text-navy"
          >
            Hjälp
          </h2>
          <button
            type="button"
            class="w-10 h-10 border border-navy text-navy text-xl leading-none flex items-center justify-center hover:bg-navy hover:text-canvas transition-colors"
            aria-label="Stäng"
            @click="close"
          >
            &times;
          </button>
        </header>

        <div class="flex-1 overflow-y-auto p-6 space-y-6">
          <HelpIndex v-if="!activeTopic" />
          <component
            :is="activeTopicComponent"
            v-else-if="activeTopicComponent"
          />
          <HelpIndex v-else />
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.help-backdrop {
  z-index: var(--huleedu-z-overlay);
}

.help-panel {
  position: fixed;
  top: calc(var(--huleedu-space-4) + var(--huleedu-header-height));
  right: var(--huleedu-space-4);
  bottom: var(--huleedu-space-4);
  width: min(420px, calc(100vw - var(--huleedu-space-8)));
  z-index: var(--huleedu-z-modal);
}

@media (max-width: 767px) {
  .help-panel {
    top: calc(
      var(--huleedu-header-height) + var(--huleedu-space-4) + env(safe-area-inset-top, 0px)
    );
    right: calc(var(--huleedu-space-4) + env(safe-area-inset-right, 0px));
    bottom: calc(var(--huleedu-space-4) + env(safe-area-inset-bottom, 0px));
    left: calc(var(--huleedu-space-4) + env(safe-area-inset-left, 0px));
    width: auto;
  }
}

.help-backdrop-enter-active,
.help-backdrop-leave-active {
  transition: opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.help-backdrop-enter-from,
.help-backdrop-leave-to {
  opacity: 0;
}

.help-panel-enter-active,
.help-panel-leave-active {
  transition: transform var(--huleedu-duration-slow) var(--huleedu-ease-default),
    opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.help-panel-enter-from,
.help-panel-leave-to {
  transform: translateY(8px);
  opacity: 0;
}
</style>
