<script setup lang="ts">
import { computed, ref } from "vue";

import type { EditorChatMessage } from "../../composables/editor/useEditorChat";
import SystemMessage from "../ui/SystemMessage.vue";

type ChatDrawerProps = {
  isOpen: boolean;
  messages: EditorChatMessage[];
  isStreaming: boolean;
  disabledMessage: string | null;
  error: string | null;
};

const props = defineProps<ChatDrawerProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "send", message: string): void;
  (event: "cancel"): void;
  (event: "clear"): void;
  (event: "clearError"): void;
  (event: "clearDisabled"): void;
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
    class="fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy shadow-brutal flex flex-col md:relative md:inset-auto md:z-auto md:w-full"
    role="dialog"
    aria-modal="true"
    aria-labelledby="chat-drawer-title"
  >
    <div class="p-6 border-b border-navy flex items-start justify-between gap-4">
      <div>
        <h2
          id="chat-drawer-title"
          class="text-lg font-semibold text-navy"
        >
          AI-chat
        </h2>
        <p class="text-sm text-navy/70">
          St&auml;ll fr&aring;gor om hur verktyget kan f&ouml;rb&auml;ttras.
        </p>
      </div>
      <button
        type="button"
        class="text-navy/60 hover:text-navy text-2xl leading-none"
        @click="emit('close')"
      >
        &times;
      </button>
    </div>

    <div class="flex-1 overflow-hidden p-6 flex flex-col gap-4">
      <div class="space-y-2">
        <span class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Konversation
        </span>
        <p class="text-sm text-navy/60">
          Skriv vad du vill f&ouml;rb&auml;ttra i verktyget.
        </p>
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
          placeholder="Beskriv vad du vill f&ouml;rb&auml;ttra..."
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
              class="btn-primary px-4"
              :disabled="!canSend"
              @click="handleSend"
            >
              Skicka
            </button>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.drawer-backdrop-enter-active,
.drawer-backdrop-leave-active {
  transition: opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to {
  opacity: 0;
}
</style>
