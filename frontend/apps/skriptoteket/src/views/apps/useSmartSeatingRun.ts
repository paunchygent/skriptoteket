/**
 * Smart seating run orchestration.
 *
 * This composable keeps the backend-owned smart seating flow out of the main
 * planner store so the store stays focused on composing lanes and workspace
 * state. It flushes the draft lane and the roster smart-rule lane, then calls
 * the seating smart-run endpoint only when the persisted state is honest.
 */

import { computed, ref, type Ref } from "vue";

import { apiPost } from "../../api/client";
import type {
  DraftWorkspaceResponse,
  PlanDraft,
  SmartSeatingRunResponse,
  SmartRuleDiagnostic,
} from "./classroomPlannerTypes";
import type { DraftPersistenceLaneResult } from "./useDraftPersistenceLane";
import type { RosterSmartRuleLaneResult } from "./useRosterSmartRuleLane";

type UseSmartSeatingRunOptions = {
  draft: Ref<PlanDraft | null>;
  smartRulesHydrated: Ref<boolean>;
  runningState: Ref<boolean>;
  flushDraftLane: () => Promise<DraftPersistenceLaneResult>;
  flushSmartRuleLane: () => Promise<RosterSmartRuleLaneResult>;
  applyWorkspace: (workspace: DraftWorkspaceResponse) => void;
  applyRuleDiagnostics?: (diagnostics: SmartRuleDiagnostic[]) => void;
  normalizeErrorMessage: (error: unknown, fallbackMessage: string) => string;
};

type SmartSeatingRunOutcome =
  | { status: "applied"; message: string | null }
  | { status: "blocked"; message: string };

const MISSING_DRAFT_MESSAGE = "Öppna ett sittschema innan du använder Smart slumpa."
const SMART_RULES_NOT_READY_MESSAGE = "Smarta regler kunde inte laddas än. Försök igen."
const GENERIC_RUN_ERROR_MESSAGE = "Det gick inte att köra smart placering just nu."
const FIXED_SEAT_RUN_ERROR_MESSAGE =
  "En fast plats kan inte användas längre. Kontrollera eleven och platsen och försök igen."

function normalizeSmartSeatingRunMessage(messageText: string): string {
  if (/fixed.?seat|fast plats|fasta platser/i.test(messageText)) {
    return FIXED_SEAT_RUN_ERROR_MESSAGE
  }
  return messageText
}

export function useSmartSeatingRun(options: UseSmartSeatingRunOptions) {
  const message = ref<string | null>(null);
  const tone = ref<"neutral" | "success" | "warning">("neutral");

  const isBusy = computed(() => options.runningState.value);

  function clearFeedback(): void {
    message.value = null;
    tone.value = "neutral";
    options.applyRuleDiagnostics?.([]);
  }

  async function run(): Promise<SmartSeatingRunOutcome> {
    const activeDraft = options.draft.value
    if (!activeDraft) {
      message.value = MISSING_DRAFT_MESSAGE
      tone.value = "warning"
      return { status: "blocked", message: MISSING_DRAFT_MESSAGE }
    }
    if (!options.smartRulesHydrated.value) {
      message.value = SMART_RULES_NOT_READY_MESSAGE
      tone.value = "warning"
      return { status: "blocked", message: SMART_RULES_NOT_READY_MESSAGE }
    }

    options.runningState.value = true
    clearFeedback()

    try {
      const smartRuleFlush = await options.flushSmartRuleLane()
      if (smartRuleFlush.status === "blocked") {
        message.value = smartRuleFlush.message
        tone.value = "warning"
        return { status: "blocked", message: smartRuleFlush.message }
      }

      const draftFlush = await options.flushDraftLane()
      if (draftFlush.status === "blocked") {
        message.value = draftFlush.message
        tone.value = "warning"
        return { status: "blocked", message: draftFlush.message }
      }

      const persistedDraft = options.draft.value
      if (!persistedDraft) {
        message.value = MISSING_DRAFT_MESSAGE
        tone.value = "warning"
        return { status: "blocked", message: MISSING_DRAFT_MESSAGE }
      }

      const result = await apiPost<SmartSeatingRunResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/seating/${persistedDraft.id}/smart-run`,
        { expected_revision: persistedDraft.revision },
      )

      options.applyWorkspace(result.workspace)
      options.applyRuleDiagnostics?.(result.rule_diagnostics ?? [])
      message.value = result.message ?? null
      tone.value = "success"
      return { status: "applied", message: result.message ?? null }
    } catch (error: unknown) {
      const normalizedMessage = normalizeSmartSeatingRunMessage(
        options.normalizeErrorMessage(error, GENERIC_RUN_ERROR_MESSAGE),
      )
      message.value = normalizedMessage
      tone.value = "warning"
      return { status: "blocked", message: normalizedMessage }
    } finally {
      options.runningState.value = false
    }
  }

  return {
    isBusy,
    message,
    tone,
    clearFeedback,
    run,
  }
}
