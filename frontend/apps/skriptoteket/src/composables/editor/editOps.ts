import type { components } from "../../api/openapi";
import type { VirtualFileId, VirtualFileTextMap } from "./virtualFiles";

type EditorEditOpsOp = components["schemas"]["EditorEditOpsOp"];
type EditorEditOpsSelection = components["schemas"]["EditorEditOpsSelection"];
type EditorEditOpsCursor = components["schemas"]["EditorEditOpsCursor"];

export type EditOpsDiffItem = {
  virtualFileId: VirtualFileId;
  beforeText: string;
  afterText: string;
};

export type EditOpsApplyResult = {
  nextFiles: VirtualFileTextMap;
  errors: string[];
  changedFiles: VirtualFileId[];
};

type ResolvedTarget = {
  fileId: VirtualFileId;
  from: number;
  to: number;
  op: EditorEditOpsOp["op"];
  content: string | null;
  targetKind: EditorEditOpsOp["target"]["kind"];
};

function invalidTargetMessage(targetKind: string, op: EditorEditOpsOp["op"]): string {
  return `AI-förslaget använder ${op} med ${targetKind}-mål som inte stöds.`;
}

function normalizeRange(from: number, to: number): { from: number; to: number } | null {
  if (from < 0 || to < 0) return null;
  if (from > to) return null;
  return { from, to };
}

function resolveTarget(params: {
  op: EditorEditOpsOp;
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
  activeFile: VirtualFileId;
  currentText: string;
}): { resolved: ResolvedTarget | null; error: string | null } {
  const { op, selection, cursor, activeFile, currentText } = params;
  const targetKind = op.target.kind;
  const fileId = op.target_file;
  const textLength = currentText.length;

  if (targetKind === "selection") {
    if (!selection) {
      return { resolved: null, error: "AI-förslaget använder markering men ingen markering finns." };
    }
    if (fileId !== activeFile) {
      return {
        resolved: null,
        error: "AI-förslaget använder markering i en annan fil än den aktiva.",
      };
    }
    const range = normalizeRange(selection.from, selection.to);
    if (!range || range.to > textLength) {
      return { resolved: null, error: "AI-förslagets markering matchar inte filens innehåll." };
    }
    return {
      resolved: {
        fileId,
        from: range.from,
        to: range.to,
        op: op.op,
        content: op.content ?? null,
        targetKind,
      },
      error: null,
    };
  }

  if (targetKind === "cursor") {
    if (!cursor) {
      return { resolved: null, error: "AI-förslaget använder markör men ingen markör finns." };
    }
    if (fileId !== activeFile) {
      return {
        resolved: null,
        error: "AI-förslaget använder markör i en annan fil än den aktiva.",
      };
    }
    if (cursor.pos < 0 || cursor.pos > textLength) {
      return { resolved: null, error: "AI-förslagets markör matchar inte filens innehåll." };
    }
    return {
      resolved: {
        fileId,
        from: cursor.pos,
        to: cursor.pos,
        op: op.op,
        content: op.content ?? null,
        targetKind,
      },
      error: null,
    };
  }

  if (targetKind === "document") {
    return {
      resolved: {
        fileId,
        from: 0,
        to: textLength,
        op: op.op,
        content: op.content ?? null,
        targetKind,
      },
      error: null,
    };
  }

  return { resolved: null, error: "AI-förslaget har en okänd måltyp." };
}

function validateOperation(resolved: ResolvedTarget): string | null {
  if (resolved.op === "insert") {
    if (resolved.targetKind !== "cursor") {
      return invalidTargetMessage(resolved.targetKind, resolved.op);
    }
    if (resolved.content === null) {
      return "AI-förslaget saknar innehåll för insert.";
    }
    return null;
  }

  if (resolved.op === "replace") {
    if (resolved.targetKind !== "selection" && resolved.targetKind !== "document") {
      return invalidTargetMessage(resolved.targetKind, resolved.op);
    }
    if (resolved.content === null) {
      return "AI-förslaget saknar innehåll för replace.";
    }
    return null;
  }

  if (resolved.op === "delete") {
    if (resolved.targetKind !== "selection" && resolved.targetKind !== "document") {
      return invalidTargetMessage(resolved.targetKind, resolved.op);
    }
    if (resolved.content !== null) {
      return "AI-förslaget skickade innehåll för delete.";
    }
    return null;
  }

  return "AI-förslaget har en okänd operation.";
}

export function applyEditOpsToVirtualFiles(params: {
  virtualFiles: VirtualFileTextMap;
  ops: EditorEditOpsOp[];
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
  activeFile: VirtualFileId;
}): EditOpsApplyResult {
  const { virtualFiles, ops, selection, cursor, activeFile } = params;
  const errors: string[] = [];
  const resolvedOps: ResolvedTarget[] = [];

  for (const op of ops) {
    const currentText = virtualFiles[op.target_file];
    const { resolved, error } = resolveTarget({
      op,
      selection,
      cursor,
      activeFile,
      currentText,
    });
    if (error) {
      errors.push(error);
      break;
    }
    if (!resolved) {
      errors.push("AI-förslaget kunde inte tolkas.");
      break;
    }
    const validationError = validateOperation(resolved);
    if (validationError) {
      errors.push(validationError);
      break;
    }
    resolvedOps.push(resolved);
  }

  if (errors.length > 0) {
    return { nextFiles: { ...virtualFiles }, errors, changedFiles: [] };
  }

  const nextFiles: VirtualFileTextMap = { ...virtualFiles };
  const changedFiles = new Set<VirtualFileId>();

  for (const op of resolvedOps) {
    const current = nextFiles[op.fileId];
    let nextText = current;

    if (op.op === "insert" && op.content !== null) {
      nextText = current.slice(0, op.from) + op.content + current.slice(op.from);
    }

    if (op.op === "replace" && op.content !== null) {
      nextText = current.slice(0, op.from) + op.content + current.slice(op.to);
    }

    if (op.op === "delete") {
      nextText = current.slice(0, op.from) + current.slice(op.to);
    }

    if (nextText !== current) {
      changedFiles.add(op.fileId);
    }
    nextFiles[op.fileId] = nextText;
  }

  return { nextFiles, errors, changedFiles: Array.from(changedFiles) };
}
