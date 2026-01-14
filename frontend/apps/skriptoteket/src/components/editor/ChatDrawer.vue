<script setup lang="ts">
import { computed, withDefaults } from "vue";
import { RouterLink } from "vue-router";

import type { EditorChatMessage } from "../../composables/editor/chat/editorChatTypes";
import type { RemoteFallbackPrompt } from "./remoteFallbackPrompt";
import ChatComposer from "./ChatComposer.vue";
import ChatMessageList from "./ChatMessageList.vue";
import SystemMessage from "../ui/SystemMessage.vue";
import type { SystemMessageVariant } from "../ui/SystemMessage.vue";

type ChatDrawerProps = {
  variant?: "drawer" | "column";
  isOpen: boolean;
  isCollapsed: boolean;
  messages: EditorChatMessage[];
  isStreaming: boolean;
  isEditOpsLoading: boolean;
  editOpsIsSlow?: boolean;
  editOpsError?: string | null;
  editOpsDisabledMessage?: string | null;
  clearDraftToken?: number;
  disabledMessage: string | null;
  error: string | null;
  noticeMessage?: string | null;
  noticeVariant?: Extract<SystemMessageVariant, "info" | "warning">;
  remoteFallbackPrompt?: RemoteFallbackPrompt | null;
};

const props = withDefaults(defineProps<ChatDrawerProps>(), {
  variant: "drawer",
  editOpsIsSlow: false,
  editOpsError: null,
  editOpsDisabledMessage: null,
  clearDraftToken: 0,
  noticeMessage: null,
  noticeVariant: "info",
  remoteFallbackPrompt: null,
});

const emit = defineEmits<{
  (event: "close"): void;
  (event: "send", message: string): void;
  (event: "cancel"): void;
  (event: "clear"): void;
  (event: "clearError"): void;
  (event: "clearDisabled"): void;
  (event: "clearNotice"): void;
  (event: "clearEditOpsError"): void;
  (event: "clearEditOpsDisabled"): void;
  (event: "toggleCollapse"): void;
  (event: "requestEditOps", message: string): void;
  (event: "allowRemoteFallbackPrompt"): void;
  (event: "denyRemoteFallbackPrompt"): void;
  (event: "dismissRemoteFallbackPrompt"): void;
}>();

const isColumnVariant = computed(() => props.variant === "column");
const isRailOnlyOnMobile = computed(() => isColumnVariant.value && props.isCollapsed);

const hasStatusPanel = computed(
  () =>
    Boolean(props.error) ||
    Boolean(props.disabledMessage) ||
    Boolean(props.noticeMessage) ||
    Boolean(props.editOpsError) ||
    Boolean(props.editOpsDisabledMessage) ||
    Boolean(props.remoteFallbackPrompt),
);

const assistantActivity = computed(() => {
  if (!props.isStreaming) {
    return null;
  }

  for (let index = props.messages.length - 1; index >= 0; index -= 1) {
    const message = props.messages[index];
    if (message.role !== "assistant") continue;
    if (!message.isStreaming) continue;

    const visible =
      message.reveal === "type" ? (message.visibleContent ?? "") : (message.content ?? "");
    return visible.length > 0 ? "writing" : "thinking";
  }

  return "thinking";
});
</script>

