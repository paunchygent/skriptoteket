/**
 * Planner session controller.
 *
 * Purpose:
 *   Own the active planner session identity and async invalidation tokens for
 *   Klassrumskartan. The controller is the single source of truth for the
 *   current draft/roster identity while persistence lanes keep only bound IDs
 *   for request guarding.
 *
 * Relationships:
 *   - composed by `useClassroomState.ts`
 *   - consulted by `useDraftPersistenceLane.ts` and
 *     `useRosterSmartRuleLane.ts` for late-response invalidation
 *   - used by `plannerTransitionPolicies.ts` to reason about teardown and
 *     session changes
 */

import { computed, ref } from "vue";

type PlannerSessionIdentity = {
  draftId: string | null;
  rosterId: string | null;
};

export function usePlannerSessionController() {
  const activeDraftId = ref<string | null>(null);
  const activeRosterId = ref<string | null>(null);
  const transitionDepth = ref(0);
  const sessionToken = ref(0);

  let workspaceLoadRequestId = 0;

  const hasActiveSession = computed(() => {
    return activeDraftId.value !== null || activeRosterId.value !== null;
  });

  function beginWorkspaceTransition(): void {
    transitionDepth.value += 1;
  }

  function endWorkspaceTransition(): void {
    transitionDepth.value = Math.max(0, transitionDepth.value - 1);
  }

  function createWorkspaceLoadRequest(): number {
    workspaceLoadRequestId += 1;
    return workspaceLoadRequestId;
  }

  function isCurrentWorkspaceLoadRequest(requestId: number): boolean {
    return workspaceLoadRequestId === requestId;
  }

  function replaceSession(identity: PlannerSessionIdentity): void {
    sessionToken.value += 1;
    activeDraftId.value = identity.draftId;
    activeRosterId.value = identity.rosterId;
  }

  function invalidateAsyncState(): void {
    sessionToken.value += 1;
    workspaceLoadRequestId += 1;
  }

  function clearSession(): void {
    invalidateAsyncState();
    activeDraftId.value = null;
    activeRosterId.value = null;
    transitionDepth.value = 0;
  }

  return {
    activeDraftId,
    activeRosterId,
    transitionDepth,
    hasActiveSession,
    sessionToken,
    beginWorkspaceTransition,
    endWorkspaceTransition,
    createWorkspaceLoadRequest,
    isCurrentWorkspaceLoadRequest,
    replaceSession,
    invalidateAsyncState,
    clearSession,
  };
}
