<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, withDefaults } from "vue";

import type { EditorChatMessage } from "../../composables/editor/useEditorChat";
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
  allowRemoteFallback: boolean;
};

const props = withDefaults(defineProps<ChatDrawerProps>(), {
  variant: "drawer",
  editOpsIsSlow: false,
  editOpsError: null,
  editOpsDisabledMessage: null,
  clearDraftToken: 0,
  noticeMessage: null,
  noticeVariant: "info",
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
  (event: "setAllowRemoteFallback", value: boolean): void;
}>();

const draft = ref("");
const textarea = ref<HTMLTextAreaElement | null>(null);
const debugOpenByMessageId = ref<Record<string, boolean>>({});

const canSend = computed(
  () => !props.isStreaming && !props.isEditOpsLoading && draft.value.trim().length > 0,
);
const canRequestOps = computed(() => canSend.value);
const isColumnVariant = computed(() => props.variant === "column");
const isRailOnlyOnMobile = computed(() => isColumnVariant.value && props.isCollapsed);

const displayMessages = computed(() => {
  if (props.messages.length > 0) {
    return props.messages;
  }
  return [
    {
      id: "assistant-intro",
      role: "assistant" as const,
      content: "Beskriv ditt mål eller problem för mig så hjälper jag dig",
      createdAt: "",
    },
  ] satisfies EditorChatMessage[];
});

function resetDraftTextarea(): void {
  const element = textarea.value;
  if (!element) {
    return;
  }
  element.style.height = "";
  element.style.overflowY = "";
}

function resizeDraftTextarea(): void {
  const element = textarea.value;
  if (!element) {
    return;
  }

  if (!draft.value) {
    resetDraftTextarea();
    return;
  }

  element.style.height = "auto";
  const maxHeightPx = 260;
  const nextHeight = Math.min(element.scrollHeight, maxHeightPx);
  element.style.height = `${nextHeight}px`;
  element.style.overflowY = element.scrollHeight > maxHeightPx ? "auto" : "hidden";
}

function handleSend(): void {
  const message = draft.value.trim();
  if (!message || props.isStreaming || props.isEditOpsLoading) {
    return;
  }
  emit("send", message);
  draft.value = "";
}

function handleRequestEditOps(): void {
  const message = draft.value.trim();
  if (!message || props.isStreaming || props.isEditOpsLoading) {
    return;
  }
  emit("requestEditOps", message);
}

function handleRemoteFallbackToggle(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  if (!target) return;
  emit("setAllowRemoteFallback", target.checked);
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

function toggleDebug(messageId: string): void {
  debugOpenByMessageId.value = {
    ...debugOpenByMessageId.value,
    [messageId]: !debugOpenByMessageId.value[messageId],
  };
}

function isDebugOpen(messageId: string): boolean {
  return Boolean(debugOpenByMessageId.value[messageId]);
}

async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    return;
  } catch {
    // fall back to the legacy clipboard API (best effort)
  }

  try {
    const element = document.createElement("textarea");
    element.value = text;
    element.setAttribute("readonly", "true");
    element.style.position = "absolute";
    element.style.left = "-9999px";
    document.body.appendChild(element);
    element.select();
    document.execCommand("copy");
    document.body.removeChild(element);
  } catch {
    // ignore clipboard failures
  }
}

onMounted(() => {
  resetDraftTextarea();
});

watch(
  () => draft.value,
  async () => {
    await nextTick();
    resizeDraftTextarea();
  },
  { flush: "post" },
);

