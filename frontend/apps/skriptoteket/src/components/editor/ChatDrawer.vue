<script setup lang="ts">
import { computed, ref, withDefaults } from "vue";

import type { EditorChatMessage } from "../../composables/editor/useEditorChat";
import SystemMessage from "../ui/SystemMessage.vue";

type ChatDrawerProps = {
  variant?: "drawer" | "column";
  isOpen: boolean;
  isCollapsed: boolean;
  messages: EditorChatMessage[];
  isStreaming: boolean;
  disabledMessage: string | null;
  error: string | null;
};

const props = withDefaults(defineProps<ChatDrawerProps>(), {
  variant: "drawer",
});

const emit = defineEmits<{
  (event: "close"): void;
  (event: "send", message: string): void;
  (event: "cancel"): void;
  (event: "clear"): void;
  (event: "clearError"): void;
  (event: "clearDisabled"): void;
  (event: "toggleCollapse"): void;
}>();

const draft = ref("");

const canSend = computed(() => !props.isStreaming && draft.value.trim().length > 0);

function handleSend(): void {
  const message = draft.value.trim();
  if (!message || props.isStreaming) {
    return;
  }
  emit("send", message);
  draft.value = "";
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    handleSend();
  }
}

function labelForRole(role: "user" | "assistant"): string {
  return role === "user" ? "Du" : "AI";
}
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer-backdrop">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-40 bg-navy/40 md:hidden"
        @click="emit('close')"
      />
    </Transition>
  </Teleport>

  <aside
    :class="[
      'fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy shadow-brutal flex flex-col md:relative md:inset-auto md:z-auto md:h-full md:overflow-hidden',
      props.variant === 'column' ? 'md:border-0 md:shadow-none md:bg-transparent' : '',
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
        :inert="props.isCollapsed ? '' : undefined"
      >
        <div class="p-3 pr-10 border-b border-navy/30">
          <h2
            id="chat-drawer-title"
            class="text-lg font-semibold text-navy"
          >
            Kodassistenten
          </h2>
          <p class="text-sm text-navy/70">
            Beskriv ditt m&aring;l eller problem f&ouml;r kodassistenten s&aring; hj&auml;lper den dig.
            H&aring;ll konversationerna korta f&ouml;r b&auml;sta kvalitet.
          </p>
        </div>

        <div class="flex-1 min-h-0 overflow-hidden p-4 flex flex-col gap-4">
          <div class="space-y-2">
            <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">
              Konversation
            </span>
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
          </div>

          <div class="flex-1 min-h-0 overflow-y-auto border-t border-navy/20 pt-4">
            <p
              v-if="messages.length === 0"
              class="text-sm text-navy/60"
            >
              Ingen chatthistorik &auml;nnu. Skriv ett f&ouml;rsta meddelande nedan.
            </p>

            <ul
              v-else
              class="divide-y divide-navy/10"
            >
              <li
                v-for="message in messages"
                :key="message.id"
                :class="[
                  'py-3 pl-3',
                  message.role === 'user'
                    ? 'border-l-2 border-burgundy/60'
                    : 'border-l-2 border-navy/30',
                ]"
              >
                <div class="flex items-center justify-between">
                  <span class="text-xs font-semibold uppercase tracking-wide text-navy/60">
                    {{ labelForRole(message.role) }}
                  </span>
                  <span
                    v-if="message.isStreaming"
                    class="text-xs text-navy/60"
                  >
                    Skriver...
                  </span>
                </div>
                <div class="mt-2 text-sm text-navy whitespace-pre-wrap">
                  {{ message.content }}
                </div>
              </li>
            </ul>
          </div>

          <div class="border-t border-navy/20 pt-4 space-y-3">
            <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
              Meddelande
            </label>
            <textarea
              v-model="draft"
              rows="4"
              class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
              placeholder="Beskriv ditt m&aring;l eller problem..."
              :disabled="isStreaming"
              @keydown="handleKeydown"
            />

            <div class="flex flex-wrap items-center justify-between gap-2">
              <span
                v-if="isStreaming"
                class="text-xs text-navy/60"
              >
                AI skriver...
              </span>
              <span
                v-else
                class="text-xs text-navy/60"
              >
                Enter skickar, Shift+Enter ny rad.
              </span>
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
                  :disabled="messages.length === 0"
                  @click="emit('clear')"
                >
                  Rensa
                </button>
                <button
                  v-if="isStreaming"
                  type="button"
                  class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
                  @click="emit('cancel')"
                >
                  Avbryt
                </button>
                <button
                  type="button"
                  class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
                  :disabled="!canSend"
                  @click="handleSend"
                >
                  Skicka
                </button>
              </div>
            </div>
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
