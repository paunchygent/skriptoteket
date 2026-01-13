import type { components } from "../../../api/openapi";
import type { VirtualFileId } from "../virtualFiles";
import type { AppliedEditOpsSnapshot } from "./editOpsSnapshots";

type EditorEditOpsSelection = components["schemas"]["EditorEditOpsSelection"];
type EditorEditOpsCursor = components["schemas"]["EditorEditOpsCursor"];
type EditorEditOpsPreviewMeta = components["schemas"]["EditorEditOpsPreviewMeta"];
type EditorEditOpsPreviewErrorDetails = components["schemas"]["EditorEditOpsPreviewErrorDetails"];
type EditorEditOpsOpOutput =
  | components["schemas"]["EditorEditOpsInsertOp-Output"]
  | components["schemas"]["EditorEditOpsReplaceOp-Output"]
  | components["schemas"]["EditorEditOpsDeleteOp-Output"]
  | components["schemas"]["EditorEditOpsPatchOp"];

type EditOpsDiffItem = {
  virtualFileId: VirtualFileId;
  beforeText: string;
  afterText: string;
};

type EditOpsProposal = {
  message: string;
  assistantMessage: string;
  ops: EditorEditOpsOpOutput[];
  activeFile: VirtualFileId;
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
  correlationId: string | null;
  createdAt: string;
};

type EditOpsPanelState = {
  proposal: EditOpsProposal | null;
  diffItems: EditOpsDiffItem[];
  previewMeta: EditorEditOpsPreviewMeta | null;
  previewErrorDetails: EditorEditOpsPreviewErrorDetails | null;
  previewError: string | null;
  applyError: string | null;
  undoError: string | null;
  canApply: boolean;
  applyDisabledReason: string | null;
  canUndo: boolean;
  undoDisabledReason: string | null;
  canRedo: boolean;
  redoDisabledReason: string | null;
  aiStatus: "applied" | "undone" | null;
  aiAppliedAt: string | null;
  isApplying: boolean;
  requiresConfirmation: boolean;
  confirmationAccepted: boolean;
};

type BuildPanelStateParams = {
  proposal: EditOpsProposal | null;
  diffItems: EditOpsDiffItem[];
  previewMeta: EditorEditOpsPreviewMeta | null;
  previewErrorDetails: EditorEditOpsPreviewErrorDetails | null;
  previewError: string | null;
  applyError: string | null;
  undoError: string | null;
  canApply: boolean;
  applyDisabledReason: string | null;
  canUndo: boolean;
  undoDisabledReason: string | null;
  canRedo: boolean;
  redoDisabledReason: string | null;
  lastApplied: AppliedEditOpsSnapshot | null;
  aiPosition: "after" | "before";
  isApplying: boolean;
  requiresConfirmation: boolean;
  confirmationAccepted: boolean;
};

export function buildEditOpsPanelState(params: BuildPanelStateParams): EditOpsPanelState {
  return {
    proposal: params.proposal,
    diffItems: params.diffItems,
    previewMeta: params.previewMeta,
    previewError: params.previewError,
    previewErrorDetails: params.previewErrorDetails,
    applyError: params.applyError,
    undoError: params.undoError,
    canApply: params.canApply,
    applyDisabledReason: params.applyDisabledReason,
    canUndo: params.canUndo,
    undoDisabledReason: params.undoDisabledReason,
    canRedo: params.canRedo,
    redoDisabledReason: params.redoDisabledReason,
    aiStatus: params.lastApplied ? (params.aiPosition === "after" ? "applied" : "undone") : null,
    aiAppliedAt: params.lastApplied?.appliedAt ?? null,
    isApplying: params.isApplying,
    requiresConfirmation: params.requiresConfirmation,
    confirmationAccepted: params.confirmationAccepted,
  };
}

export type {
  EditOpsDiffItem,
  EditOpsPanelState,
  EditOpsProposal,
  EditorEditOpsCursor,
  EditorEditOpsOpOutput,
  EditorEditOpsPreviewErrorDetails,
  EditorEditOpsPreviewMeta,
  EditorEditOpsSelection,
};
