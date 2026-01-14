<script setup lang="ts">
import type { EditorView } from "@codemirror/view";
import { computed, ref, toRef, watch, type Ref } from "vue";
import { storeToRefs } from "pinia";

import { useEditorChat } from "../../composables/editor/useEditorChat";
import { useEditorEditOps } from "../../composables/editor/useEditorEditOps";
import { createLocalMessageId, appendMessage } from "../../composables/editor/chat/editorChatReducer";
import type { EditorChatMessage } from "../../composables/editor/chat/editorChatTypes";
import type { VirtualFileId } from "../../composables/editor/virtualFiles";
import { virtualFileTextFromEditorFields } from "../../composables/editor/virtualFiles";
import { useToast } from "../../composables/useToast";
import { useAiStore } from "../../stores/ai";
import type { RemoteFallbackPrompt, RemoteFallbackPromptSource } from "./remoteFallbackPrompt";

type EditorFieldRefs = {
  entrypoint: Ref<string>;
  sourceCode: Ref<string>;
  settingsSchemaText: Ref<string>;
  inputSchemaText: Ref<string>;
  usageInstructions: Ref<string>;
};

type ScriptEditorAiPanelProps = {
  toolId: string;
  baseVersionId: string | null;
  isReadOnly: boolean;
  editorView: EditorView | null;
  compareActiveFileId: VirtualFileId | null;
  fields: EditorFieldRefs;
  createBeforeApplyCheckpoint: () => Promise<void> | void;
  isChatDrawerOpen: boolean;
};

const props = defineProps<ScriptEditorAiPanelProps>();
const emit = defineEmits<{
  (event: "proposalReady"): void;
}>();

const toolId = toRef(props, "toolId");
const baseVersionId = toRef(props, "baseVersionId");
const isReadOnly = toRef(props, "isReadOnly");
const editorView = toRef(props, "editorView");
const compareActiveFileId = toRef(props, "compareActiveFileId");
const isChatDrawerOpen = toRef(props, "isChatDrawerOpen");
const toast = useToast();
const ai = useAiStore();
const { allowRemoteFallback, remoteFallbackPreference } = storeToRefs(ai);

const REMOTE_FALLBACK_REQUIRED_CODE = "remote_fallback_required";
const REMOTE_FALLBACK_REQUIRED_TEXT_SNIPPET = "Aktivera externa AI-API:er (OpenAI)";

const chatVirtualFiles = computed(() => {
  if (!toolId.value) return null;
  return virtualFileTextFromEditorFields({
    entrypoint: props.fields.entrypoint.value,
    sourceCode: props.fields.sourceCode.value,
    settingsSchemaText: props.fields.settingsSchemaText.value,
    inputSchemaText: props.fields.inputSchemaText.value,
    usageInstructions: props.fields.usageInstructions.value,
  });
});

const chatActiveFileId = computed(() => compareActiveFileId.value ?? "tool.py");

const editorChat = useEditorChat({
  toolId,
  baseVersionId,
  allowRemoteFallback,
  activeFile: chatActiveFileId,
  virtualFiles: chatVirtualFiles,
});

const editOps = useEditorEditOps({
  toolId,
  allowRemoteFallback,
  isReadOnly,
  editorView,
  fields: props.fields,
  createBeforeApplyCheckpoint: props.createBeforeApplyCheckpoint,
});

type PendingRemoteFallback = {
  source: RemoteFallbackPromptSource;
  message: string;
  chatSnapshot?: EditorChatMessage[];
};

const editOpsDisabledMessage = ref<string | null>(null);
const editOpsClearDraftToken = ref(0);
const remoteFallbackPrompt = ref<RemoteFallbackPrompt | null>(null);
const pendingRemoteFallback = ref<PendingRemoteFallback | null>(null);

function clearRemoteFallbackPrompt(): void {
  remoteFallbackPrompt.value = null;
  pendingRemoteFallback.value = null;
}

watch(
  () => remoteFallbackPreference.value,
  (value) => {
    if (value !== "unset") {
      clearRemoteFallbackPrompt();
    }
  },
);

function latestAssistantFailureOutcome(): string | null {
  for (let index = editorChat.messages.value.length - 1; index >= 0; index -= 1) {
    const message = editorChat.messages.value[index];
    if (message.role !== "assistant") continue;
    return message.failureOutcome ?? null;
  }
  return null;
}

async function sendChatMessage(message: string): Promise<void> {
  if (remoteFallbackPrompt.value) {
    // If the user is mid-consent, treat new sends as a dismissal of the prior prompt.
    clearRemoteFallbackPrompt();
  }

  const snapshot = editorChat.messages.value.slice();
  await editorChat.sendMessage(message);

  if (remoteFallbackPreference.value !== "unset") {
    return;
  }

  if (latestAssistantFailureOutcome() !== REMOTE_FALLBACK_REQUIRED_CODE) {
    return;
  }

  const promptMessage = editorChat.disabledMessage.value ?? "";
  remoteFallbackPrompt.value = {
    source: "chat",
    message:
      promptMessage ||
      "Den lokala AI-modellen är inte tillgänglig. Aktivera externa AI-API:er (OpenAI) för att fortsätta.",
  };
  pendingRemoteFallback.value = { source: "chat", message, chatSnapshot: snapshot };
}

