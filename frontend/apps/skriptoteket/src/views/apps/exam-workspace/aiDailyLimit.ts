/**
 * Exam workspace daily AI limit.
 *
 * Domain purpose:
 *   The HuleEdu LLM door refuses AI work once the daily pool, user share or
 *   cost ceiling is spent. The backend reports this on every AI status shape
 *   (`ai_limit`) and on the one-question retry (HTTP 429
 *   AI_DAILY_LIMIT_REACHED). The frontend then disables that AI control for
 *   the page session and shows the door's own note inline next to it, with
 *   no toast: a reload clears the flag and the door refuses again without an
 *   OpenAI call.
 *
 * Relationships:
 *   - Marked by the exam-workspace AI composables (enrichment, content
 *     suggestions, conversion, item retry); read by the components that own
 *     an AI button (header, export blockers, details drawer, open drawer,
 *     import box).
 */

import { readonly, ref } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";

/** The door's own refusal note; every AI control shows exactly this text. */
export const AI_DAILY_LIMIT_NOTE =
  "Du har nått dagens gräns för AI-hjälp. Försök igen i morgon.";

/** The three limits the door reports, mirroring the backend `AiDailyLimit`. */
export type AiDailyLimit = "pool" | "user_share" | "usd_ceiling";

/** A status shape carrying the door's limit, or a nullish non-status. */
type AiLimitStatus = {
  readonly ai_limit?: AiDailyLimit | null;
} | null | undefined;

/** True when the status names one of the three door limits. */
export function hasAiDailyLimit(status: AiLimitStatus): boolean {
  const limit = status?.ai_limit;
  return limit === "pool" || limit === "user_share" || limit === "usd_ceiling";
}

/** True when the failure is the door's daily-limit refusal of the retry. */
export function isAiDailyLimitError(error: unknown): boolean {
  return isApiError(error) && error.code === "AI_DAILY_LIMIT_REACHED";
}

/**
 * Whether the door refused an AI action in this page session. Module state
 * on purpose: it lives exactly as long as the page, and a reload clears it.
 */
const reached = ref(false);

/** Read-only view of the page-session limit flag for AI controls. */
export const aiDailyLimitReached: Ref<boolean> = readonly(reached);

/** Remember the door's refusal for the rest of the page session. */
export function markAiDailyLimit(): void {
  reached.value = true;
}

/** Clear the flag; tests only, so one spec's limit never leaks into the next. */
export function resetAiDailyLimitForTests(): void {
  reached.value = false;
}
