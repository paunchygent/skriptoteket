/**
 * Smart grouping run orchestration.
 *
 * This composable keeps the backend-owned smart grouping flow out of the main
 * planner store so the store stays focused on composing lanes and workspace
 * state. It flushes the draft lane and the roster smart-rule lane, then calls
 * the grouping smart-run endpoint only when the persisted state is honest.
 */

import { computed, ref, type Ref } from "vue";

import { apiPost } from "../../api/client";
import type {
  DraftWorkspaceResponse,
  PlanDraft,
  SmartGroupingRunResponse,
} from "./classroomPlannerTypes";
import type { DraftPersistenceLaneResult } from "./useDraftPersistenceLane";
import type { RosterSmartRuleLaneResult } from "./useRosterSmartRuleLane";

type UseSmartGroupingRunOptions = {
  draft: Ref<PlanDraft | null>;
  smartRulesHydrated: Ref<boolean>;
  runningState: Ref<boolean>;
  flushDraftLane: () => Promise<DraftPersistenceLaneResult>;
  flushSmartRuleLane: () => Promise<RosterSmartRuleLaneResult>;
  applyWorkspace: (workspace: DraftWorkspaceResponse) => void;
  normalizeErrorMessage: (error: unknown, fallbackMessage: string) => string;
};

type SmartGroupingRunOutcome =
  | { status: "applied"; message: string | null }
  | { status: "blocked"; message: string };

const MISSING_DRAFT_MESSAGE = "Öppna en gruppindelning innan du använder Smart slumpa."
const SMART_RULES_NOT_READY_MESSAGE = "Smarta regler kunde inte laddas än. Försök igen."
const GENERIC_RUN_ERROR_MESSAGE = "Det gick inte att köra smart gruppindelning just nu."

export function useSmartGroupingRun(options: UseSmartGroupingRunOptions) {
  const message = ref<string | null>(null);
  const tone = ref<"neutral" | "success" | "warning">("neutral");

  const isBusy = computed(() => options.runningState.value);

  function clearFeedback(): void {
    message.value = null;
    tone.value = "neutral";
  }

  async function run(): Promise<SmartGroupingRunOutcome> {
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

      const persistedDraft = options.draft.value;
      if (!persistedDraft) {
        message.value = MISSING_DRAFT_MESSAGE;
        tone.value = "warning";
        return { status: "blocked", message: MISSING_DRAFT_MESSAGE };
      }

      const result = await apiPost<SmartGroupingRunResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${persistedDraft.id}/smart-run`,
        { expected_revision: persistedDraft.revision },
      );
      if (result.status === "blocked") {
        message.value = result.message;
        tone.value = "warning";
        return { status: "blocked", message: result.message };
      }

      options.applyWorkspace(result.workspace);
      message.value = result.message ?? null;
      tone.value = "success";
      return { status: "applied", message: result.message ?? null };
    } catch (error: unknown) {
      const normalizedMessage = options.normalizeErrorMessage(error, GENERIC_RUN_ERROR_MESSAGE);
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
