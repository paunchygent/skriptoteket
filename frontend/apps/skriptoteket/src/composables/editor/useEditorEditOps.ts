import type { EditorView } from "@codemirror/view";
import { computed, onScopeDispose, ref, watch, type Ref } from "vue";

import { apiFetch, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import type { UiNotifier } from "../notify";
import { applyEditOpsToVirtualFiles, type EditOpsApplyResult, type EditOpsDiffItem } from "./editOps";
import {
  virtualFileTextFromEditorFields,
  type VirtualFileId,
  type VirtualFileTextMap,
} from "./virtualFiles";

type EditorEditOpsResponse = components["schemas"]["EditorEditOpsResponse"];
type EditorEditOpsRequest = components["schemas"]["EditorEditOpsRequest"];
type EditorEditOpsSelection = components["schemas"]["EditorEditOpsSelection"];
type EditorEditOpsCursor = components["schemas"]["EditorEditOpsCursor"];
type EditorEditOpsOp = components["schemas"]["EditorEditOpsOp"];

export type EditOpsProposal = {
  message: string;
  assistantMessage: string;
  ops: EditorEditOpsOp[];
  baseFingerprints: Record<VirtualFileId, string>;
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
  isStale: boolean;
  staleFiles: VirtualFileId[];
  previewError: string | null;
  applyError: string | null;
  undoError: string | null;
  canApply: boolean;
  applyDisabledReason: string | null;
  canUndo: boolean;
  undoDisabledReason: string | null;
  hasUndoSnapshot: boolean;
  isApplying: boolean;
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
  notify: UiNotifier;
  fingerprint?: (text: string) => Promise<string>;
};

type EditOpsRequestResult = {
  response: EditorEditOpsResponse;
  message: string;
  activeFile: VirtualFileId;
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
};

const DEFAULT_ACTIVE_FILE: VirtualFileId = "tool.py";

function virtualFilesFingerprint(files: VirtualFileTextMap): string {
  return [
    files["entrypoint.txt"],
    files["tool.py"],
    files["settings_schema.json"],
    files["input_schema.json"],
    files["usage_instructions.md"],
  ].join("\u0000");
}

function uniqueTargetFiles(ops: EditorEditOpsOp[]): VirtualFileId[] {
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

async function sha256Fingerprint(text: string): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error("WebCrypto är inte tillgängligt.");
  }
  const data = new TextEncoder().encode(text);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", data);
  const hash = Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
  return `sha256:${hash}`;
}

