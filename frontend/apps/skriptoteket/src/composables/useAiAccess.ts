import { computed, type ComputedRef } from "vue";

import { useAuthStore } from "../stores/auth";

/**
 * Temporary gate until the AI spend cap and rate limits ship (TASK-SKRIPT-REP-0044).
 * Carries no setting or flag.
 */
export const AI_ADMIN_ONLY_NOTE =
  "AI-funktionerna är tillfälligt bara tillgängliga för administratörer.";

export function useAiAccess(): { canUseAi: ComputedRef<boolean> } {
  const canUseAi = computed(() => useAuthStore().hasAtLeastRole("admin"));
  return { canUseAi };
}
