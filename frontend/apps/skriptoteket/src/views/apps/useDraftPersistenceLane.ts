/**
 * Draft persistence lane.
 *
 * Purpose:
 *   Own draft-local autosave timing, retry bookkeeping, and request guarding
 *   for Klassrumskartan arrangement state. This lane persists only the active
 *   draft payload and never decides cross-lane transition policy by itself.
 *
 * Relationships:
 *   - composed by `useClassroomState.ts`
 *   - guarded by `usePlannerSessionController.ts` session tokens
 *   - coordinated by `plannerTransitionPolicies.ts` for history, export,
 *     workspace-switch, and exit semantics
 */

import { computed, ref } from "vue";

import { ApiError } from "../../api/client";
import type { DraftWorkspaceResponse, SaveStatus } from "./classroomPlannerTypes";

const DEFAULT_AUTOSAVE_DELAY_MS = 900;
const DRAFT_CONFLICT_FALLBACK_MESSAGE =
  "Utkastet har ändrats i en annan flik. Ladda om arbetsytan innan du fortsätter.";

export type DraftLanePatchPayload = {
  expected_revision: number | null;
  smart_enabled: boolean;
  use_history: boolean;
  grouping_seating_distance_enabled: boolean;
  groups: DraftWorkspaceResponse["groups"];
  group_assignments: DraftWorkspaceResponse["group_assignments"];
  seat_assignments: DraftWorkspaceResponse["seat_assignments"];
};

export type DraftPersistenceLaneResult =
  | { status: "saved" }
  | { status: "blocked"; reason: "conflict" | "error"; message: string };

type DraftPersistenceLaneOptions = {
  autosaveDelayMs?: number;
  canSchedule: () => boolean;
  getSessionToken: () => number;
  normalizeErrorMessage: (error: unknown, fallbackMessage: string) => string;
  persistDraft: (draftId: string, patch: DraftLanePatchPayload) => Promise<DraftWorkspaceResponse>;
  serializePatch: () => DraftLanePatchPayload;
  applyCommittedWorkspace: (workspace: DraftWorkspaceResponse) => void;
  applyAcknowledgement: (workspace: DraftWorkspaceResponse) => void;
};

export function useDraftPersistenceLane(options: DraftPersistenceLaneOptions) {
  const autosaveDelayMs = options.autosaveDelayMs ?? DEFAULT_AUTOSAVE_DELAY_MS;
  const boundDraftId = ref<string | null>(null);
  const status = ref<SaveStatus>("idle");
  const message = ref<string | null>(null);
  const hasPendingChanges = ref(false);
  const inFlight = ref(false);

  let autosaveTimer: ReturnType<typeof setTimeout> | null = null;
  let mutationVersion = 0;
  let saveQueued = false;

  const isSaving = computed(() => {
    return status.value === "saving" || inFlight.value;
  });

  function clearAutosaveTimer(): void {
    if (!autosaveTimer) {
      return;
    }
    clearTimeout(autosaveTimer);
    autosaveTimer = null;
  }

  function resetBoundDraft(draftId: string | null): void {
    clearAutosaveTimer();
    boundDraftId.value = draftId;
    hasPendingChanges.value = false;
    inFlight.value = false;
    message.value = null;
    mutationVersion = 0;
    saveQueued = false;
    status.value = "idle";
  }

  function syncBoundDraft(draftId: string | null): void {
    boundDraftId.value = draftId;
  }

  function discardPendingChanges(): void {
    clearAutosaveTimer();
    hasPendingChanges.value = false;
    message.value = null;
    saveQueued = false;
    status.value = "idle";
  }

  function acknowledgeExternalCommit(draftId: string | null): void {
    clearAutosaveTimer();
    boundDraftId.value = draftId;
    hasPendingChanges.value = false;
    message.value = null;
    saveQueued = false;
    mutationVersion += 1;
    status.value = draftId ? "saved" : "idle";
  }

  function resolveResult(): DraftPersistenceLaneResult {
    if (status.value === "conflict") {
      return {
        status: "blocked",
        reason: "conflict",
        message: message.value ?? DRAFT_CONFLICT_FALLBACK_MESSAGE,
      };
    }
    if (status.value === "error") {
      return {
        status: "blocked",
        reason: "error",
        message: message.value ?? "Kunde inte spara utkastet.",
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
    if (!boundDraftId.value) {
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

  async function persistPendingChanges(): Promise<DraftPersistenceLaneResult | "cancelled"> {
    const draftId = boundDraftId.value;
    if (!draftId || !hasPendingChanges.value) {
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
      const workspace = await options.persistDraft(draftId, patch);
      if (
        options.getSessionToken() !== requestSessionToken
        || boundDraftId.value !== draftId
      ) {
        return "cancelled";
      }
      if (mutationVersion !== requestMutationVersion) {
        if (hasPendingChanges.value) {
          options.applyAcknowledgement(workspace);
        }
        return { status: "saved" };
      }
      options.applyCommittedWorkspace(workspace);
      hasPendingChanges.value = false;
      status.value = "saved";
      message.value = null;
      return { status: "saved" };
    } catch (error: unknown) {
      if (
        options.getSessionToken() !== requestSessionToken
        || boundDraftId.value !== draftId
      ) {
        return "cancelled";
      }
      if (error instanceof ApiError && error.status === 409) {
        status.value = "conflict";
        message.value = error.message || DRAFT_CONFLICT_FALLBACK_MESSAGE;
      } else {
        status.value = "error";
        message.value = options.normalizeErrorMessage(error, "Kunde inte spara utkastet.");
      }
      return resolveResult();
    } finally {
      inFlight.value = false;
      if (saveQueued && status.value !== "conflict") {
        saveQueued = false;
        if (boundDraftId.value && hasPendingChanges.value) {
          void persistPendingChanges();
        }
      }
    }
  }

  async function flushPendingChanges(): Promise<DraftPersistenceLaneResult> {
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
    boundDraftId,
    status,
    message,
    hasPendingChanges,
    isSaving,
    resetBoundDraft,
    syncBoundDraft,
    discardPendingChanges,
    acknowledgeExternalCommit,
    markDirty,
    waitForIdle,
    flushPendingChanges,
  };
}
