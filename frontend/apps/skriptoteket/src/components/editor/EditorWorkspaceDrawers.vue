<script setup lang="ts">
import { defineAsyncComponent } from "vue";

import type { EditorChatMessage } from "../../composables/editor/chat/editorChatTypes";

const ChatDrawer = defineAsyncComponent(() => import("./ChatDrawer.vue"));

type EditorWorkspaceDrawersProps = {
  isChatDrawerOpen: boolean;
  isChatCollapsed: boolean;
  variant?: "drawer" | "column";

  chatMessages: EditorChatMessage[];
  chatIsStreaming: boolean;
  chatError: string | null;
  aiBlockedNote: string | null;
  isEditOpsLoading: boolean;
  isEditOpsSlow: boolean;

  editOpsError: string | null;
  editOpsDisabledMessage: string | null;
  editOpsClearDraftToken?: number;
};

const props = withDefaults(defineProps<EditorWorkspaceDrawersProps>(), {
  variant: "drawer",
  editOpsClearDraftToken: 0,
});

const emit = defineEmits<{
  (event: "close"): void;
  (event: "sendChatMessage", message: string): void;
  (event: "cancelChatStream"): void;
  (event: "clearChat"): void;
  (event: "clearChatError"): void;
  (event: "toggleChatCollapsed"): void;
  (event: "requestEditOps", message: string): void;
  (event: "clearEditOpsError"): void;
  (event: "clearEditOpsDisabled"): void;
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
    :error="props.chatError"
    :ai-blocked-note="props.aiBlockedNote"
    :is-edit-ops-loading="props.isEditOpsLoading"
    :edit-ops-is-slow="props.isEditOpsSlow"
    :edit-ops-error="props.editOpsError"
    :edit-ops-disabled-message="props.editOpsDisabledMessage"
    :clear-draft-token="props.editOpsClearDraftToken"
    @close="emit('close')"
    @toggle-collapse="emit('toggleChatCollapsed')"
    @send="emit('sendChatMessage', $event)"
    @cancel="emit('cancelChatStream')"
    @clear="emit('clearChat')"
    @clear-error="emit('clearChatError')"
    @clear-edit-ops-error="emit('clearEditOpsError')"
    @clear-edit-ops-disabled="emit('clearEditOpsDisabled')"
    @request-edit-ops="emit('requestEditOps', $event)"
  />
</template>
