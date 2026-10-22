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
 * Allowances:
 *   The door counts the pool and each caller's share per allowance: the
 *   small-model allowance (inline completion and all exam-workspace AI) and
 *   the full-model allowance (editor chat and edit-ops). A refusal is
 *   remembered under the allowance that made the request and disables only
 *   that allowance's controls. The cost ceiling is service-wide and disables
 *   both.
 *
 * Relationships:
 *   - Marked under `small` by the exam-workspace AI composables (enrichment,
 *     content suggestions, conversion, item retry) and by ghost text
 *     (`skriptoteketGhostText`); read by the components that own an exam AI
 *     button (header, export blockers, details drawer, open drawer, import
 *     box).
 *   - Marked under `full` by `useEditorChatRequest` and `useEditorEditOps`;
 *     `ScriptEditorAiPanel` shows the note beside the disabled composer for
 *     the full allowance, and `EditorSourceCodePanel` shows the small
 *     allowance's note inline over the editor.
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
 * The door's two separate allowances. `pool` and `user_share` limits count per
 * allowance; `usd_ceiling` is service-wide.
 *
 * - `small`: the small-model allowance, used by inline completion and every
 *   exam-workspace AI action.
 * - `full`: the full-model allowance, used by editor chat and edit-ops.
 */
export type AiAllowance = "small" | "full";

const allAllowances: readonly AiAllowance[] = ["small", "full"];

/** What one allowance has seen refused in this page session. */
export type AiAllowanceState = {
  /** The first limit this allowance was refused with, or null. */
  readonly limit: Readonly<Ref<AiDailyLimit | null>>;
  /** Whether the AI controls of this allowance are disabled. */
  readonly reached: ComputedRef<boolean>;
  /** The door's note for the refused limit, or null while nothing is refused. */
  readonly note: ComputedRef<string | null>;
};

/**
 * The first door limit refused per allowance in this page session. Module
 * state on purpose: it lives exactly as long as the page, and a reload clears
 * it.
 */
const reachedLimits: Record<AiAllowance, Ref<AiDailyLimit | null>> = {
  small: ref(null),
  full: ref(null),
};

function allowanceState(allowance: AiAllowance): AiAllowanceState {
  const limit = reachedLimits[allowance];
  return {
    limit: readonly(limit),
    reached: computed(() => limit.value !== null),
    note: computed(() => (limit.value === null ? null : aiLimitNote(limit.value))),
  };
}

const allowanceStates: Record<AiAllowance, AiAllowanceState> = {
  small: allowanceState("small"),
  full: allowanceState("full"),
};

/** Read-only refusal state of one allowance; each AI control reads its own. */
export function aiDailyLimitFor(allowance: AiAllowance): AiAllowanceState {
  return allowanceStates[allowance];
}

/**
 * Remember the door's refusal for the rest of the page session under the
 * allowance that made the request. The first limit per allowance wins; later
 * refusals keep the first note. The service-wide `usd_ceiling` blocks both
 * allowances.
 */
export function markAiDailyLimit(allowance: AiAllowance, limit: AiDailyLimit): void {
  const refused = limit === "usd_ceiling" ? allAllowances : [allowance];
  for (const target of refused) {
    if (reachedLimits[target].value === null) {
      reachedLimits[target].value = limit;
    }
  }
}

/** Clear the flags; tests only, so one spec's limit never leaks into the next. */
export function resetAiDailyLimitForTests(): void {
  for (const allowance of allAllowances) {
    reachedLimits[allowance].value = null;
  }
}
