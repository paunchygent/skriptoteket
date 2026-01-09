<script setup lang="ts">
import { withDefaults } from "vue";
import type { EditorChatMessage } from "../../composables/editor/useEditorChat";

import ChatDrawer from "./ChatDrawer.vue";

type EditorWorkspaceDrawersProps = {
  isChatDrawerOpen: boolean;
  isChatCollapsed: boolean;
  variant?: "drawer" | "column";

  chatMessages: EditorChatMessage[];
  chatIsStreaming: boolean;
  chatDisabledMessage: string | null;
  chatError: string | null;
};

const props = withDefaults(defineProps<EditorWorkspaceDrawersProps>(), {
  variant: "drawer",
});

const emit = defineEmits<{
  (event: "close"): void;
  (event: "sendChatMessage", message: string): void;
  (event: "cancelChatStream"): void;
  (event: "clearChat"): void;
  (event: "clearChatError"): void;
  (event: "clearChatDisabled"): void;
  (event: "toggleChatCollapsed"): void;
}>();
</script>

<template>
  <ChatDrawer
    v-if="props.isChatDrawerOpen"
    :variant="props.variant"
    :is-open="props.isChatDrawerOpen"
    :is-collapsed="props.isChatCollapsed"
    :messages="props.chatMessages"
    :is-streaming="props.chatIsStreaming"
    :disabled-message="props.chatDisabledMessage"
    :error="props.chatError"
    @close="emit('close')"
    @toggle-collapse="emit('toggleChatCollapsed')"
    @send="emit('sendChatMessage', $event)"
    @cancel="emit('cancelChatStream')"
    @clear="emit('clearChat')"
    @clear-error="emit('clearChatError')"
    @clear-disabled="emit('clearChatDisabled')"
  />
</template>
