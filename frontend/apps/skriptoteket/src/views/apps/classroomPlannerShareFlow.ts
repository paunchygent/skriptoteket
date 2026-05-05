/**
 * Shared classroom planner share-link orchestration.
 *
 * This module owns the authenticated Dela länk state machine for grouping and
 * seating drafts: reuse export preparation, send the post-flush revision,
 * copy newly created links, and keep owned share list/revoke behavior separate
 * from export-job polling.
 */

import { computed, ref, watch } from "vue";

import { isApiError } from "../../api/client";
import { useToast } from "../../composables/useToast";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";
import type { PlanDraft, PlanDraftKind } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";
import type {
  ClassroomPlannerShareArtifact,
  CreatedClassroomPlannerShare,
} from "./classroomPlannerShareApi";

type ClassroomPlannerSharePlannerState = {
  draft: PlanDraft | null;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type ClassroomPlannerShareMessages = {
  missingDraftMessage: string;
  scopeChangedMessage: string;
  initialStatusLabel: string;
  copiedMessage: string;
  createFallbackMessage: string;
  listFallbackMessage: string;
  revokeFallbackMessage: string;
  copyUnavailableMessage: string;
};

type CreateClassroomPlannerShareFlowOptions<DraftKind extends PlanDraftKind> = {
  plannerState: ClassroomPlannerSharePlannerState;
  draftKind: DraftKind;
  createShare: (params: {
    draftId: string;
    expectedRevision: number;
  }) => Promise<CreatedClassroomPlannerShare>;
  listShares: (draftId: string) => Promise<ClassroomPlannerShareArtifact[]>;
  revokeShare: (shareId: string) => Promise<ClassroomPlannerShareArtifact>;
  messages: ClassroomPlannerShareMessages;
};

type ShareScope = {
  draftId: string;
  token: number;
};

class ShareFlowScopeChangedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ShareFlowScopeChangedError";
  }
}

function normalizeShareError(error: unknown, fallbackMessage: string): string {
  if (isApiError(error)) {
    return error.message || fallbackMessage;
  }
  return normalizeClassroomPlannerUiError(error, fallbackMessage);
}

async function copyTextToClipboard(value: string): Promise<boolean> {
  const clipboard = navigator.clipboard;
  if (!clipboard) {
    return false;
  }
  await clipboard.writeText(value);
  return true;
}

