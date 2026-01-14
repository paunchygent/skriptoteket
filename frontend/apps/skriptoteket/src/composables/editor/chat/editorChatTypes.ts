import type { components } from "../../../api/openapi";

type EditorChatHistoryResponse = components["schemas"]["EditorChatHistoryResponse"];
type EditorChatHistoryMessage = components["schemas"]["EditorChatHistoryMessage"];
type EditorChatRequest = components["schemas"]["EditorChatRequest"];
type EditorVirtualFiles = components["schemas"]["EditorVirtualFiles"];

type VirtualFileId = keyof EditorVirtualFiles;

type ChatRole = "user" | "assistant";
type NoticeVariant = "info" | "warning";
type ChatTurnStatus = "pending" | "complete" | "failed" | "cancelled";
type ChatRevealMode = "instant" | "type";

type EditorChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  isStreaming?: boolean;
  correlationId?: string | null;
  turnId?: string | null;
  status?: ChatTurnStatus;
  failureOutcome?: string | null;
  reveal?: ChatRevealMode;
};

export type {
  ChatRole,
  ChatRevealMode,
  ChatTurnStatus,
  EditorChatHistoryMessage,
  EditorChatHistoryResponse,
  EditorChatMessage,
  EditorChatRequest,
  EditorVirtualFiles,
  NoticeVariant,
  VirtualFileId,
};
