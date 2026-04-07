/**
 * Classroom planner guest draft/session API assembly.
 *
 * This module keeps the guest session's flattened return contract out of the
 * main session controller so that file can stay focused on state wiring and
 * public/auth boundary behavior.
 */

type SessionApiGroup = Record<string, unknown>;

export function createClassroomPlannerGuestDraftSessionApi<
  TSessionState extends SessionApiGroup,
  TSmartRuleState extends SessionApiGroup,
  TWorkspaceActions extends SessionApiGroup,
  THistoryActions extends SessionApiGroup,
  TMutationActions extends SessionApiGroup,
>(input: {
  sessionState: TSessionState;
  smartRuleState: TSmartRuleState;
  workspaceActions: TWorkspaceActions;
  historyActions: THistoryActions;
  mutationActions: TMutationActions;
}): TSessionState
  & TSmartRuleState
  & TWorkspaceActions
  & THistoryActions
  & TMutationActions {
  return {
    ...input.sessionState,
    ...input.smartRuleState,
    ...input.workspaceActions,
    ...input.historyActions,
    ...input.mutationActions,
  };
}
