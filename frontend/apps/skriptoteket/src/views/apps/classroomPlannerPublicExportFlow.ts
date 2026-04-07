/**
 * Classroom planner public export-flow orchestration.
 *
 * This module owns the guest-only direct-download export flow: flush the
 * browser-owned snapshot, call the public export helper, trigger a download,
 * and write a deduped export checkpoint back into the guest snapshot.
 */

import { computed, ref, unref, type Ref } from "vue";

import { isApiError } from "../../api/client";
import { useToast } from "../../composables/useToast";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { GuestSnapshotMutationRunner } from "./classroomPlannerGuestDraftPersistence";
import {
  appendGuestCheckpointDescriptor,
  resolveGuestExportCheckpointDescriptor,
} from "./classroomPlannerGuestDraftMutations";
import { triggerPlannerBrowserDownload } from "./plannerBrowserDownload";
import type { PlanDraft, PlanDraftKind } from "./classroomPlannerTypes";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";
import type { PlannerTransitionResult } from "./plannerTransitionPolicies";

type PublicExportPlannerState = {
  draft: PlanDraft | null | Ref<PlanDraft | null>;
  prepareForExport: (messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }) => Promise<PlannerTransitionResult>;
};

type PublicExportMessages<Option> = {
  missingDraftMessage: string;
  initialStatusLabelForOption: (option: Option) => string;
  successMessageForOption: (option: Option) => string;
  startErrorMessageForOption: (option: Option) => string;
  fallbackDownloadName: (option: Option) => string;
};

type CreateClassroomPlannerPublicExportFlowOptions<Option, DraftKind extends PlanDraftKind> = {
  plannerState: PublicExportPlannerState;
  getSnapshot: () => Promise<ClassroomPlannerGuestSnapshot>;
  persistSnapshotMutation: GuestSnapshotMutationRunner;
  draftKind: DraftKind;
  defaultOption: Option;
  exportSnapshot: (
    snapshot: ClassroomPlannerGuestSnapshot,
    expectedRevision: number,
    option: Option,
  ) => Promise<{ blob: Blob; filename: string | null }>;
  messages: PublicExportMessages<Option>;
};

function normalizeExportError(error: unknown, fallbackMessage: string): string {
  if (isApiError(error)) {
    return error.message || fallbackMessage;
  }
  return normalizeClassroomPlannerUiError(error, fallbackMessage);
}

export function createClassroomPlannerPublicExportFlow<
  Option,
  DraftKind extends PlanDraftKind,
>(
  options: CreateClassroomPlannerPublicExportFlowOptions<Option, DraftKind>,
) {
  const toast = useToast();
  const isBusy = ref(false);
  const statusLabel = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);

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

  async function persistExportCheckpoint(input: {
    exportedSnapshot: ClassroomPlannerGuestSnapshot;
    draftId: string;
    label: string | null;
  }): Promise<void> {
    await options.persistSnapshotMutation({
      mutate(snapshot, updatedAt) {
        const descriptor = resolveGuestExportCheckpointDescriptor(input.exportedSnapshot, {
          draftKind: options.draftKind,
          draftId: input.draftId,
          createdAt: updatedAt,
          label: input.label,
        });
        if (!descriptor) {
          return {
            nextSnapshot: snapshot,
            result: undefined,
          };
        }
        return {
          nextSnapshot: appendGuestCheckpointDescriptor(snapshot, {
            descriptor,
            updatedAt,
          }),
          result: undefined,
        };
      },
    });
  }

  async function startExport(option: Option): Promise<void> {
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
    statusLabel.value = options.messages.initialStatusLabelForOption(option);
    errorMessage.value = null;

    try {
      const saveOutcome = await options.plannerState.prepareForExport({
        conflictMessage: "Lös sparkonflikten innan du exporterar.",
        fallbackMessage: "Kunde inte spara ändringarna innan exporten startade.",
      });
      if (saveOutcome.status === "blocked") {
        errorMessage.value = saveOutcome.message;
        toast.warning(saveOutcome.message);
        return;
      }

      const draftAfterFlush = getActiveDraft();
      if (!draftAfterFlush || draftAfterFlush.id !== activeDraft.id) {
        throw new Error(options.messages.startErrorMessageForOption(option));
      }

      const exportedSnapshot = await options.getSnapshot();
      const result = await options.exportSnapshot(exportedSnapshot, draftAfterFlush.revision, option);
      triggerPlannerBrowserDownload(
        result.blob,
        result.filename ?? options.messages.fallbackDownloadName(option),
      );

      await persistExportCheckpoint({
        exportedSnapshot,
        draftId: draftAfterFlush.id,
        label: result.filename ?? options.messages.fallbackDownloadName(option),
      });

      toast.success(options.messages.successMessageForOption(option));
      errorMessage.value = null;
    } catch (error: unknown) {
      const message = normalizeExportError(
        error,
        options.messages.startErrorMessageForOption(option),
      );
      errorMessage.value = message;
      toast.warning(message);
    } finally {
      isBusy.value = false;
      statusLabel.value = null;
    }
  }

  async function startDefaultExport(): Promise<void> {
    await startExport(options.defaultOption);
  }

  return {
    isBusy,
    statusLabel,
    errorMessage,
    isDraftInScope,
    startDefaultExport,
    startExport,
  };
}
