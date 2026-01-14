<script setup lang="ts">
import { computed, ref } from "vue";

import type { EditorChatMessage } from "../../composables/editor/chat/editorChatTypes";
import ChatMessageContent from "./ChatMessageContent.vue";

type ChatMessageListProps = {
  messages: EditorChatMessage[];
};

const props = defineProps<ChatMessageListProps>();

const debugOpenByMessageId = ref<Record<string, boolean>>({});

const displayMessages = computed(() => {
  if (props.messages.length > 0) {
    return props.messages;
  }
  return [
    {
      id: "assistant-intro",
      role: "assistant" as const,
      content: "Beskriv vad du vill ha hjälp med. När du är redo att ändra något väljer du \"Edit\".",
      createdAt: "",
    },
  ] satisfies EditorChatMessage[];
});

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
</script>

<template>
  <ul class="divide-y divide-navy/10">
    <li
      v-for="message in displayMessages"
      :key="message.id"
      :class="[
        'py-2 pl-3',
        message.role === 'user' ? 'border-l-2 border-burgundy/60' : 'border-l-2 border-navy/30',
      ]"
    >
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold uppercase tracking-wide text-navy/60">
            {{ labelForRole(message.role) }}
          </span>
          <span
            v-if="message.role === 'assistant' && message.status === 'failed'"
            class="text-[11px] font-semibold text-burgundy/70"
          >
            Misslyckades
          </span>
          <span
            v-else-if="message.role === 'assistant' && message.status === 'cancelled'"
            class="text-[11px] font-semibold text-navy/50"
          >
            Avbruten
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
        <template v-if="message.content">
          <ChatMessageContent
            :content="message.content"
            :reveal="message.reveal ?? 'instant'"
          />
        </template>
        <template v-else-if="message.role === 'assistant' && message.status === 'failed'">
          Misslyckades. Försök igen.
        </template>
        <template v-else-if="message.role === 'assistant' && message.status === 'cancelled'">
          Avbrutet.
        </template>
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
</template>
