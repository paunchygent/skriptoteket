/**
 * Exam workspace new-picture registry.
 *
 * Domain purpose:
 *   Hold the pictures the teacher just added from files before their first
 *   save: each known picture keeps its asset record, its bytes and one object
 *   URL, so the editor shows it at once and the save that must carry its
 *   bytes finds them.
 *
 * Relationships:
 *   - Created per editing session inside `useExamWorkspaceDocument`; its
 *     `patchItem` and `editDocument` declare through `withDeclared`, overlay
 *     its `urls` on `examWorkspaceAssetUrls`, and reset it when the opening
 *     changes or the scope is disposed.
 *   - `bytesFor`/`noteSent` are the save seam the history store (`unit F3`,
 *     another junior) calls; the guest store is untouched here.
 *   - Declares by the same walk `withReferencedAssetsOnly` prunes by
 *     (`examWorkspaceReferencedAssetIds`), so the body edit and its asset
 *     record stay one edit, one undo step, one autosave.
 */

import { readonly, ref, type Ref } from "vue";

import type { NativeExamAsset, NativeExamDocument } from "../../../api/examWorkspace";
import { examWorkspaceReferencedAssetIds } from "./examWorkspaceStructure";

export type ExamWorkspaceNewPictures = ReturnType<typeof createExamWorkspaceNewPictures>;

/**
 * Track pictures added from files until their bytes are saved. `declare`
 * keeps the asset, its bytes and one object URL; `withDeclared` appends the
 * known assets the document references but does not declare yet.
 */
export function createExamWorkspaceNewPictures() {
  const entries = new Map<string, { asset: NativeExamAsset; blob: Blob }>();
  /** Pictures whose bytes a committed save already carried; kept until reset. */
  const sent = new Set<string>();
  const objectUrls = ref<Record<string, string>>({});

  /** Keep the picture and its bytes; a second declare of the same id is a no-op. */
  function declare(asset: NativeExamAsset, blob: Blob): void {
    if (entries.has(asset.asset_id)) {
      return;
    }
    entries.set(asset.asset_id, { asset, blob });
    objectUrls.value = { ...objectUrls.value, [asset.asset_id]: URL.createObjectURL(blob) };
  }

  /**
   * Append the known pictures the document references but does not declare
   * (question and other item bodies, the exam instruction, part
   * instructions); returns the same object when nothing is added.
   */
  function withDeclared(document: NativeExamDocument): NativeExamDocument {
    if (entries.size === 0) {
      return document;
    }
    const declared = new Set(document.assets.map((asset) => asset.asset_id));
    const referenced = examWorkspaceReferencedAssetIds(document);
    const missing = [...entries.values()]
      .map((entry) => entry.asset)
      .filter((asset) => !declared.has(asset.asset_id) && referenced.has(asset.asset_id));
    if (missing.length === 0) {
      return document;
    }
    return { ...document, assets: [...document.assets, ...missing] };
  }

  /**
   * The bytes the save must carry: unsent known pictures the document
   * declares.
   */
  function bytesFor(document: NativeExamDocument): Record<string, Blob> {
    const declared = new Set(document.assets.map((asset) => asset.asset_id));
    const pending: Record<string, Blob> = {};
    for (const [assetId, entry] of entries) {
      if (declared.has(assetId) && !sent.has(assetId)) {
        pending[assetId] = entry.blob;
      }
    }
    return pending;
  }

  /** Those pictures' bytes reached a committed save; they are sent no more. */
  function noteSent(assetIds: readonly string[]): void {
    for (const assetId of assetIds) {
      sent.add(assetId);
    }
  }

  /** Revoke every object URL and forget every picture. */
  function reset(): void {
    for (const url of Object.values(objectUrls.value)) {
      URL.revokeObjectURL(url);
    }
    entries.clear();
    sent.clear();
    objectUrls.value = {};
  }

  return {
    declare,
    withDeclared,
    /** One object URL per known picture, overlaying the server URLs. */
    urls: readonly(objectUrls) as Readonly<Ref<Record<string, string>>>,
    bytesFor,
    noteSent,
    reset,
  };
}
