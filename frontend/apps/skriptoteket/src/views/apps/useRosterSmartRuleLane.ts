/**
 * Roster smart-rule lane.
 *
 * Purpose:
 *   Own roster-global smart-rule hydration and autosave timing without merging
 *   those states into draft persistence truth. Hydration failure is distinct
 *   from persistence conflict or save error.
 *
 * Relationships:
 *   - composed by `useClassroomState.ts`
 *   - guarded by `usePlannerSessionController.ts` session tokens
 *   - coordinated by `plannerTransitionPolicies.ts` for smart-lane-first
 *     abandon/exit semantics and fail-safe workspace loading
 */

import { computed, ref } from "vue";

import { ApiError } from "../../api/client";
import type {
  FixedSeatRule,
  RelationshipRule,
  RosterSmartRulesResponse,
  SaveStatus,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";

const DEFAULT_AUTOSAVE_DELAY_MS = 900;
const SMART_RULE_CONFLICT_FALLBACK_MESSAGE =
  "Smarta regler har ändrats i en annan flik. Ladda om arbetsytan innan du fortsätter.";

export type SmartRuleHydrationStatus = "idle" | "loading" | "ready" | "error";

export type RosterSmartRulePatchPayload = {
  expected_revision: number;
  seating_preferences: StudentSeatingPreference[];
  relationship_rules: RelationshipRule[];
  fixed_seat_rules: FixedSeatRule[];
};

export type RosterSmartRuleLaneResult =
  | { status: "saved" }
  | { status: "blocked"; reason: "conflict" | "error"; message: string };

type UseRosterSmartRuleLaneOptions = {
  autosaveDelayMs?: number;
  canSchedule: () => boolean;
  getSessionToken: () => number;
  normalizeErrorMessage: (error: unknown, fallbackMessage: string) => string;
  persistSmartRules: (
    rosterId: string,
    patch: RosterSmartRulePatchPayload,
  ) => Promise<RosterSmartRulesResponse>;
  serializePatch: () => RosterSmartRulePatchPayload;
  applyCommittedRules: (rules: RosterSmartRulesResponse) => void;
  applyAcknowledgement: (rules: RosterSmartRulesResponse) => void;
};

export function useRosterSmartRuleLane(options: UseRosterSmartRuleLaneOptions) {
  const autosaveDelayMs = options.autosaveDelayMs ?? DEFAULT_AUTOSAVE_DELAY_MS;
  const boundRosterId = ref<string | null>(null);
  const status = ref<SaveStatus>("idle");
  const message = ref<string | null>(null);
  const hydrationStatus = ref<SmartRuleHydrationStatus>("idle");
  const hydrationMessage = ref<string | null>(null);
  const hasPendingChanges = ref(false);
  const inFlight = ref(false);

  let autosaveTimer: ReturnType<typeof setTimeout> | null = null;
  let mutationVersion = 0;
  let saveQueued = false;

  const isSaving = computed(() => {
    return status.value === "saving" || inFlight.value;
  });

  const isHydrated = computed(() => hydrationStatus.value === "ready");

  function clearAutosaveTimer(): void {
    if (!autosaveTimer) {
      return;
    }
    clearTimeout(autosaveTimer);
    autosaveTimer = null;
  }

  function bindRoster(rosterId: string | null): void {
    clearAutosaveTimer();
    boundRosterId.value = rosterId;
    hasPendingChanges.value = false;
    inFlight.value = false;
    mutationVersion = 0;
    saveQueued = false;
    status.value = "idle";
    message.value = null;
    hydrationStatus.value = rosterId ? "loading" : "idle";
    hydrationMessage.value = null;
  }

  function syncBoundRoster(rosterId: string | null): void {
    boundRosterId.value = rosterId;
  }

  function markHydrating(): void {
    hydrationStatus.value = boundRosterId.value ? "loading" : "idle";
    hydrationMessage.value = null;
  }

  function applyHydratedRules(): void {
    hydrationStatus.value = "ready";
    hydrationMessage.value = null;
  }

  function failHydration(messageText: string): void {
    hydrationStatus.value = "error";
    hydrationMessage.value = messageText;
  }

  function discardPendingChanges(): void {
    clearAutosaveTimer();
    hasPendingChanges.value = false;
    saveQueued = false;
    status.value = "idle";
    message.value = null;
  }

  function resolveResult(): RosterSmartRuleLaneResult {
    if (status.value === "conflict") {
      return {
        status: "blocked",
        reason: "conflict",
        message: message.value ?? SMART_RULE_CONFLICT_FALLBACK_MESSAGE,
      };
    }
    if (status.value === "error") {
      return {
        status: "blocked",
        reason: "error",
        message: message.value ?? "Kunde inte spara smarta regler.",
      };
    }
    return { status: "saved" };
  }

  function markDirty(): void {
    if (!options.canSchedule()) {
      return;
    }
    mutationVersion += 1;
    hasPendingChanges.value = true;
    message.value = null;
    status.value = "saving";
    if (!boundRosterId.value) {
      return;
    }
    if (inFlight.value) {
      saveQueued = true;
      return;
    }
    clearAutosaveTimer();
    autosaveTimer = window.setTimeout(() => {
      void persistPendingChanges();
    }, autosaveDelayMs);
  }

  async function waitForIdle(): Promise<void> {
    while (inFlight.value) {
      await new Promise((resolve) => window.setTimeout(resolve, 10));
    }
  }

  async function persistPendingChanges(): Promise<RosterSmartRuleLaneResult | "cancelled"> {
    const rosterId = boundRosterId.value;
    if (!rosterId || !hasPendingChanges.value) {
      return { status: "saved" };
    }
    if (inFlight.value) {
      saveQueued = true;
      return { status: "saved" };
    }

    clearAutosaveTimer();
    inFlight.value = true;
    status.value = "saving";
    message.value = null;
    const requestSessionToken = options.getSessionToken();
    const requestMutationVersion = mutationVersion;
    const patch = options.serializePatch();

    try {
      const rules = await options.persistSmartRules(rosterId, patch);
      if (
        options.getSessionToken() !== requestSessionToken
        || boundRosterId.value !== rosterId
      ) {
        return "cancelled";
      }
      if (mutationVersion !== requestMutationVersion) {
        options.applyAcknowledgement(rules);
        applyHydratedRules();
        return { status: "saved" };
      }
      options.applyCommittedRules(rules);
      hasPendingChanges.value = false;
      status.value = "saved";
      message.value = null;
      applyHydratedRules();
      return { status: "saved" };
    } catch (error: unknown) {
      if (
        options.getSessionToken() !== requestSessionToken
        || boundRosterId.value !== rosterId
      ) {
        return "cancelled";
      }
      if (error instanceof ApiError && error.status === 409) {
        status.value = "conflict";
        message.value = error.message || SMART_RULE_CONFLICT_FALLBACK_MESSAGE;
      } else {
        status.value = "error";
        message.value = options.normalizeErrorMessage(error, "Kunde inte spara smarta regler.");
      }
      return resolveResult();
    } finally {
      inFlight.value = false;
      if (saveQueued && status.value !== "conflict") {
        saveQueued = false;
        if (boundRosterId.value && hasPendingChanges.value) {
          void persistPendingChanges();
        }
      }
    }
  }

  async function flushPendingChanges(): Promise<RosterSmartRuleLaneResult> {
    clearAutosaveTimer();
    while (true) {
      if (inFlight.value) {
        await waitForIdle();
        if (status.value === "conflict" || status.value === "error") {
          return resolveResult();
        }
        continue;
      }
      if (!hasPendingChanges.value) {
        return resolveResult();
      }
      const result = await persistPendingChanges();
      if (result === "cancelled") {
        return { status: "saved" };
      }
      if (result.status === "blocked") {
        return result;
      }
    }
  }

  return {
    boundRosterId,
    status,
    message,
    hydrationStatus,
    hydrationMessage,
    hasPendingChanges,
    isSaving,
    isHydrated,
    bindRoster,
    syncBoundRoster,
    markHydrating,
    applyHydratedRules,
    failHydration,
    discardPendingChanges,
    markDirty,
    waitForIdle,
    flushPendingChanges,
  };
}