function resolveSelection(view: EditorView | null): {
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
} {
  if (!view) {
    return { selection: null, cursor: null };
  }

  const main = view.state.selection.main;
  if (!main.empty) {
    return {
      selection: { from: main.from, to: main.to },
      cursor: null,
    };
  }

  return {
    selection: null,
    cursor: { pos: main.from },
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
    notify,
    fingerprint = sha256Fingerprint,
  } = options;

  const proposal = ref<EditOpsProposal | null>(null);
  const lastApplied = ref<AppliedEditOpsSnapshot | null>(null);
  const isRequesting = ref(false);
  const isApplying = ref(false);
  const requestError = ref<string | null>(null);
  const previewError = ref<string | null>(null);
  const applyError = ref<string | null>(null);
  const undoError = ref<string | null>(null);
  const staleFiles = ref<VirtualFileId[]>([]);
  const previewResult = ref<EditOpsApplyResult | null>(null);

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
  const isStale = computed(() => staleFiles.value.length > 0);
  const targetFiles = computed(() => (proposal.value ? uniqueTargetFiles(proposal.value.ops) : []));
  const hasChanges = computed(() => (previewResult.value?.changedFiles.length ?? 0) > 0);

  const diffItems = computed<EditOpsDiffItem[]>(() => {
    if (!proposal.value || !previewResult.value) return [];
    const beforeFiles = currentFiles.value;
    const afterFiles = previewResult.value.nextFiles;
    return targetFiles.value
      .filter((fileId) => beforeFiles[fileId] !== afterFiles[fileId])
      .map((fileId) => ({
        virtualFileId: fileId,
        beforeText: beforeFiles[fileId],
        afterText: afterFiles[fileId],
      }));
  });

  const applyDisabledReason = computed(() => {
    if (!proposal.value) return null;
    if (isReadOnly.value) return "Editorn är låst för redigering.";
    if (isStale.value) return "Förslaget är utdaterat. Regenerera.";
    if (previewError.value) return previewError.value;
    if (!hasChanges.value) return "Inga ändringar att tillämpa.";
    return null;
  });

  const canApply = computed(
    () =>
      Boolean(proposal.value) &&
      !isReadOnly.value &&
      !isStale.value &&
      !previewError.value &&
      hasChanges.value &&
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

  let staleTimer: ReturnType<typeof setTimeout> | null = null;
  let staleToken = 0;

  function clearErrors(): void {
    requestError.value = null;
    previewError.value = null;
    applyError.value = null;
    undoError.value = null;
  }

  function updatePreview(nextFiles: VirtualFileTextMap, nextProposal: EditOpsProposal | null): void {
    if (!nextProposal) {
      previewResult.value = null;
      previewError.value = null;
      return;
    }

    if (isStale.value) {
      previewResult.value = null;
      previewError.value = null;
      return;
    }

    const result = applyEditOpsToVirtualFiles({
      virtualFiles: nextFiles,
      ops: nextProposal.ops,
      selection: nextProposal.selection,
      cursor: nextProposal.cursor,
      activeFile: nextProposal.activeFile,
    });
    previewResult.value = result;
    previewError.value = result.errors[0] ?? null;
  }

  async function checkStaleNow(): Promise<void> {
    staleToken += 1;
    const token = staleToken;
    if (!proposal.value) {
      staleFiles.value = [];
      previewResult.value = null;
      previewError.value = null;
      return;
    }

    const proposalValue = proposal.value;
    const files = currentFiles.value;
    const targets = targetFiles.value;

    if (targets.length === 0) {
      staleFiles.value = [];
      updatePreview(files, proposalValue);
      return;
    }

    try {
      const hashes = await Promise.all(targets.map((fileId) => fingerprint(files[fileId])));
      if (token !== staleToken) return;

      const mismatched = targets.filter(
        (fileId, index) => hashes[index] !== proposalValue.baseFingerprints[fileId],
      );
      staleFiles.value = mismatched;
      updatePreview(files, proposalValue);
    } catch (error: unknown) {
      if (token !== staleToken) return;
      staleFiles.value = [...targets];
      previewError.value = "Kunde inte verifiera filernas status.";
      notify.warning(
        error instanceof Error
          ? error.message
          : "Kunde inte verifiera filernas status.",
      );
    }
  }

  function scheduleStaleCheck(): void {
    if (staleTimer) {
      clearTimeout(staleTimer);
    }
    staleTimer = setTimeout(() => {
      staleTimer = null;
      void checkStaleNow();
    }, 250);
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
    isRequesting.value = true;

    const { selection, cursor } = resolveSelection(editorView.value);
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
        proposal.value = {
          message: trimmed,
          assistantMessage: response.assistant_message,
          ops: response.ops,
          baseFingerprints: response.base_fingerprints as Record<VirtualFileId, string>,
          activeFile,
          selection,
          cursor,
          createdAt: new Date().toISOString(),
        };
      } else {
        proposal.value = null;
      }

      scheduleStaleCheck();

      return { response, message: trimmed, activeFile, selection, cursor };
    } catch (error: unknown) {
      proposal.value = null;
      if (isApiError(error)) {
        requestError.value = error.message;
        notify.failure(error.message);
      } else if (error instanceof Error) {
        requestError.value = error.message;
        notify.failure(error.message);
      } else {
        requestError.value = "Det gick inte att skapa ett AI-förslag.";
        notify.failure(requestError.value);
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

    await checkStaleNow();
    if (isStale.value) {
      applyError.value = "Förslaget är utdaterat. Regenerera.";
      return false;
    }

    const result = applyEditOpsToVirtualFiles({
      virtualFiles: currentFiles.value,
      ops: proposal.value.ops,
      selection: proposal.value.selection,
      cursor: proposal.value.cursor,
      activeFile: proposal.value.activeFile,
    });

    if (result.errors.length > 0) {
      applyError.value = result.errors[0];
      return false;
    }
    if (result.changedFiles.length === 0) {
      applyError.value = "Inga ändringar att tillämpa.";
      return false;
    }

    const beforeFiles = cloneVirtualFiles(currentFiles.value);

    isApplying.value = true;
    try {
      await createBeforeApplyCheckpoint();
      applyVirtualFiles(result.nextFiles);
      lastApplied.value = {
        beforeFiles,
        afterFiles: result.nextFiles,
        afterFingerprint: virtualFilesFingerprint(result.nextFiles),
        appliedAt: new Date().toISOString(),
      };
      proposal.value = null;
      previewResult.value = null;
      previewError.value = null;
      staleFiles.value = [];
      return true;
    } catch (error: unknown) {
      applyError.value =
        error instanceof Error ? error.message : "Det gick inte att tillämpa förslaget.";
      notify.failure(applyError.value);
      return false;
    } finally {
      isApplying.value = false;
    }
  }

  function discardProposal(): void {
    proposal.value = null;
    previewResult.value = null;
    previewError.value = null;
    applyError.value = null;
    staleFiles.value = [];
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
    () => [proposal.value, currentFiles.value] as const,
    () => {
      if (!proposal.value) {
        previewResult.value = null;
        previewError.value = null;
        staleFiles.value = [];
        return;
      }
      scheduleStaleCheck();
    },
    { immediate: true },
  );

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
    if (staleTimer) {
      clearTimeout(staleTimer);
    }
  });

  const panelState = computed<EditOpsPanelState>(() => ({
    proposal: proposal.value,
    diffItems: diffItems.value,
    isStale: isStale.value,
    staleFiles: staleFiles.value,
    previewError: previewError.value,
    applyError: applyError.value,
    undoError: undoError.value,
    canApply: canApply.value,
    applyDisabledReason: applyDisabledReason.value,
    canUndo: canUndo.value,
    undoDisabledReason: undoDisabledReason.value,
    hasUndoSnapshot: hasUndoSnapshot.value,
    isApplying: isApplying.value,
  }));

  return {
    proposal,
    isRequesting,
    requestError,
    panelState,
    diffItems,
    isStale,
    staleFiles,
    previewError,
    applyError,
    undoError,
    canApply,
    applyDisabledReason,
    canUndo,
    undoDisabledReason,
    hasUndoSnapshot,
    isApplying,
    requestEditOps,
    applyProposal,
    discardProposal,
    undoLastApply,
  };
}
