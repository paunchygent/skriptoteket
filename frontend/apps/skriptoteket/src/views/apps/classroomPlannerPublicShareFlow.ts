/**
 * Classroom planner public guest share-link flow.
 *
 * This module owns the browser-held guest `Dela länk` lifecycle: flush current
 * browser state, call the public helper with an idempotency key and revoke
 * secret, copy the returned URL, and retain only newest-link metadata in
 * localStorage for best-effort supersede on the next share.
 */

import { computed, ref, unref, type Ref } from "vue";

import { isApiError } from "../../api/client";
import { useToast } from "../../composables/useToast";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";
import type { ClassroomPlannerShareArtifact } from "./classroomPlannerShareApi";
import type { PlanDraft, PlanDraftKind } from "./classroomPlannerTypes";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";
import type { CreatedPublicGuestShare } from "./classroomPlannerPublicShareApi";

type PublicSharePlannerState = {
  draft: PlanDraft | null | Ref<PlanDraft | null>;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type PublicGuestShareMetadata = {
  publicPath: string;
  revokeSecret: string;
  snapshotContentHash: string;
  displayShare: ClassroomPlannerShareArtifact | null;
};

type PendingPublicGuestShareOperation = {
  clientOperationId: string;
  revokeSecret: string;
  snapshotContentHash: string;
  expectedRevision: number;
};

type PublicGuestShareMessages = {
  missingDraftMessage: string;
  initialStatusLabel: string;
  copiedMessage: string;
  revokedMessage: string;
  fallbackMessage: string;
  revokeFallbackMessage: string;
};

type CreateClassroomPlannerPublicShareFlowOptions<DraftKind extends PlanDraftKind> = {
  plannerState: PublicSharePlannerState;
  getSnapshot: () => Promise<ClassroomPlannerGuestSnapshot>;
  draftKind: DraftKind;
  createShare: (params: {
    snapshot: ClassroomPlannerGuestSnapshot;
    expectedRevision: number;
    clientOperationId: string;
    revokeSecret: string;
    previousPublicPath: string | null;
    previousRevokeSecret: string | null;
  }) => Promise<CreatedPublicGuestShare>;
  revokeShare: (params: {
    publicPath: string;
    revokeSecret: string;
  }) => Promise<unknown>;
  messages: PublicGuestShareMessages;
};

const STORAGE_PREFIX = "skriptoteket:classroom-planner:public-share";
const PENDING_STORAGE_PREFIX = `${STORAGE_PREFIX}:pending`;

function normalizeShareError(error: unknown, fallbackMessage: string): string {
  if (isApiError(error)) {
    return error.message || fallbackMessage;
  }
  return normalizeClassroomPlannerUiError(error, fallbackMessage);
}

function randomBrowserSecret(byteLength: number): string {
  const randomValues = new Uint8Array(byteLength);
  crypto.getRandomValues(randomValues);
  const binary = Array.from(randomValues, (value) => String.fromCharCode(value)).join("");
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function randomOperationId(): string {
  if (typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `guest-share-${randomBrowserSecret(18)}`;
}

function metadataStorageKey(
  snapshot: ClassroomPlannerGuestSnapshot,
  draftKind: PlanDraftKind,
): string {
  return [STORAGE_PREFIX, draftKind, snapshot.snapshot_id].join(":");
}

function pendingStorageKey(
  snapshot: ClassroomPlannerGuestSnapshot,
  draftKind: PlanDraftKind,
  expectedRevision: number,
): string {
  return [PENDING_STORAGE_PREFIX, draftKind, snapshot.snapshot_id, expectedRevision].join(":");
}

function readPreviousMetadata(
  snapshot: ClassroomPlannerGuestSnapshot,
  draftKind: PlanDraftKind,
): PublicGuestShareMetadata | null {
  try {
    const raw = localStorage.getItem(metadataStorageKey(snapshot, draftKind));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<PublicGuestShareMetadata>;
    if (
      typeof parsed.publicPath !== "string" ||
      typeof parsed.revokeSecret !== "string"
    ) {
      return null;
    }
    return {
      publicPath: parsed.publicPath,
      revokeSecret: parsed.revokeSecret,
      snapshotContentHash:
        typeof parsed.snapshotContentHash === "string" ? parsed.snapshotContentHash : "",
      displayShare: isDisplayShareArtifact(parsed.displayShare) ? parsed.displayShare : null,
    };
  } catch {
    return null;
  }
}

function isDisplayShareArtifact(value: unknown): value is ClassroomPlannerShareArtifact {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<ClassroomPlannerShareArtifact>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.public_path === "string" &&
    typeof candidate.public_url === "string" &&
    candidate.revoked_at === null
  );
}

function writeLatestMetadata(params: {
  snapshot: ClassroomPlannerGuestSnapshot;
  draftKind: PlanDraftKind;
  publicPath: string;
  revokeSecret: string;
  displayShare: ClassroomPlannerShareArtifact;
}): void {
  try {
    localStorage.setItem(
      metadataStorageKey(params.snapshot, params.draftKind),
      JSON.stringify({
        publicPath: params.publicPath,
        revokeSecret: params.revokeSecret,
        snapshotContentHash: params.snapshot.snapshot_content_hash,
        displayShare: params.displayShare,
      } satisfies PublicGuestShareMetadata),
    );
  } catch {
    return;
  }
}

function clearLatestMetadata(snapshot: ClassroomPlannerGuestSnapshot, draftKind: PlanDraftKind): void {
  try {
    localStorage.removeItem(metadataStorageKey(snapshot, draftKind));
  } catch {
    return;
  }
}

function readOrCreatePendingOperation(
  snapshot: ClassroomPlannerGuestSnapshot,
  draftKind: PlanDraftKind,
  expectedRevision: number,
): PendingPublicGuestShareOperation {
  const storageKey = pendingStorageKey(snapshot, draftKind, expectedRevision);
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<PendingPublicGuestShareOperation>;
      if (
        typeof parsed.clientOperationId === "string" &&
        typeof parsed.revokeSecret === "string" &&
        parsed.expectedRevision === expectedRevision
      ) {
        return {
          clientOperationId: parsed.clientOperationId,
          revokeSecret: parsed.revokeSecret,
          snapshotContentHash:
            typeof parsed.snapshotContentHash === "string" ? parsed.snapshotContentHash : "",
          expectedRevision,
        };
      }
    }
  } catch {
    // Fall through and replace unreadable pending metadata.
  }

  const pending = {
    clientOperationId: randomOperationId(),
    revokeSecret: randomBrowserSecret(32),
    snapshotContentHash: snapshot.snapshot_content_hash,
    expectedRevision,
  } satisfies PendingPublicGuestShareOperation;
  try {
    localStorage.setItem(storageKey, JSON.stringify(pending));
  } catch {
    return pending;
  }
  return pending;
}

