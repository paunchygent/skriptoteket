import type { EditorView } from "@codemirror/view";
import type { components } from "../../api/openapi";
import type { EditorChatMessage } from "../../composables/editor/chat/editorChatTypes";
import type { EditOpsPanelState } from "../../composables/editor/editOps/editOpsState";
import type { EditorCompareTarget } from "../../composables/editor/useEditorCompareState";
import type { WorkingCopyProvider } from "../../composables/editor/useEditorCompareData";
import type { EditorWorkingCopyCheckpointSummary } from "../../composables/editor/useEditorWorkingCopy";
import type { SchemaIssuesBySchema } from "../../composables/editor/useEditorSchemaValidation";
import type { SubmitReviewTooltip } from "../../composables/editor/useEditorWorkflowActions";
import type { VirtualFileId } from "../../composables/editor/virtualFiles";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];
type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];
type MaintainerSummary = components["schemas"]["MaintainerSummary"];
type CreateDraftVersionRequest = components["schemas"]["CreateDraftVersionRequest"];
type ToolInputSchema = NonNullable<CreateDraftVersionRequest["input_schema"]>;
type ToolSettingsSchema = NonNullable<CreateDraftVersionRequest["settings_schema"]>;

type EditorWorkspacePanelProps = {
  toolId: string;
  versions: EditorVersionSummary[];
  selectedVersion: EditorVersionSummary | null;
  entrypointOptions: string[];

  changeSummary: string;
  entrypoint: string;
  sourceCode: string;
  settingsSchemaText: string;
  inputSchemaText: string;
  settingsSchema: ToolSettingsSchema | null;
  settingsSchemaError: string | null;
  inputSchema: ToolInputSchema;
  inputSchemaError: string | null;
  schemaIssuesBySchema: SchemaIssuesBySchema;
  hasBlockingSchemaIssues: boolean;
  isSchemaValidating: boolean;
  schemaValidationError: string | null;
  validateSchemasNow: () => Promise<boolean>;
  usageInstructions: string;

  metadataTitle: string;
  metadataSlug: string;
  metadataSummary: string;
  slugError: string | null;
  statusLine: string;
  isTitleSaving: boolean;
  isSummarySaving: boolean;

  selectedProfessionIds: string[];
  selectedCategoryIds: string[];

  canEditTaxonomy: boolean;
  canEditMaintainers: boolean;
  canEditSlug: boolean;
  canRollbackVersions: boolean;
  isWorkflowSubmitting: boolean;

  isSaving: boolean;
  saveLabel: string;
  saveTitle: string;
  openCompareTitle: string;
  activeMode: "source" | "diff" | "metadata" | "test";
  canEnterDiff: boolean;
  hasDirtyChanges: boolean;
  isReadOnly: boolean;

  isHistoryDrawerOpen: boolean;
  isChatDrawerOpen: boolean;
  isChatCollapsed: boolean;
  allowRemoteFallback: boolean;
  canCompareVersions: boolean;
  lockBadgeLabel: string | null;
  lockBadgeTone: "success" | "neutral";
  canSubmitReview: boolean;
  submitReviewTooltip: SubmitReviewTooltip | null;
  canPublish: boolean;
  canRequestChanges: boolean;
  canRollback: boolean;

  professions: ProfessionItem[];
  categories: CategoryItem[];
  taxonomyError: string | null;
  isTaxonomyLoading: boolean;
  isSavingAllMetadata: boolean;

  maintainers: MaintainerSummary[];
  ownerUserId: string | null;
  isMaintainersLoading: boolean;
  isMaintainersSaving: boolean;
  maintainersError: string | null;

  compareTarget: EditorCompareTarget | null;
  compareActiveFileId: VirtualFileId | null;
  canCompareWorkingCopy: boolean;
  workingCopyProvider?: WorkingCopyProvider | null;
  localCheckpoints: EditorWorkingCopyCheckpointSummary[];
  pinnedCheckpointCount: number;
  pinnedCheckpointLimit: number;
  isCheckpointBusy: boolean;

  chatMessages: EditorChatMessage[];
  chatIsStreaming: boolean;
  chatDisabledMessage: string | null;
  chatError: string | null;
  chatNoticeMessage: string | null;
  chatNoticeVariant: "info" | "warning";
  editOpsRequestError: string | null;
  editOpsDisabledMessage: string | null;
  editOpsClearDraftToken: number;

  editOpsState: EditOpsPanelState;
  isEditOpsRequesting: boolean;
  isEditOpsSlow: boolean;
};

type EditorWorkspacePanelEmits = {
  (event: "save"): void;
  (event: "openHistoryDrawer"): void;
  (event: "workflowAction", action: "submit_review" | "publish" | "request_changes" | "rollback"): void;
  (event: "selectMode", mode: "source" | "diff" | "metadata" | "test"): void;
  (event: "closeDrawer"): void;
  (event: "toggleChatCollapsed"): void;
  (event: "selectHistoryVersion", versionId: string): void;
  (event: "compareVersion", versionId: string): void;
  (event: "rollbackVersion", versionId: string): void;
  (event: "saveAllMetadata"): void;
  (event: "suggestSlugFromTitle"): void;
  (event: "addMaintainer", email: string): void;
  (event: "removeMaintainer", userId: string): void;
  (event: "update:changeSummary", value: string): void;
  (event: "update:entrypoint", value: string): void;
  (event: "update:sourceCode", value: string): void;
  (event: "update:settingsSchemaText", value: string): void;
  (event: "update:inputSchemaText", value: string): void;
  (event: "update:usageInstructions", value: string): void;
  (event: "update:metadataTitle", value: string): void;
  (event: "update:metadataSlug", value: string): void;
  (event: "update:metadataSummary", value: string): void;
  (event: "commitTitle"): void;
  (event: "commitSummary"): void;
  (event: "update:slugError", value: string | null): void;
  (event: "update:taxonomyError", value: string | null): void;
  (event: "update:maintainersError", value: string | null): void;
  (event: "update:selectedProfessionIds", value: string[]): void;
  (event: "update:selectedCategoryIds", value: string[]): void;
  (event: "editorViewReady", value: EditorView | null): void;
  (event: "closeCompare"): void;
  (event: "update:compareTarget", value: EditorCompareTarget | null): void;
  (event: "update:compareActiveFileId", value: VirtualFileId): void;
  (event: "createCheckpoint", label: string): void;
  (event: "restoreCheckpoint", checkpointId: string): void;
  (event: "removeCheckpoint", checkpointId: string): void;
  (event: "restoreServerVersion"): void;
  (event: "sendChatMessage", message: string): void;
  (event: "cancelChatStream"): void;
  (event: "clearChat"): void;
  (event: "clearChatError"): void;
  (event: "clearChatDisabled"): void;
  (event: "clearChatNotice"): void;
  (event: "setAllowRemoteFallback", value: boolean): void;
  (event: "requestEditOps", message: string): void;
  (event: "clearEditOpsError"): void;
  (event: "clearEditOpsDisabled"): void;
  (event: "setEditOpsConfirmationAccepted", value: boolean): void;
  (event: "applyEditOps"): void;
  (event: "discardEditOps"): void;
  (event: "regenerateEditOps"): void;
  (event: "undoEditOps"): void;
  (event: "redoEditOps"): void;
};

export type { EditorWorkspacePanelEmits, EditorWorkspacePanelProps };
