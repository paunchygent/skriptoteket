import { apiFetch } from "../../../api/client";
import type { components } from "../../../api/openapi";
import type { VirtualFileId, VirtualFileTextMap } from "../virtualFiles";

type EditorEditOpsResponse = components["schemas"]["EditorEditOpsResponse"];
type EditorEditOpsRequest = components["schemas"]["EditorEditOpsRequest"];
type EditorEditOpsSelection = components["schemas"]["EditorEditOpsSelection"];
type EditorEditOpsCursor = components["schemas"]["EditorEditOpsCursor"];
type EditorEditOpsPreviewRequest = components["schemas"]["EditorEditOpsPreviewRequest"];
type EditorEditOpsPreviewResponse = components["schemas"]["EditorEditOpsPreviewResponse"];
type EditorEditOpsApplyRequest = components["schemas"]["EditorEditOpsApplyRequest"];
type EditorEditOpsOpInput =
  | components["schemas"]["EditorEditOpsInsertOp-Input"]
  | components["schemas"]["EditorEditOpsReplaceOp-Input"]
  | components["schemas"]["EditorEditOpsDeleteOp-Input"]
  | components["schemas"]["EditorEditOpsPatchOp"];

type RequestEditOpsParams = {
  toolId: string;
  message: string;
  allowRemoteFallback: boolean;
  activeFile: VirtualFileId;
  virtualFiles: VirtualFileTextMap;
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
  correlationId: string;
};

type PreviewEditOpsParams = {
  toolId: string;
  activeFile: VirtualFileId;
  virtualFiles: VirtualFileTextMap;
  ops: EditorEditOpsOpInput[];
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
  correlationId: string;
};

type ApplyEditOpsParams = {
  toolId: string;
  activeFile: VirtualFileId;
  virtualFiles: VirtualFileTextMap;
  ops: EditorEditOpsOpInput[];
  baseHash: string;
  patchId: string;
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
  correlationId: string;
};

export async function requestEditOps(params: RequestEditOpsParams): Promise<EditorEditOpsResponse> {
  const body: EditorEditOpsRequest = {
    tool_id: params.toolId,
    message: params.message,
    allow_remote_fallback: params.allowRemoteFallback,
    active_file: params.activeFile,
    virtual_files: params.virtualFiles,
  };
  if (params.selection) {
    body.selection = params.selection;
  }
  if (params.cursor) {
    body.cursor = params.cursor;
  }

  return await apiFetch<EditorEditOpsResponse>("/api/v1/editor/edit-ops", {
    method: "POST",
    body,
    headers: { "X-Correlation-ID": params.correlationId },
  });
}

export async function previewEditOps(params: PreviewEditOpsParams): Promise<EditorEditOpsPreviewResponse> {
  const body: EditorEditOpsPreviewRequest = {
    tool_id: params.toolId,
    active_file: params.activeFile,
    virtual_files: params.virtualFiles,
    ops: params.ops,
  };
  if (params.selection) {
    body.selection = params.selection;
  }
  if (params.cursor) {
    body.cursor = params.cursor;
  }

  return await apiFetch<EditorEditOpsPreviewResponse>("/api/v1/editor/edit-ops/preview", {
    method: "POST",
    body,
    headers: { "X-Correlation-ID": params.correlationId },
  });
}

export async function applyEditOps(params: ApplyEditOpsParams): Promise<EditorEditOpsPreviewResponse> {
  const body: EditorEditOpsApplyRequest = {
    tool_id: params.toolId,
    active_file: params.activeFile,
    virtual_files: params.virtualFiles,
    ops: params.ops,
    base_hash: params.baseHash,
    patch_id: params.patchId,
  };
  if (params.selection) {
    body.selection = params.selection;
  }
  if (params.cursor) {
    body.cursor = params.cursor;
  }

  return await apiFetch<EditorEditOpsPreviewResponse>("/api/v1/editor/edit-ops/apply", {
    method: "POST",
    body,
    headers: { "X-Correlation-ID": params.correlationId },
  });
}

export type {
  EditorEditOpsApplyRequest,
  EditorEditOpsCursor,
  EditorEditOpsOpInput,
  EditorEditOpsPreviewResponse,
  EditorEditOpsRequest,
  EditorEditOpsResponse,
  EditorEditOpsSelection,
};
