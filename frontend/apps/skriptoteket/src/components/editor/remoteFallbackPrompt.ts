export type RemoteFallbackPromptSource = "chat" | "editOps";

export type RemoteFallbackPrompt = {
  source: RemoteFallbackPromptSource;
  message: string;
};
