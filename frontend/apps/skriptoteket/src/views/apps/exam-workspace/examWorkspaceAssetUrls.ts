/**
 * Exam workspace picture URLs.
 *
 * Domain purpose:
 *   Map each declared picture of the open exam to its protected URL, so the
 *   editor's image atoms and the read-only instructions resolve them once.
 *
 * Relationships:
 *   - Uses `examWorkspaceAssetUrl` through the shared store half.
 *   - Consumed by `useExamWorkspaceDocument`.
 */

import type { NativeExamDocument } from "../../../api/examWorkspace";
import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";

export function examWorkspaceAssetUrls(
  shared: ExamWorkspaceSharedStore,
  document: NativeExamDocument | null,
  lineageId: string | null,
): Record<string, string> {
  if (!document || !lineageId || document.assets.length === 0) {
    return {};
  }
  return Object.fromEntries(
    document.assets.map((asset) => [
      asset.asset_id,
      shared.examWorkspaceAssetUrl(lineageId, asset.asset_id, document.revision),
    ]),
  );
}
