<script setup lang="ts">
/**
 * Global contextual help drawer.
 *
 * This component resolves the currently visible help topic from the active SPA
 * route and nested workspace context, while keeping the signed-out public
 * landing page on the logged-out index instead of authenticated dashboard help.
 *
 * The panel is non-modal and has no scrim: the page behind stays usable. Every
 * entry, including one while help is already open, moves focus into the panel;
 * Escape inside the panel closes it, and `useHelp` returns focus to the opener.
 * While a covering layer suspends help, the panel is inert.
 */
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import HelpIndex from "./HelpIndex.vue";
import { prefetchHelpTopics, resolveHelpTopicComponent } from "./helpTopics";
import { resolveHelpTopic, useHelp } from "./useHelp";
import { useAuthStore } from "../../stores/auth";

const route = useRoute();
const auth = useAuthStore();
const { isOpen, activeTopic, helpContext, entryRequest, isSuspended, close, showIndex, showTopic } =
  useHelp();
/** `undefined` removes the attribute; `inert="false"` would still be inert. */
const panelInert = computed(() => (isSuspended.value ? true : undefined));
const hasPrefetched = ref(false);
const panelRef = ref<HTMLElement | null>(null);

const routeTopic = computed(() => {
  if (route.name === "home" && !auth.isAuthenticated && !helpContext.value) {
    return null;
  }
  return resolveHelpTopic(route.name, helpContext.value);
});
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

/** Escape closes help only while focus is in it; outer layers keep their own Escape. */
function onEscape(): void {
  close();
}

async function focusPanel(): Promise<void> {
  await nextTick();
  panelRef.value?.focus({ preventScroll: true });
}

function onOpened(): void {
  syncToRoute();
  prefetchDefaultTopics();
}

onMounted(() => {
  if (isOpen.value) {
    onOpened();
    void focusPanel();
  }
});

watch(
  () => isOpen.value,
  (open) => {
    if (open) {
      onOpened();
    }
  },
);

watch(entryRequest, () => {
  if (isOpen.value) {
    void focusPanel();
  }
});

watch(
  () => route.fullPath,
  () => {
    if (isOpen.value) {
      syncToRoute();
    }
  },
);

watch(
  () => helpContext.value,
  () => {
    if (isOpen.value) {
      syncToRoute();
    }
  },
);
</script>

<template>
  <Teleport to="body">
    <Transition name="help-panel">
      <aside
        v-if="isOpen"
        id="help-panel"
        ref="panelRef"
        tabindex="-1"
        :inert="panelInert"
        class="help-panel border border-navy shadow-md flex flex-col text-navy"
        role="dialog"
        aria-modal="false"
        aria-labelledby="help-panel-title"
        @keydown.esc.stop="onEscape"
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
            @click="close()"
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
.help-panel {
  position: fixed;
  top: calc(var(--huleedu-space-4) + var(--huleedu-header-height));
  right: var(--huleedu-space-4);
  bottom: var(--huleedu-space-4);
  width: min(420px, calc(100vw - var(--huleedu-space-8)));
  background-color: var(--surface-modal);
  z-index: var(--huleedu-z-modal);
}

.help-panel:focus-visible {
  outline: 2px solid var(--huleedu-action-40);
  outline-offset: 2px;
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
