<script setup lang="ts">
import type { EditorView } from "@codemirror/view";
import { computed, ref, toRef, watch, type Ref } from "vue";

import { useEditorChat } from "../../composables/editor/useEditorChat";
import { useEditorEditOps } from "../../composables/editor/useEditorEditOps";
import { createLocalMessageId, appendMessage } from "../../composables/editor/chat/editorChatReducer";
import type { EditorChatMessage } from "../../composables/editor/chat/editorChatTypes";
import type { VirtualFileId } from "../../composables/editor/virtualFiles";
import { virtualFileTextFromEditorFields } from "../../composables/editor/virtualFiles";
import { useToast } from "../../composables/useToast";

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
  allowRemoteFallback: boolean;
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
const allowRemoteFallback = toRef(props, "allowRemoteFallback");
const isReadOnly = toRef(props, "isReadOnly");
const editorView = toRef(props, "editorView");
const compareActiveFileId = toRef(props, "compareActiveFileId");
const isChatDrawerOpen = toRef(props, "isChatDrawerOpen");
const toast = useToast();

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

const editOpsDisabledMessage = ref<string | null>(null);
const editOpsClearDraftToken = ref(0);
const slotBindings = computed(() => ({
  chatMessages: editorChat.messages.value,
  chatStreaming: editorChat.streaming.value,
  chatDisabledMessage: editorChat.disabledMessage.value,
  chatError: editorChat.error.value,
  chatNoticeMessage: editorChat.noticeMessage.value,
  chatNoticeVariant: editorChat.noticeVariant.value,
  sendChatMessage: editorChat.sendMessage,
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
  editOpsDisabledMessage.value = null;
  const result = await editOps.requestEditOps(message);
  if (!result) return;

  if (!result.response.enabled) {
    editOpsDisabledMessage.value = result.response.assistant_message
      ? `AI-redigering: ${result.response.assistant_message}`
      : "AI-redigering är inte tillgänglig.";
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
