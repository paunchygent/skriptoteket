/**
 * Public Smart grouping run orchestration.
 *
 * This composable keeps the browser-owned guest Smart grouping flow out of the
 * guest session assembly so the public lane can flush local state honestly,
 * call the dedicated public helper namespace, and then persist the accepted
 * solver result back into the browser snapshot.
 */

import { computed, ref, type Ref } from "vue";

import { apiPost } from "../../api/client";
import { normalizePublicSmartRunError } from "./classroomPlannerPublicSmartRunFeedback";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type {
  DraftWorkspaceResponse,
  PlanDraft,
  PublicSmartGroupingRunResponse,
} from "./classroomPlannerTypes";
import type { DraftPersistenceLaneResult } from "./useDraftPersistenceLane";
import type { RosterSmartRuleLaneResult } from "./useRosterSmartRuleLane";

type UsePublicSmartGroupingRunOptions = {
  apiPath: string;
  draft: Ref<PlanDraft | null>;
  smartRulesHydrated: Ref<boolean>;
  runningState: Ref<boolean>;
  flushDraftLane: () => Promise<DraftPersistenceLaneResult>;
  flushSmartRuleLane: () => Promise<RosterSmartRuleLaneResult>;
  getCurrentWorkspace: () => DraftWorkspaceResponse | null;
  commitWorkspaceToSnapshot: (
    workspace: DraftWorkspaceResponse,
  ) => Promise<ClassroomPlannerGuestSnapshot>;
  applyWorkspace: (workspace: DraftWorkspaceResponse) => void;
  normalizeErrorMessage: (error: unknown, fallbackMessage: string) => string;
};

type PublicSmartGroupingRunOutcome =
  | { status: "applied"; message: string | null }
  | { status: "blocked"; message: string };

const MISSING_DRAFT_MESSAGE = "Öppna en gruppindelning innan du använder Smart slumpa.";
const SMART_RULES_NOT_READY_MESSAGE = "Smarta regler kunde inte laddas än. Försök igen.";
const GENERIC_RUN_ERROR_MESSAGE = "Det gick inte att köra smart gruppindelning just nu.";

function resolveGroupingRevision(snapshot: ClassroomPlannerGuestSnapshot): number {
  if (!snapshot.grouping_draft) {
    throw new Error(MISSING_DRAFT_MESSAGE);
  }
  return snapshot.grouping_draft.revision;
}

export function usePublicSmartGroupingRun(options: UsePublicSmartGroupingRunOptions) {
  const message = ref<string | null>(null);
  const tone = ref<"neutral" | "success" | "warning">("neutral");

  const isBusy = computed(() => options.runningState.value);

  function clearFeedback(): void {
    message.value = null;
    tone.value = "neutral";
  }

  async function run(): Promise<PublicSmartGroupingRunOutcome> {
    const activeDraft = options.draft.value;
    if (!activeDraft) {
      message.value = MISSING_DRAFT_MESSAGE;
      tone.value = "warning";
      return { status: "blocked", message: MISSING_DRAFT_MESSAGE };
    }
    if (!options.smartRulesHydrated.value) {
      message.value = SMART_RULES_NOT_READY_MESSAGE;
      tone.value = "warning";
      return { status: "blocked", message: SMART_RULES_NOT_READY_MESSAGE };
    }

    options.runningState.value = true;
    clearFeedback();
    let previousWorkspace: DraftWorkspaceResponse | null = null;
    let appliedWorkspace = false;

    try {
      const smartRuleFlush = await options.flushSmartRuleLane();
      if (smartRuleFlush.status === "blocked") {
        message.value = smartRuleFlush.message;
        tone.value = "warning";
        return { status: "blocked", message: smartRuleFlush.message };
      }

      const draftFlush = await options.flushDraftLane();
      if (draftFlush.status === "blocked") {
        message.value = draftFlush.message;
        tone.value = "warning";
        return { status: "blocked", message: draftFlush.message };
      }

      const currentWorkspace = options.getCurrentWorkspace();
      if (!currentWorkspace) {
        message.value = MISSING_DRAFT_MESSAGE;
        tone.value = "warning";
        return { status: "blocked", message: MISSING_DRAFT_MESSAGE };
      }

      const snapshot = await options.commitWorkspaceToSnapshot(currentWorkspace);
      const result = await apiPost<PublicSmartGroupingRunResponse>(
        options.apiPath,
        {
          expected_revision: resolveGroupingRevision(snapshot),
          snapshot,
        },
      );
      if (result.status === "blocked") {
        message.value = result.message;
        tone.value = "warning";
        return { status: "blocked", message: result.message };
      }

      previousWorkspace = currentWorkspace;
      await options.commitWorkspaceToSnapshot(result.workspace);
      options.applyWorkspace(result.workspace);
      appliedWorkspace = true;

      message.value = result.message ?? null;
      tone.value = "success";
      return { status: "applied", message: result.message ?? null };
    } catch (error: unknown) {
      if (appliedWorkspace && previousWorkspace) {
        options.applyWorkspace(previousWorkspace);
      }
      const normalizedMessage = normalizePublicSmartRunError(
        error,
        GENERIC_RUN_ERROR_MESSAGE,
        options.normalizeErrorMessage,
      );
      message.value = normalizedMessage;
      tone.value = "warning";
      return { status: "blocked", message: normalizedMessage };
    } finally {
      options.runningState.value = false;
    }
  }

  return {
    isBusy,
    message,
    tone,
    clearFeedback,
    run,
  };
}
