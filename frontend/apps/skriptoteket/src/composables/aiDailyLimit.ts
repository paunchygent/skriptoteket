/**
 * Daily AI limit shared by the exam workspace and the script editor.
 *
 * Domain purpose:
 *   The HuleEdu LLM door refuses AI work once the daily pool, user share or
 *   cost ceiling is spent. The backend reports this on every AI status shape
 *   (`ai_limit`) and on the one-question retry (HTTP 429
 *   AI_DAILY_LIMIT_REACHED). The frontend then disables that AI control for
 *   the page session and shows the door's own note inline next to it, with
 *   no toast: a reload clears the flag and the door refuses again without an
 *   OpenAI call. The first limit seen wins: the note names the user's own
 *   share, or the app's pool/ceiling.
 *
 * Relationships:
 *   - Marked by the exam-workspace AI composables (enrichment, content
 *     suggestions, conversion, item retry); read by the components that own
 *     an AI button (header, export blockers, details drawer, open drawer,
 *     import box).
 *   - The script editor shares the same page-session flag, because it is the
 *     same door and the same teacher: ghost text, chat and edit-ops mark it
 *     on a 429 (`skriptoteketGhostText`, `useEditorChatRequest`,
 *     `useEditorEditOps`); `ScriptEditorAiPanel` shows the note beside the
 *     disabled composer and `EditorSourceCodePanel` shows it inline over the
 *     editor.
 */

import { computed, readonly, ref } from "vue";
import type { ComputedRef, Ref } from "vue";

import { isApiError } from "../api/client";

/** The door's own note for the teacher's personal share. */
export const AI_USER_LIMIT_NOTE =
  "Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon.";

/** The door's own note for the shared pool and cost ceiling. */
export const AI_APP_LIMIT_NOTE =
  "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon.";

/** The note the door shows for one of its limits. */
export function aiLimitNote(limit: AiDailyLimit): string {
  return limit === "user_share" ? AI_USER_LIMIT_NOTE : AI_APP_LIMIT_NOTE;
}

/** The three limits the door reports, mirroring the backend `AiDailyLimit`. */
export type AiDailyLimit = "pool" | "user_share" | "usd_ceiling";

function isAiDailyLimit(value: unknown): value is AiDailyLimit {
  return value === "pool" || value === "user_share" || value === "usd_ceiling";
}

/** A status shape carrying the door's limit, or a nullish non-status. */
type AiLimitStatus = {
  readonly ai_limit?: AiDailyLimit | null;
} | null | undefined;

/** True when the status names one of the three door limits. */
export function hasAiDailyLimit(status: AiLimitStatus): boolean {
  return aiLimitFromStatus(status) !== null;
}

/** The door limit a status names, or null when it names none. */
export function aiLimitFromStatus(status: AiLimitStatus): AiDailyLimit | null {
  const limit = status?.ai_limit;
  return isAiDailyLimit(limit) ? limit : null;
}

/** True when the failure is the door's daily-limit refusal of the retry. */
export function isAiDailyLimitError(error: unknown): boolean {
  return aiLimitFromError(error) !== null;
}

/**
 * The door limit a 429 refusal names in `details.limit`, or null when the
 * failure is not the door's daily-limit refusal naming one of the three limits.
 */
export function aiLimitFromError(error: unknown): AiDailyLimit | null {
  if (!isApiError(error) || error.code !== "AI_DAILY_LIMIT_REACHED") {
    return null;
  }
  const details: unknown = error.details;
  if (typeof details !== "object" || details === null || !("limit" in details)) {
    return null;
  }
  return isAiDailyLimit(details.limit) ? details.limit : null;
}

/**
 * The door's own busy sentence when a 429 refusal is AI_TRY_AGAIN, or null for
 * any other failure. Unlike a daily limit, the refusal clears at once: callers
 * show the sentence inline and keep the AI control enabled so the teacher can
 * retry immediately.
 */
export function aiTryAgainFromError(error: unknown): string | null {
  if (!isApiError(error) || error.code !== "AI_TRY_AGAIN") {
    return null;
  }
  return error.message;
}

/**
 * The first door limit refused in this page session, or null while no AI
 * action has been refused. Module state on purpose: it lives exactly as long
 * as the page, and a reload clears it.
 */
const reachedLimit = ref<AiDailyLimit | null>(null);

/** Read-only view of the first limit refused this page session. */
export const aiDailyLimit: Readonly<Ref<AiDailyLimit | null>> = readonly(reachedLimit);

/** Whether the door refused an AI action in this page session. */
export const aiDailyLimitReached: ComputedRef<boolean> = computed(
  () => reachedLimit.value !== null,
);

/** The door's note for the refused limit, or null while nothing is refused. */
export const aiDailyLimitNote: ComputedRef<string | null> = computed(() =>
  reachedLimit.value === null ? null : aiLimitNote(reachedLimit.value),
);

/**
 * Remember the door's refusal for the rest of the page session. The first
 * limit seen wins; later refusals keep the first note.
 */
export function markAiDailyLimit(limit: AiDailyLimit): void {
  if (reachedLimit.value !== null) {
    return;
  }
  reachedLimit.value = limit;
}

/** Clear the flag; tests only, so one spec's limit never leaks into the next. */
export function resetAiDailyLimitForTests(): void {
  reachedLimit.value = null;
}