async function allowRemoteFallbackPrompt(): Promise<void> {
  const pending = pendingRemoteFallback.value;
  clearRemoteFallbackPrompt();

  ai.setRemoteFallbackPreference("allow");
  void ai.persistRemoteFallbackPreference("allow").catch((error: unknown) => {
    toast.failure(
      error instanceof Error
        ? error.message
        : "Kunde inte spara AI-inställningen. Du kan behöva välja igen.",
    );
  });

  if (!pending) return;

  if (pending.source === "chat") {
    if (pending.chatSnapshot) {
      editorChat.messages.value = pending.chatSnapshot;
    }
    editorChat.clearDisabledMessage();
    await editorChat.sendMessage(pending.message);
    return;
  }

  if (pending.source === "editOps") {
    await requestEditOps(pending.message);
  }
}

function denyRemoteFallbackPrompt(): void {
  ai.setRemoteFallbackPreference("deny");
  void ai.persistRemoteFallbackPreference("deny").catch((error: unknown) => {
    toast.failure(
      error instanceof Error
        ? error.message
        : "Kunde inte spara AI-inställningen. Du kan behöva välja igen.",
    );
  });
  clearRemoteFallbackPrompt();
}

function dismissRemoteFallbackPrompt(): void {
  clearRemoteFallbackPrompt();
}

const slotBindings = computed(() => ({
  chatMessages: editorChat.messages.value,
  chatStreaming: editorChat.streaming.value,
  chatDisabledMessage: editorChat.disabledMessage.value,
  chatError: editorChat.error.value,
  chatNoticeMessage: editorChat.noticeMessage.value,
  chatNoticeVariant: editorChat.noticeVariant.value,
  remoteFallbackPrompt: remoteFallbackPrompt.value,
  allowRemoteFallbackPrompt,
  denyRemoteFallbackPrompt,
  dismissRemoteFallbackPrompt,
  sendChatMessage,
  cancelChat: editorChat.cancel,
  clearChat: editorChat.clear,
  clearChatError: editorChat.clearError,
  clearChatDisabled: editorChat.clearDisabledMessage,
  clearChatNotice: editorChat.clearNoticeMessage,
  editOpsRequestError: editOps.requestError.value,
  editOpsDisabledMessage: editOpsDisabledMessage.value,
  editOpsClearDraftToken: editOpsClearDraftToken.value,
  editOpsState: editOps.panelState.value,
  isEditOpsRequesting: editOps.isRequesting.value,
  isEditOpsSlow: editOps.isSlowRequest.value,
  clearEditOpsRequestError: editOps.clearRequestError,
  clearEditOpsDisabledMessage,
  requestEditOps,
  setEditOpsConfirmationAccepted: editOps.setConfirmationAccepted,
  applyEditOps,
  discardEditOps: editOps.discardProposal,
  regenerateEditOps,
  undoEditOps,
  redoEditOps,
}));

watch(
  () => isChatDrawerOpen.value,
  (open) => {
    if (!open) return;
    void editorChat.loadHistory();
  },
  { immediate: true },
);

watch(
  () => toolId.value,
  (value, previous) => {
    if (!value || value === previous) return;
    if (!isChatDrawerOpen.value) return;
    void editorChat.loadHistory();
  },
);

watch(
  () => editOps.proposal.value,
  (value) => {
    if (value) {
      emit("proposalReady");
    }
  },
);

function appendChatMessage(
  role: "user" | "assistant",
  content: string,
  correlationId: string | null = null,
): void {
  const message: EditorChatMessage = {
    id: createLocalMessageId(),
    role,
    content,
    createdAt: new Date().toISOString(),
    isStreaming: false,
    correlationId,
  };
  editorChat.messages.value = appendMessage(editorChat.messages.value, message);
}

async function requestEditOps(message: string): Promise<void> {
  if (editorChat.streaming.value || editOps.isRequesting.value) return;
  if (remoteFallbackPrompt.value) {
    clearRemoteFallbackPrompt();
  }
  editOpsDisabledMessage.value = null;
  const result = await editOps.requestEditOps(message);
  if (!result) return;

  if (!result.response.enabled) {
    const assistantMessage = result.response.assistant_message?.trim() ?? "";
    editOpsDisabledMessage.value = result.response.assistant_message
      ? `AI-redigering: ${result.response.assistant_message}`
      : "AI-redigering är inte tillgänglig.";

    if (
      remoteFallbackPreference.value === "unset" &&
      assistantMessage.includes(REMOTE_FALLBACK_REQUIRED_TEXT_SNIPPET)
    ) {
      remoteFallbackPrompt.value = {
        source: "editOps",
        message: assistantMessage,
      };
      pendingRemoteFallback.value = { source: "editOps", message };
    }
    return;
  }

  appendChatMessage("user", result.message);
  appendChatMessage("assistant", result.response.assistant_message, result.correlationId);

  if (editOps.proposal.value && !editOps.previewError.value) {
    editOpsClearDraftToken.value += 1;
  }
}

async function applyEditOps(): Promise<void> {
  const applied = await editOps.applyProposal();
  if (applied) {
    toast.success("AI-förslaget är tillämpat.");
  }
}

function undoEditOps(): void {
  editOps.undoLastApply();
}

function redoEditOps(): void {
  editOps.redoLastApply();
}

async function regenerateEditOps(): Promise<void> {
  const message = editOps.proposal.value?.message;
  if (!message) return;
  await requestEditOps(message);
}

function clearEditOpsDisabledMessage(): void {
  editOpsDisabledMessage.value = null;
}
</script>

<template>
  <slot
    v-bind="slotBindings"
  />
</template>
