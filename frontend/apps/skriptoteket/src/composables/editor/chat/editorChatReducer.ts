import { reactive } from "vue";

import type {
  ChatTurnStatus,
  EditorChatHistoryMessage,
  EditorChatMessage,
} from "./editorChatTypes";

type EnsureAssistantMessageParams = {
  messages: EditorChatMessage[];
  activeAssistantMessage: EditorChatMessage | null;
  correlationId: string;
  messageId?: string | null;
  turnId?: string | null;
};

type EnsureAssistantMessageResult = {
  messages: EditorChatMessage[];
  activeAssistantMessage: EditorChatMessage;
};

type FinalizeTurnParams = {
  messages: EditorChatMessage[];
  userMessage: EditorChatMessage;
  activeAssistantMessage: EditorChatMessage | null;
  status: ChatTurnStatus;
  failureOutcome?: string | null;
};

export function createLocalMessageId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `chat-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function mapHistoryMessage(message: EditorChatHistoryMessage): EditorChatMessage {
  return reactive<EditorChatMessage>({
    id: message.message_id,
    turnId: message.turn_id,
    role: message.role,
    content: message.content,
    createdAt: message.created_at,
    isStreaming: false,
    correlationId: message.correlation_id ?? null,
    status: message.status,
    failureOutcome: message.failure_outcome ?? null,
    reveal: "instant",
  });
}

export function createUserMessage(content: string): EditorChatMessage {
  return reactive<EditorChatMessage>({
    id: createLocalMessageId(),
    role: "user",
    content,
    createdAt: new Date().toISOString(),
    correlationId: null,
    turnId: null,
    status: "pending",
    failureOutcome: null,
    reveal: "instant",
  });
}

export function appendMessage(
  messages: EditorChatMessage[],
  message: EditorChatMessage,
): EditorChatMessage[] {
  return [...messages, message];
}

export function ensureAssistantMessage({
  messages,
  activeAssistantMessage,
  correlationId,
  messageId,
  turnId,
}: EnsureAssistantMessageParams): EnsureAssistantMessageResult {
  if (activeAssistantMessage) {
    if (correlationId) {
      activeAssistantMessage.correlationId = correlationId;
    }
    if (turnId) {
      activeAssistantMessage.turnId = turnId;
    }
    return { messages, activeAssistantMessage };
  }

  const assistantMessage = reactive<EditorChatMessage>({
    id: messageId || createLocalMessageId(),
    role: "assistant",
    content: "",
    visibleContent: "",
    createdAt: new Date().toISOString(),
    isStreaming: true,
    correlationId,
    turnId: turnId ?? null,
    status: "pending",
    failureOutcome: null,
    reveal: "type",
  });

  return {
    messages: [...messages, assistantMessage],
    activeAssistantMessage: assistantMessage,
  };
}

export function finalizeAssistant(activeAssistantMessage: EditorChatMessage | null): void {
  if (activeAssistantMessage) {
    activeAssistantMessage.isStreaming = false;
  }
}

export function finalizeTurn({
  messages,
  userMessage,
  activeAssistantMessage,
  status,
  failureOutcome,
}: FinalizeTurnParams): void {
  const turnId = activeAssistantMessage?.turnId ?? userMessage.turnId;
  if (turnId) {
    for (const item of messages) {
      if (item.turnId === turnId) {
        item.status = status;
        if (failureOutcome) {
          item.failureOutcome = failureOutcome;
        }
      }
    }
    userMessage.status = status;
    if (failureOutcome) {
      userMessage.failureOutcome = failureOutcome;
    }
    return;
  }

  userMessage.status = status;
  if (failureOutcome) {
    userMessage.failureOutcome = failureOutcome;
  }
  if (activeAssistantMessage) {
    activeAssistantMessage.status = status;
    if (failureOutcome) {
      activeAssistantMessage.failureOutcome = failureOutcome;
    }
  }
}