watch(
  () => props.clearDraftToken,
  async () => {
    draft.value = "";
    await nextTick();
    resetDraftTextarea();
  },
);
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

        <div class="flex-1 min-h-0 overflow-hidden p-4 flex flex-col gap-4">
          <div
            v-if="
              error ||
                disabledMessage ||
                props.noticeMessage ||
                props.editOpsError ||
                props.editOpsDisabledMessage
            "
            class="space-y-2"
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
          </div>

          <div class="flex-1 min-h-0 overflow-y-auto border-t border-navy/20 pt-4 pr-3">
            <ul
              class="divide-y divide-navy/10"
            >
              <li
                v-for="message in displayMessages"
                :key="message.id"
                :class="[
                  'py-3 pl-3',
                  message.role === 'user'
                    ? 'border-l-2 border-burgundy/60'
                    : 'border-l-2 border-navy/30',
                ]"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold uppercase tracking-wide text-navy/60">
                      {{ labelForRole(message.role) }}
                    </span>
                    <span
                      v-if="message.correlationId"
                      class="relative inline-flex group"
                    >
                      <button
                        type="button"
                        class="text-[11px] font-mono leading-none text-navy/45 hover:text-navy/70"
                        :aria-expanded="isDebugOpen(message.id)"
                        aria-label="Visa correlation-id"
                        @click="toggleDebug(message.id)"
                      >
                        ...
                      </button>
                      <span
                        class="pointer-events-none absolute left-0 top-full z-10 mt-1 whitespace-nowrap border border-navy/30 bg-white px-2 py-1 text-[10px] text-navy/70 opacity-0 shadow-brutal-sm transition-opacity group-hover:opacity-100"
                        aria-hidden="true"
                      >
                        Visa correlation-id
                      </span>
                    </span>
                  </div>
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
                <div
                  v-if="message.correlationId && isDebugOpen(message.id)"
                  class="mt-2 flex flex-wrap items-center justify-between gap-2 border border-navy/20 bg-white px-2 py-1 text-[10px] text-navy/70"
                >
                  <span class="font-mono break-all">correlation-id: {{ message.correlationId }}</span>
                  <button
                    type="button"
                    class="text-[10px] font-semibold text-navy/60 hover:text-navy"
                    @click="copyText(message.correlationId)"
                  >
                    Kopiera
                  </button>
                </div>
              </li>
            </ul>
          </div>

          <div class="border-t border-navy/20 pt-4 space-y-3">
            <textarea
              ref="textarea"
              v-model="draft"
              rows="2"
              class="w-full resize-none border border-navy/30 bg-white px-3 py-2 text-sm text-navy shadow-none"
              placeholder="Beskriv ditt m&aring;l eller problem..."
              :disabled="isStreaming"
              @keydown="handleKeydown"
            />

            <label class="flex items-start gap-2 text-[10px] text-navy/70">
              <input
                type="checkbox"
                class="mt-0.5"
                :checked="props.allowRemoteFallback"
                :disabled="props.isStreaming || props.isEditOpsLoading"
                @change="handleRemoteFallbackToggle"
              >
              <span>
                Till&aring;t externa API:er (OpenAI) om den lokala modellen &auml;r nere eller
                &ouml;verbelastad. Detta kan skicka inneh&aring;ll utanf&ouml;r servern.
              </span>
            </label>

            <div class="flex flex-wrap items-center justify-between gap-2">
              <span
                v-if="isStreaming"
                class="text-xs text-navy/60"
              >
                AI skriver...
              </span>
              <span
                v-else-if="props.isEditOpsLoading"
                class="text-xs text-navy/60"
              >
                <span>Skapar f&ouml;rslag...</span>
                <span
                  v-if="props.editOpsIsSlow"
                  class="block pt-1 text-[10px] text-navy/50"
                >
                  Tar lite l&auml;ngre tid &auml;n vanligt. Lokala modeller kan ta upp till ~2 min.
                </span>
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
                  class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
                  :disabled="messages.length === 0"
                  @click="emit('clear')"
                >
                  Ny chatt
                </button>
                <button
                  type="button"
                  class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
                  :disabled="!canRequestOps"
                  @click="handleRequestEditOps"
                >
                  F&ouml;resl&aring; &auml;ndringar
                </button>
                <button
                  v-if="isStreaming"
                  type="button"
                  class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
                  @click="emit('cancel')"
                >
                  Avbryt
                </button>
                <button
                  type="button"
                  class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
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
