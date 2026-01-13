import type { EditorEditOpsOpOutput } from "./editOpsState";
import type { VirtualFileId, VirtualFileTextMap } from "../virtualFiles";
import type { EditOpsDiffItem } from "./editOpsState";

export function uniqueTargetFiles(ops: EditorEditOpsOpOutput[]): VirtualFileId[] {
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

export function buildDiffItems(params: {
  targetFiles: VirtualFileId[];
  beforeFiles: VirtualFileTextMap;
  afterFiles: VirtualFileTextMap;
}): EditOpsDiffItem[] {
  const { targetFiles, beforeFiles, afterFiles } = params;
  return targetFiles
    .filter((fileId) => beforeFiles[fileId] !== afterFiles[fileId])
    .map((fileId) => ({
      virtualFileId: fileId,
      beforeText: beforeFiles[fileId],
      afterText: afterFiles[fileId],
    }));
}