<template>
  <Teleport
    v-if="!isColumnVariant"
    to="body"
  >
    <Transition name="drawer-backdrop">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-40 bg-navy/40 lg:hidden"
        @click="emit('close')"
      />
    </Transition>
  </Teleport>

  <aside
    :class="[
      'fixed inset-y-0 right-0 z-50 bg-canvas border-l border-navy shadow-brutal flex flex-col lg:relative lg:inset-auto lg:z-auto lg:h-full lg:overflow-hidden',
      isRailOnlyOnMobile ? 'w-[var(--chat-rail-width,64px)]' : 'w-full',
      props.variant === 'column' ? 'lg:border-0 lg:shadow-none lg:bg-transparent' : '',
    ]"
    role="dialog"
    aria-modal="true"
    aria-labelledby="chat-drawer-title"
  >
    <div
      class="chat-shell"
      :class="{ 'chat-shell--collapsed': props.isCollapsed }"
    >
      <div
        class="chat-body"
        :class="{ 'chat-body--collapsed': props.isCollapsed }"
        :aria-hidden="props.isCollapsed"
        :inert="props.isCollapsed"
      >
        <div class="p-3 pr-10 border-b border-navy/30">
          <h2
            id="chat-drawer-title"
            class="text-lg font-semibold text-navy"
          >
            Kodassistenten
          </h2>
        </div>

        <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
          <div
            v-if="hasStatusPanel"
            class="shrink-0 border-b border-navy/20 px-3 py-2 space-y-2"
          >
            <SystemMessage
              v-if="props.noticeMessage"
              :model-value="props.noticeMessage"
              :variant="props.noticeVariant"
              @update:model-value="emit('clearNotice')"
            />
            <SystemMessage
              v-if="error"
              :model-value="error"
              variant="error"
              @update:model-value="emit('clearError')"
            />
            <SystemMessage
              v-if="disabledMessage"
              :model-value="disabledMessage"
              variant="warning"
              @update:model-value="emit('clearDisabled')"
            />
            <SystemMessage
              v-if="props.editOpsError"
              :model-value="props.editOpsError"
              variant="error"
              @update:model-value="emit('clearEditOpsError')"
            />
            <SystemMessage
              v-if="props.editOpsDisabledMessage"
              :model-value="props.editOpsDisabledMessage"
              variant="warning"
              @update:model-value="emit('clearEditOpsDisabled')"
            />

            <div
              v-if="props.remoteFallbackPrompt"
              class="border border-navy/20 bg-canvas px-3 py-3"
              data-editor-remote-fallback-prompt
            >
              <div class="flex items-start justify-between gap-3">
                <div class="space-y-1 min-w-0">
                  <p class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                    Externa AI-API:er
                  </p>
                  <p class="text-sm text-navy">
                    {{ props.remoteFallbackPrompt.message }}
                  </p>
                  <RouterLink
                    to="/profile"
                    class="text-xs text-navy/70 underline decoration-navy/40 hover:text-navy"
                  >
                    Öppna Profil och ändra inställningen
                  </RouterLink>
                </div>
                <button
                  type="button"
                  class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-white leading-none"
                  aria-label="Stäng"
                  @click="emit('dismissRemoteFallbackPrompt')"
                >
                  ×
                </button>
              </div>

              <div class="flex flex-wrap items-center gap-2 pt-3">
                <button
                  type="button"
                  class="btn-primary shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 leading-none"
                  :disabled="props.isStreaming || props.isEditOpsLoading"
                  @click="emit('allowRemoteFallbackPrompt')"
                >
                  Aktivera
                </button>
                <button
                  type="button"
                  class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-white leading-none"
                  :disabled="props.isStreaming || props.isEditOpsLoading"
                  @click="emit('denyRemoteFallbackPrompt')"
                >
                  Stäng av
                </button>
              </div>
            </div>
          </div>

          <div class="flex-1 min-h-0 overflow-y-auto px-3 py-2">
            <ChatMessageList :messages="props.messages" />
          </div>

          <div class="shrink-0 border-t border-navy/20 px-3 py-3">
            <ChatComposer
              :is-streaming="props.isStreaming"
              :is-edit-ops-loading="props.isEditOpsLoading"
              :assistant-activity="assistantActivity"
              :can-clear="props.messages.length > 0"
              :edit-ops-is-slow="props.editOpsIsSlow"
              :clear-draft-token="props.clearDraftToken"
              @send="emit('send', $event)"
              @clear="emit('clear')"
              @cancel="emit('cancel')"
              @request-edit-ops="emit('requestEditOps', $event)"
            />
          </div>
        </div>
      </div>

      <div class="chat-rail">
        <button
          type="button"
          class="inline-flex items-center justify-center h-8 w-8 text-navy/70 hover:text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy/40"
          :aria-label="props.isCollapsed ? 'Expandera kodassistenten' : 'Minimera kodassistenten'"
          @click="emit('toggleCollapse')"
        >
          <svg
            viewBox="0 0 24 24"
            class="h-5 w-5"
            aria-hidden="true"
          >
            <rect
              x="5"
              y="7"
              width="14"
              height="10"
              rx="2"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
            />
            <circle
              cx="9"
              cy="12"
              r="1"
              fill="currentColor"
            />
            <circle
              cx="15"
              cy="12"
              r="1"
              fill="currentColor"
            />
            <path
              d="M9 16h6"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
            <path
              d="M8 5h8"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.chat-shell {
  position: relative;
  display: flex;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.chat-body {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  transition: transform 120ms var(--huleedu-ease-default),
    filter 120ms var(--huleedu-ease-default),
    opacity 110ms var(--huleedu-ease-default);
  will-change: transform, filter, opacity;
  transform-origin: right center;
}

.chat-body--collapsed {
  opacity: 0.22;
  filter: blur(4px);
  transform: translateX(12px);
  pointer-events: none;
}

.chat-rail {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 2;
}

.chat-shell--collapsed .chat-rail {
  position: static;
  flex: 0 0 var(--chat-rail-width, 64px);
  height: 100%;
  padding-top: 12px;
}

.drawer-backdrop-enter-active,
.drawer-backdrop-leave-active {
  transition: opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to {
  opacity: 0;
}
</style>
