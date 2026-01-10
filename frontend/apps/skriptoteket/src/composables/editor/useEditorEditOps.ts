import type { EditorView } from "@codemirror/view";
import { computed, onScopeDispose, ref, watch, type Ref } from "vue";

import { apiFetch, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import {
  virtualFileTextFromEditorFields,
  type VirtualFileId,
  type VirtualFileTextMap,
} from "./virtualFiles";

type EditorEditOpsResponse = components["schemas"]["EditorEditOpsResponse"];
type EditorEditOpsRequest = components["schemas"]["EditorEditOpsRequest"];
type EditorEditOpsSelection = components["schemas"]["EditorEditOpsSelection"];
type EditorEditOpsCursor = components["schemas"]["EditorEditOpsCursor"];
type EditorEditOpsPreviewRequest = components["schemas"]["EditorEditOpsPreviewRequest"];
type EditorEditOpsPreviewResponse = components["schemas"]["EditorEditOpsPreviewResponse"];
type EditorEditOpsApplyRequest = components["schemas"]["EditorEditOpsApplyRequest"];
type EditorEditOpsPreviewMeta = components["schemas"]["EditorEditOpsPreviewMeta"];
type EditorEditOpsPreviewErrorDetails = components["schemas"]["EditorEditOpsPreviewErrorDetails"];
type EditorEditOpsOpInput =
  | components["schemas"]["EditorEditOpsInsertOp-Input"]
  | components["schemas"]["EditorEditOpsReplaceOp-Input"]
  | components["schemas"]["EditorEditOpsDeleteOp-Input"]
  | components["schemas"]["EditorEditOpsPatchOp"];
type EditorEditOpsOpOutput =
  | components["schemas"]["EditorEditOpsInsertOp-Output"]
  | components["schemas"]["EditorEditOpsReplaceOp-Output"]
  | components["schemas"]["EditorEditOpsDeleteOp-Output"]
  | components["schemas"]["EditorEditOpsPatchOp"];

export type EditOpsDiffItem = {
  virtualFileId: VirtualFileId;
  beforeText: string;
  afterText: string;
};

export type EditOpsProposal = {
  message: string;
  assistantMessage: string;
  ops: EditorEditOpsOpOutput[];
  activeFile: VirtualFileId;
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
  createdAt: string;
};

type AppliedEditOpsSnapshot = {
  beforeFiles: VirtualFileTextMap;
  afterFiles: VirtualFileTextMap;
  afterFingerprint: string;
  appliedAt: string;
};

export type EditOpsPanelState = {
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
  hasUndoSnapshot: boolean;
  isApplying: boolean;
  requiresConfirmation: boolean;
  confirmationAccepted: boolean;
};

type UseEditorEditOpsOptions = {
  toolId: Readonly<Ref<string>>;
  isReadOnly: Readonly<Ref<boolean>>;
  editorView: Readonly<Ref<EditorView | null>>;
  fields: {
    entrypoint: Ref<string>;
    sourceCode: Ref<string>;
    settingsSchemaText: Ref<string>;
    inputSchemaText: Ref<string>;
    usageInstructions: Ref<string>;
  };
  createBeforeApplyCheckpoint: () => Promise<void> | void;
};

type EditOpsRequestResult = {
  response: EditorEditOpsResponse;
  message: string;
  activeFile: VirtualFileId;
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
};

const DEFAULT_ACTIVE_FILE: VirtualFileId = "tool.py";
const EXPLICIT_CURSOR_TTL_MS = 45_000;

function virtualFilesFingerprint(files: VirtualFileTextMap): string {
  return [
    files["entrypoint.txt"],
    files["tool.py"],
    files["settings_schema.json"],
    files["input_schema.json"],
    files["usage_instructions.md"],
  ].join("\u0000");
}

function uniqueTargetFiles(ops: EditorEditOpsOpOutput[]): VirtualFileId[] {
  const seen = new Set<VirtualFileId>();
  const ordered: VirtualFileId[] = [];
  for (const op of ops) {
    if (!seen.has(op.target_file)) {
      seen.add(op.target_file);
      ordered.push(op.target_file);
    }
  }
  return ordered;
}

function resolveSelection(params: {
  view: EditorView | null;
  includeCursorWhenNoSelection: boolean;
}): {
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
} {
  const { view, includeCursorWhenNoSelection } = params;

  if (!view) {
    return { selection: null, cursor: null };
  }

  const main = view.state.selection.main;
  if (!main.empty) {
    return {
      selection: { from: main.from, to: main.to },
      cursor: { pos: main.to },
    };
  }

  return {
    selection: null,
    cursor: includeCursorWhenNoSelection ? { pos: main.from } : null,
  };
}

function cloneVirtualFiles(files: VirtualFileTextMap): VirtualFileTextMap {
  return { ...files };
}

export function useEditorEditOps(options: UseEditorEditOpsOptions) {
  const {
    toolId,
    isReadOnly,
    editorView,
    fields,
    createBeforeApplyCheckpoint,
  } = options;

  const proposal = ref<EditOpsProposal | null>(null);
  const lastApplied = ref<AppliedEditOpsSnapshot | null>(null);
  const isRequesting = ref(false);
  const isPreviewing = ref(false);
  const isApplying = ref(false);
  const requestError = ref<string | null>(null);
  const previewError = ref<string | null>(null);
  const previewErrorDetails = ref<EditorEditOpsPreviewErrorDetails | null>(null);
  const applyError = ref<string | null>(null);
  const undoError = ref<string | null>(null);
  const previewResponse = ref<EditorEditOpsPreviewResponse | null>(null);
  const previewBaseFiles = ref<VirtualFileTextMap | null>(null);
  const confirmationAccepted = ref(false);
  const lastExplicitCursorInteractionAt = ref<number | null>(null);

  const currentFiles = computed(() =>
    virtualFileTextFromEditorFields({
      entrypoint: fields.entrypoint.value,
      sourceCode: fields.sourceCode.value,
      settingsSchemaText: fields.settingsSchemaText.value,
      inputSchemaText: fields.inputSchemaText.value,
      usageInstructions: fields.usageInstructions.value,
    }),
  );

  const currentFingerprint = computed(() => virtualFilesFingerprint(currentFiles.value));

  const hasUndoSnapshot = computed(() => lastApplied.value !== null);
  const targetFiles = computed(() => (proposal.value ? uniqueTargetFiles(proposal.value.ops) : []));

  const diffItems = computed<EditOpsDiffItem[]>(() => {
    if (!proposal.value || !previewResponse.value || !previewBaseFiles.value) return [];
    if (!previewResponse.value.ok) return [];
    const beforeFiles = previewBaseFiles.value;
    const afterFiles = previewResponse.value.after_virtual_files as unknown as VirtualFileTextMap;
    return targetFiles.value
      .filter((fileId) => beforeFiles[fileId] !== afterFiles[fileId])
      .map((fileId) => ({
        virtualFileId: fileId,
        beforeText: beforeFiles[fileId],
        afterText: afterFiles[fileId],
      }));
  });

  const hasChanges = computed(() => diffItems.value.length > 0);
  const previewMeta = computed(() => previewResponse.value?.meta ?? null);
  const requiresConfirmation = computed(() => previewMeta.value?.requires_confirmation ?? false);

  const applyDisabledReason = computed(() => {
    if (!proposal.value) return null;
    if (isReadOnly.value) return "Editorn är låst för redigering.";
    if (isPreviewing.value) return "Skapar förhandsvisning...";
    if (previewError.value) return previewError.value;
    if (!hasChanges.value) return "Inga ändringar att tillämpa.";
    if (requiresConfirmation.value && !confirmationAccepted.value) {
      return "Bekräfta att du har granskat ändringen.";
    }
    return null;
  });

  const canApply = computed(
    () =>
      Boolean(proposal.value) &&
      !isReadOnly.value &&
      !isPreviewing.value &&
      !previewError.value &&
      hasChanges.value &&
      (!requiresConfirmation.value || confirmationAccepted.value) &&
      !isApplying.value,
  );

  const undoDisabledReason = computed(() => {
    if (!lastApplied.value) return null;
    if (isReadOnly.value) return "Editorn är låst för redigering.";
    if (currentFingerprint.value !== lastApplied.value.afterFingerprint) {
      return "Ändringar har gjorts efter AI-förslaget. Återställ via lokala checkpoints.";
    }
    return null;
  });

  const canUndo = computed(
    () =>
      Boolean(lastApplied.value) &&
      !isReadOnly.value &&
      !undoDisabledReason.value &&
      !isApplying.value,
  );

  let detachExplicitListeners: (() => void) | null = null;

  function clearErrors(): void {
    requestError.value = null;
    previewError.value = null;
    previewErrorDetails.value = null;
    applyError.value = null;
    undoError.value = null;
  }

  function clearRequestError(): void {
    requestError.value = null;
  }

  function setConfirmationAccepted(nextValue: boolean): void {
    confirmationAccepted.value = nextValue;
  }

  async function loadPreview(params: {
    proposal: EditOpsProposal;
    virtualFiles: VirtualFileTextMap;
  }): Promise<EditorEditOpsPreviewResponse | null> {
    if (!toolId.value) {
      previewError.value = "Ingen editor hittades.";
      return null;
    }

    isPreviewing.value = true;
    previewError.value = null;
    previewErrorDetails.value = null;
    applyError.value = null;

    const body: EditorEditOpsPreviewRequest = {
      tool_id: toolId.value,
      active_file: params.proposal.activeFile,
      virtual_files: params.virtualFiles,
      ops: params.proposal.ops as unknown as EditorEditOpsOpInput[],
    };
    if (params.proposal.selection) {
      body.selection = params.proposal.selection;
    }
    if (params.proposal.cursor) {
      body.cursor = params.proposal.cursor;
    }

    try {
      const response = await apiFetch<EditorEditOpsPreviewResponse>("/api/v1/editor/edit-ops/preview", {
        method: "POST",
        body,
      });

      previewResponse.value = response;
      previewBaseFiles.value = cloneVirtualFiles(params.virtualFiles);

      const errors = response.errors ?? [];
      const details = response.error_details ?? [];
      previewError.value = response.ok ? null : (errors[0] ?? "Förhandsvisningen misslyckades. Regenerera.");
      previewErrorDetails.value = details[0] ?? null;
      confirmationAccepted.value = false;

      return response;
    } catch (error: unknown) {
      previewResponse.value = null;
      previewBaseFiles.value = null;
      confirmationAccepted.value = false;
      if (isApiError(error)) {
        previewError.value = error.message;
      } else if (error instanceof Error) {
        previewError.value = error.message;
      } else {
        previewError.value = "Det gick inte att förhandsvisa förslaget.";
      }
      return null;
    } finally {
      isPreviewing.value = false;
    }
  }

  async function refreshPreview(): Promise<EditorEditOpsPreviewResponse | null> {
    if (!proposal.value) {
      previewResponse.value = null;
      previewBaseFiles.value = null;
      previewError.value = null;
      previewErrorDetails.value = null;
      confirmationAccepted.value = false;
      return null;
    }

    return await loadPreview({ proposal: proposal.value, virtualFiles: currentFiles.value });
  }

  function applyVirtualFiles(nextFiles: VirtualFileTextMap): void {
    fields.entrypoint.value = nextFiles["entrypoint.txt"];
    fields.sourceCode.value = nextFiles["tool.py"];
    fields.settingsSchemaText.value = nextFiles["settings_schema.json"];
    fields.inputSchemaText.value = nextFiles["input_schema.json"];
    fields.usageInstructions.value = nextFiles["usage_instructions.md"];
  }

  async function requestEditOps(message: string): Promise<EditOpsRequestResult | null> {
    const trimmed = message.trim();
    if (!trimmed) {
      requestError.value = "Skriv ett meddelande först.";
      return null;
    }
    if (!toolId.value) {
      requestError.value = "Ingen editor hittades.";
      return null;
    }

    clearErrors();
    previewResponse.value = null;
    previewBaseFiles.value = null;
    confirmationAccepted.value = false;
    isRequesting.value = true;

    const hasExplicitCursor =
      lastExplicitCursorInteractionAt.value !== null &&
      Date.now() - lastExplicitCursorInteractionAt.value <= EXPLICIT_CURSOR_TTL_MS;

    const { selection, cursor } = resolveSelection({
      view: editorView.value,
      includeCursorWhenNoSelection: hasExplicitCursor,
    });
    const activeFile = DEFAULT_ACTIVE_FILE;
    const virtualFiles = currentFiles.value;

    const body: EditorEditOpsRequest = {
      tool_id: toolId.value,
      message: trimmed,
      active_file: activeFile,
      virtual_files: virtualFiles,
    };
    if (selection) {
      body.selection = selection;
    }
    if (cursor) {
      body.cursor = cursor;
    }

    try {
      const response = await apiFetch<EditorEditOpsResponse>("/api/v1/editor/edit-ops", {
        method: "POST",
        body,
      });

      if (response.enabled && response.ops.length > 0) {
        const nextProposal: EditOpsProposal = {
          message: trimmed,
          assistantMessage: response.assistant_message,
          ops: response.ops as unknown as EditorEditOpsOpOutput[],
          activeFile,
          selection,
          cursor,
          createdAt: new Date().toISOString(),
        };
        proposal.value = nextProposal;
        await loadPreview({ proposal: nextProposal, virtualFiles });
      } else {
        proposal.value = null;
        previewResponse.value = null;
        previewBaseFiles.value = null;
        previewError.value = null;
        previewErrorDetails.value = null;
        confirmationAccepted.value = false;
      }

      return { response, message: trimmed, activeFile, selection, cursor };
    } catch (error: unknown) {
      proposal.value = null;
      previewResponse.value = null;
      previewBaseFiles.value = null;
      previewErrorDetails.value = null;
      confirmationAccepted.value = false;
      if (isApiError(error)) {
        requestError.value = error.message;
      } else if (error instanceof Error) {
        requestError.value = error.message;
      } else {
        requestError.value = "Det gick inte att skapa ett AI-förslag.";
      }
      return null;
    } finally {
      isRequesting.value = false;
    }
  }

  async function applyProposal(): Promise<boolean> {
    applyError.value = null;
    undoError.value = null;

    if (!proposal.value) return false;
    if (isReadOnly.value) {
      applyError.value = "Editorn är låst för redigering.";
      return false;
    }

    if (!previewResponse.value || previewError.value) {
      await refreshPreview();
    }

    if (!previewResponse.value) {
      applyError.value = previewError.value ?? "Förhandsvisningen saknas. Försök igen.";
      return false;
    }

    if (!previewResponse.value.ok) {
      const errors = previewResponse.value.errors ?? [];
      applyError.value = errors[0] ?? "Förhandsvisningen misslyckades. Regenerera.";
      return false;
    }

    if (!hasChanges.value) {
      applyError.value = "Inga ändringar att tillämpa.";
      return false;
    }

    if (previewResponse.value.meta.requires_confirmation && !confirmationAccepted.value) {
      applyError.value = "Bekräfta att du har granskat ändringen innan du tillämpar.";
      return false;
    }

    const proposalValue = proposal.value;
    const beforeFiles = cloneVirtualFiles(currentFiles.value);

    isApplying.value = true;
    try {
      const body: EditorEditOpsApplyRequest = {
        tool_id: toolId.value,
        active_file: proposalValue.activeFile,
        virtual_files: beforeFiles,
        ops: proposalValue.ops as unknown as EditorEditOpsOpInput[],
        base_hash: previewResponse.value.meta.base_hash,
        patch_id: previewResponse.value.meta.patch_id,
      };
      if (proposalValue.selection) {
        body.selection = proposalValue.selection;
      }
      if (proposalValue.cursor) {
        body.cursor = proposalValue.cursor;
      }

      const response = await apiFetch<EditorEditOpsPreviewResponse>("/api/v1/editor/edit-ops/apply", {
        method: "POST",
        body,
      });

      if (!response.ok) {
        const errors = response.errors ?? [];
        const errorMessage = errors[0] ?? "Förslaget kunde inte tillämpas. Regenerera.";
        applyError.value = null;
        previewResponse.value = response;
        previewBaseFiles.value = cloneVirtualFiles(beforeFiles);
        previewError.value = errorMessage;
        previewErrorDetails.value = (response.error_details ?? [])[0] ?? null;
        confirmationAccepted.value = false;
        return false;
      }

      await createBeforeApplyCheckpoint();
      const afterFiles = response.after_virtual_files as unknown as VirtualFileTextMap;
      applyVirtualFiles(afterFiles);
      lastApplied.value = {
        beforeFiles,
        afterFiles,
        afterFingerprint: virtualFilesFingerprint(afterFiles),
        appliedAt: new Date().toISOString(),
      };
      proposal.value = null;
      previewResponse.value = null;
      previewBaseFiles.value = null;
      previewError.value = null;
      previewErrorDetails.value = null;
      confirmationAccepted.value = false;
      return true;
    } catch (error: unknown) {
      if (isApiError(error) && error.status === 409) {
        confirmationAccepted.value = false;
        const message = error.message;
        await refreshPreview();
        applyError.value = message;
        return false;
      }

      applyError.value = isApiError(error)
        ? error.message
        : error instanceof Error
            ? error.message
            : "Det gick inte att tillämpa förslaget.";
      return false;
    } finally {
      isApplying.value = false;
    }
  }

  function discardProposal(): void {
    proposal.value = null;
    previewResponse.value = null;
    previewBaseFiles.value = null;
    previewError.value = null;
    previewErrorDetails.value = null;
    applyError.value = null;
    confirmationAccepted.value = false;
  }

  function undoLastApply(): boolean {
    undoError.value = null;
    if (!lastApplied.value) return false;
    if (!canUndo.value) {
      undoError.value = undoDisabledReason.value ?? "Det gick inte att ångra.";
      return false;
    }

    applyVirtualFiles(lastApplied.value.beforeFiles);
    lastApplied.value = null;
    return true;
  }

  watch(
    () => currentFingerprint.value,
    () => {
      if (!lastApplied.value) return;
      if (currentFingerprint.value !== lastApplied.value.afterFingerprint && undoError.value) {
        undoError.value = null;
      }
    },
  );

  onScopeDispose(() => {
    if (detachExplicitListeners) {
      detachExplicitListeners();
      detachExplicitListeners = null;
    }
  });

  watch(
    () => editorView.value,
    (view) => {
      if (detachExplicitListeners) {
        detachExplicitListeners();
        detachExplicitListeners = null;
      }

      if (!view) {
        lastExplicitCursorInteractionAt.value = null;
        return;
      }

      const markExplicit = () => {
        lastExplicitCursorInteractionAt.value = Date.now();
      };

      view.dom.addEventListener("pointerdown", markExplicit);
      view.dom.addEventListener("keydown", markExplicit);

      detachExplicitListeners = () => {
        view.dom.removeEventListener("pointerdown", markExplicit);
        view.dom.removeEventListener("keydown", markExplicit);
      };
    },
    { immediate: true },
  );

  const panelState = computed<EditOpsPanelState>(() => ({
    proposal: proposal.value,
    diffItems: diffItems.value,
    previewMeta: previewMeta.value,
    previewError: previewError.value,
    previewErrorDetails: previewErrorDetails.value,
    applyError: applyError.value,
    undoError: undoError.value,
    canApply: canApply.value,
    applyDisabledReason: applyDisabledReason.value,
    canUndo: canUndo.value,
    undoDisabledReason: undoDisabledReason.value,
    hasUndoSnapshot: hasUndoSnapshot.value,
    isApplying: isApplying.value,
    requiresConfirmation: requiresConfirmation.value,
    confirmationAccepted: confirmationAccepted.value,
  }));

  return {
    proposal,
    isRequesting,
    requestError,
    clearRequestError,
    panelState,
    diffItems,
    previewError,
    previewErrorDetails,
    previewMeta,
    applyError,
    undoError,
    canApply,
    applyDisabledReason,
    canUndo,
    undoDisabledReason,
    hasUndoSnapshot,
    isApplying,
    requiresConfirmation,
    confirmationAccepted,
    setConfirmationAccepted,
    requestEditOps,
    applyProposal,
    discardProposal,
    undoLastApply,
  };
}
