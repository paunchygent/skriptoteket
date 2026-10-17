import { getCurrentScope, onScopeDispose, watch, type Ref } from "vue";

import type { EditorChatMessage } from "./chat/editorChatTypes";

type RevealState = {
  lastTickMs: number;
  pendingCharBudget: number;
};

const REVEAL_CHARS_PER_SECOND = 90;
const REVEAL_MAX_CHUNK_SIZE = 18;
const REVEAL_INITIAL_BUDGET = 8;

/** Owns incremental message presentation and the animation-frame lifecycle. */
export function useEditorChatReveal(messages: Ref<EditorChatMessage[]>) {
  const revealStateByMessageId = new Map<string, RevealState>();
  let revealRafId: number | null = null;

  function stopRevealTick(): void {
    if (typeof window === "undefined") {
      return;
    }
    if (revealRafId === null) {
      return;
    }
    window.cancelAnimationFrame(revealRafId);
    revealRafId = null;
  }

  function hasPendingReveal(): boolean {
    for (const message of messages.value) {
      if (message.reveal !== "type") continue;
      if (message.visibleContent === undefined) {
        message.visibleContent = "";
      }
      if ((message.visibleContent ?? "").length < (message.content ?? "").length) {
        return true;
      }
    }
    return false;
  }

  function scheduleRevealTick(): void {
    if (typeof window === "undefined") {
      return;
    }
    if (revealRafId !== null) {
      return;
    }
    if (!hasPendingReveal()) {
      return;
    }
    revealRafId = window.requestAnimationFrame(tickReveal);
  }

  function tickReveal(now: number): void {
    revealRafId = null;
    let needsAnother = false;

    const liveIds = new Set(messages.value.map((message) => message.id));
    for (const id of revealStateByMessageId.keys()) {
      if (!liveIds.has(id)) {
        revealStateByMessageId.delete(id);
      }
    }

    for (const message of messages.value) {
      if (message.reveal !== "type") continue;

      const target = message.content ?? "";
      const current = message.visibleContent ?? "";
      if (!target) {
        if (message.visibleContent !== "") {
          message.visibleContent = "";
        }
        revealStateByMessageId.delete(message.id);
        continue;
      }

      if (!target.startsWith(current)) {
        message.visibleContent = "";
        revealStateByMessageId.delete(message.id);
        needsAnother = true;
        continue;
      }

      if (current.length >= target.length) {
        revealStateByMessageId.delete(message.id);
        continue;
      }

      const state = revealStateByMessageId.get(message.id) ?? {
        lastTickMs: now,
        pendingCharBudget: REVEAL_INITIAL_BUDGET,
      };

      const elapsedMs = Math.max(0, now - state.lastTickMs);
      state.lastTickMs = now;
      state.pendingCharBudget += (elapsedMs / 1000) * REVEAL_CHARS_PER_SECOND;

      let chunkSize = Math.floor(state.pendingCharBudget);
      if (chunkSize <= 0) {
        revealStateByMessageId.set(message.id, state);
        needsAnother = true;
        continue;
      }

      chunkSize = Math.min(chunkSize, REVEAL_MAX_CHUNK_SIZE);
      state.pendingCharBudget -= chunkSize;
      revealStateByMessageId.set(message.id, state);

      const start = current.length;
      const end = Math.min(target.length, start + chunkSize);
      message.visibleContent = target.slice(0, end);

      if (end < target.length) {
        needsAnother = true;
      }
    }

    if (needsAnother) {
      scheduleRevealTick();
    }
  }

  function resetReveal(): void {
    stopRevealTick();
    revealStateByMessageId.clear();
  }

  watch(
    () => messages.value.length,
    () => scheduleRevealTick(),
  );

  if (getCurrentScope()) {
    onScopeDispose(resetReveal);
  }

  return { scheduleRevealTick, resetReveal };
}