function clearPendingOperation(
  snapshot: ClassroomPlannerGuestSnapshot,
  draftKind: PlanDraftKind,
  expectedRevision: number,
): void {
  try {
    localStorage.removeItem(pendingStorageKey(snapshot, draftKind, expectedRevision));
  } catch {
    return;
  }
}

async function copyTextToClipboard(value: string): Promise<boolean> {
  const clipboard = navigator.clipboard;
  if (!clipboard) {
    return false;
  }
  await clipboard.writeText(value);
  return true;
}

export function createClassroomPlannerPublicShareFlow<DraftKind extends PlanDraftKind>(
  options: CreateClassroomPlannerPublicShareFlowOptions<DraftKind>,
) {
  const toast = useToast();
  const isBusy = ref(false);
  const revokingShareId = ref<string | null>(null);
  const statusLabel = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);
  const shares = ref<ClassroomPlannerShareArtifact[]>([]);

  const isDraftInScope = computed(() => {
    return unref(options.plannerState.draft)?.draft_kind === options.draftKind;
  });

  function getActiveDraft(): PlanDraft | null {
    const draft = unref(options.plannerState.draft);
    if (!draft || draft.draft_kind !== options.draftKind) {
      return null;
    }
    return draft;
  }

  async function hydrateLatestBrowserOwnedShare(): Promise<void> {
    if (!getActiveDraft() || shares.value.length > 0) {
      return;
    }
    try {
      const snapshot = await options.getSnapshot();
      if (shares.value.length > 0) {
        return;
      }
      const metadata = readPreviousMetadata(snapshot, options.draftKind);
      if (!metadata?.displayShare || metadata.displayShare.public_path !== metadata.publicPath) {
        return;
      }
      shares.value = [metadata.displayShare];
    } catch {
      return;
    }
  }

  void hydrateLatestBrowserOwnedShare();

  async function startShare(): Promise<void> {
    if (isBusy.value) {
      return;
    }

    const activeDraft = getActiveDraft();
    if (!activeDraft) {
      errorMessage.value = options.messages.missingDraftMessage;
      toast.warning(options.messages.missingDraftMessage);
      return;
    }

    isBusy.value = true;
    statusLabel.value = options.messages.initialStatusLabel;
    errorMessage.value = null;

    try {
      const saveOutcome = await options.plannerState.prepareForExport({
        conflictMessage: "Lös sparkonflikten innan du delar länken.",
        fallbackMessage: "Kunde inte spara ändringarna innan delning.",
      });
      if (saveOutcome.status === "blocked") {
        errorMessage.value = saveOutcome.message;
        toast.warning(saveOutcome.message);
        return;
      }

      const draftAfterFlush = getActiveDraft();
      if (!draftAfterFlush || draftAfterFlush.id !== activeDraft.id) {
        throw new Error(options.messages.fallbackMessage);
      }

      const snapshot = await options.getSnapshot();
      const previous = readPreviousMetadata(snapshot, options.draftKind);
      const pending = readOrCreatePendingOperation(
        snapshot,
        options.draftKind,
        draftAfterFlush.revision,
      );
      const created = await options.createShare({
        snapshot,
        expectedRevision: draftAfterFlush.revision,
        clientOperationId: pending.clientOperationId,
        revokeSecret: pending.revokeSecret,
        previousPublicPath: previous?.publicPath ?? null,
        previousRevokeSecret: previous?.revokeSecret ?? null,
      });
      const displayShare = {
        ...created.artifact,
        public_path: created.artifact.public_path ?? created.public_path,
        public_url: created.artifact.public_url ?? created.public_url,
      };
      writeLatestMetadata({
        snapshot,
        draftKind: options.draftKind,
        publicPath: created.public_path,
        revokeSecret: created.public_revoke_secret,
        displayShare,
      });
      clearPendingOperation(snapshot, options.draftKind, draftAfterFlush.revision);
      shares.value = [displayShare];

      const copied = await copyTextToClipboard(created.public_url);
      statusLabel.value = copied ? null : created.public_url;
      toast.success(options.messages.copiedMessage);
      errorMessage.value = null;
    } catch {
      errorMessage.value = null;
      toast.failure(options.messages.fallbackMessage);
    } finally {
      isBusy.value = false;
      if (statusLabel.value === options.messages.initialStatusLabel) {
        statusLabel.value = null;
      }
    }
  }

  async function copyShareLink(share: ClassroomPlannerShareArtifact): Promise<void> {
    if (!share.public_url) {
      errorMessage.value = options.messages.fallbackMessage;
      toast.warning(options.messages.fallbackMessage);
      return;
    }

    try {
      const copied = await copyTextToClipboard(share.public_url);
      statusLabel.value = copied ? null : share.public_url;
      errorMessage.value = null;
      toast.success(options.messages.copiedMessage);
    } catch (error: unknown) {
      const message = normalizeShareError(error, options.messages.fallbackMessage);
      errorMessage.value = message;
      toast.warning(message);
    }
  }

  async function revokePublicShare(share: ClassroomPlannerShareArtifact): Promise<void> {
    if (revokingShareId.value !== null || share.revoked_at) {
      return;
    }
    const publicPath = share.public_path;
    if (!publicPath) {
      errorMessage.value = null;
      toast.failure(options.messages.revokeFallbackMessage);
      return;
    }

    revokingShareId.value = share.id;
    errorMessage.value = null;
    try {
      const snapshot = await options.getSnapshot();
      const metadata = readPreviousMetadata(snapshot, options.draftKind);
      if (!metadata || metadata.publicPath !== publicPath) {
        errorMessage.value = null;
        toast.failure(options.messages.revokeFallbackMessage);
        return;
      }
      await options.revokeShare({
        publicPath,
        revokeSecret: metadata.revokeSecret,
      });
      clearLatestMetadata(snapshot, options.draftKind);
      shares.value = shares.value.filter((item) => item.id !== share.id);
      statusLabel.value = null;
      toast.success(options.messages.revokedMessage);
    } catch {
      errorMessage.value = null;
      toast.failure(options.messages.revokeFallbackMessage);
    } finally {
      revokingShareId.value = null;
    }
  }

  return {
    isBusy,
    revokingShareId,
    statusLabel,
    errorMessage,
    isDraftInScope,
    shares,
    startShare,
    copyShareLink,
    revokePublicShare,
  };
}
