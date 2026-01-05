import { createTwoFilesPatch } from "diff";

import type { VirtualFileId } from "../virtualFiles";

export function normalizeTextForPatch(text: string): string {
  const normalized = text.replaceAll("\r\n", "\n").replaceAll("\r", "\n");
  if (normalized.length === 0) {
    return "";
  }
  return normalized.endsWith("\n") ? normalized : `${normalized}\n`;
}

export function buildUnifiedPatch(params: {
  virtualFileId: VirtualFileId;
  before: string;
  after: string;
}): string {
  const before = normalizeTextForPatch(params.before);
  const after = normalizeTextForPatch(params.after);

  const patch = createTwoFilesPatch(`a/${params.virtualFileId}`, `b/${params.virtualFileId}`, before, after, "", "", {
    context: 3,
  });

  const normalizedPatch = patch.replaceAll("\r\n", "\n").replaceAll("\r", "\n");
  return normalizedPatch.endsWith("\n") ? normalizedPatch : `${normalizedPatch}\n`;
}