export function createClassroomPlannerShareFlow<DraftKind extends PlanDraftKind>(
  options: CreateClassroomPlannerShareFlowOptions<DraftKind>,
) {
  const toast = useToast();
  const shares = ref<ClassroomPlannerShareArtifact[]>([]);
  const isCreating = ref(false);
  const isLoading = ref(false);
  const revokingShareId = ref<string | null>(null);
  const statusLabel = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);
  const copiedShareId = ref<string | null>(null);
  const draftScopeToken = ref(0);

  const isBusy = computed(
    () => isCreating.value || isLoading.value || revokingShareId.value !== null,
  );

  function getActiveDraftId(): string | null {
    const activeDraft = options.plannerState.draft;
    if (!activeDraft || activeDraft.draft_kind !== options.draftKind) {
      return null;
    }
    return activeDraft.id;
  }

  function isActiveScope(scope: ShareScope): boolean {
    return draftScopeToken.value === scope.token && getActiveDraftId() === scope.draftId;
  }

  function ensureActiveScope(scope: ShareScope): void {
    if (!isActiveScope(scope)) {
      throw new ShareFlowScopeChangedError(options.messages.scopeChangedMessage);
    }
  }

  function resetShareState(): void {
    shares.value = [];
    isCreating.value = false;
    isLoading.value = false;
    revokingShareId.value = null;
    statusLabel.value = null;
    errorMessage.value = null;
    copiedShareId.value = null;
  }

  function replaceShare(share: ClassroomPlannerShareArtifact): void {
    const nextShares = shares.value.filter((item) => item.id !== share.id);
    shares.value = [share, ...nextShares];
  }

  async function refreshSharesForScope(scope: ShareScope): Promise<void> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const loadedShares = await options.listShares(scope.draftId);
      ensureActiveScope(scope);
      shares.value = loadedShares;
    } catch (error: unknown) {
      if (error instanceof ShareFlowScopeChangedError || !isActiveScope(scope)) {
        return;
      }
      shares.value = [];
      errorMessage.value = normalizeShareError(error, options.messages.listFallbackMessage);
    } finally {
      if (isActiveScope(scope)) {
        isLoading.value = false;
      }
    }
  }

  async function copyShareLink(share: ClassroomPlannerShareArtifact): Promise<void> {
    copiedShareId.value = null;
    errorMessage.value = null;
    if (!share.public_url) {
      errorMessage.value = options.messages.copyUnavailableMessage;
      return;
    }
    try {
      const copied = await copyTextToClipboard(share.public_url);
      if (!copied) {
        statusLabel.value = share.public_url;
        return;
      }
      copiedShareId.value = share.id;
      statusLabel.value = null;
      toast.success(options.messages.copiedMessage);
    } catch (error: unknown) {
      errorMessage.value = normalizeShareError(error, "Kunde inte kopiera länken.");
    }
  }

  async function startShare(): Promise<void> {
    if (isBusy.value) {
      return;
    }

    const initialDraftId = getActiveDraftId();
    if (!initialDraftId) {
      errorMessage.value = options.messages.missingDraftMessage;
      statusLabel.value = null;
      return;
    }

    const scope = {
      draftId: initialDraftId,
      token: draftScopeToken.value,
    } satisfies ShareScope;

    isCreating.value = true;
    errorMessage.value = null;
    statusLabel.value = options.messages.initialStatusLabel;
    copiedShareId.value = null;

    const saveOutcome = await options.plannerState.prepareForExport({
      conflictMessage: "Lös sparkonflikten innan du delar länken.",
      fallbackMessage: "Kunde inte spara ändringarna innan delning.",
    });
    if (saveOutcome.status === "blocked") {
      if (!isActiveScope(scope)) {
        return;
      }
      isCreating.value = false;
      errorMessage.value = saveOutcome.message;
      statusLabel.value = null;
      return;
    }

    if (!isActiveScope(scope)) {
      return;
    }

    const activeDraft = options.plannerState.draft;
    if (!activeDraft || activeDraft.draft_kind !== options.draftKind) {
      throw new ShareFlowScopeChangedError(options.messages.scopeChangedMessage);
    }

    try {
      const created = await options.createShare({
        draftId: activeDraft.id,
        expectedRevision: activeDraft.revision,
      });
      ensureActiveScope(scope);
      replaceShare(created.artifact);
      await copyShareLink(created.artifact);
    } catch (error: unknown) {
      if (error instanceof ShareFlowScopeChangedError || !isActiveScope(scope)) {
        return;
      }
      toast.failure(options.messages.createFallbackMessage);
      errorMessage.value = null;
      statusLabel.value = null;
    } finally {
      if (isActiveScope(scope)) {
        isCreating.value = false;
      }
    }
  }

  async function revokeOwnedShare(share: ClassroomPlannerShareArtifact): Promise<void> {
    if (revokingShareId.value !== null || share.revoked_at) {
      return;
    }
    revokingShareId.value = share.id;
    errorMessage.value = null;
    copiedShareId.value = null;
    try {
      const revoked = await options.revokeShare(share.id);
      replaceShare(revoked);
      toast.success("Länken är återkallad.");
    } catch {
      toast.failure(options.messages.revokeFallbackMessage);
      errorMessage.value = null;
    } finally {
      revokingShareId.value = null;
    }
  }

  watch(
    () => options.plannerState.draft?.id ?? null,
    (draftId) => {
      draftScopeToken.value += 1;
      resetShareState();
      if (!draftId || options.plannerState.draft?.draft_kind !== options.draftKind) {
        return;
      }
      const scope = {
        draftId,
        token: draftScopeToken.value,
      } satisfies ShareScope;
      void refreshSharesForScope(scope);
    },
    { immediate: true },
  );

  return {
    shares,
    isBusy,
    isLoading,
    revokingShareId,
    statusLabel,
    errorMessage,
    copiedShareId,
    startShare,
    copyShareLink,
    revokeOwnedShare,
    refreshShares: async () => {
      const draftId = getActiveDraftId();
      if (!draftId) {
        resetShareState();
        return;
      }
      const scope = {
        draftId,
        token: draftScopeToken.value,
      } satisfies ShareScope;
      await refreshSharesForScope(scope);
    },
  };
}
