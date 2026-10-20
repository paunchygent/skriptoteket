/**
 * Guest draft recovery archive.
 *
 * Domain purpose:
 *   Build the one zip a guest draft is downloaded as when the app cannot
 *   open it: `draft.json` plus every stored picture byte as `assets/<id>`,
 *   unchanged, named `<titel>.zip` (`Prov.zip` for a blank title). The
 *   stored record stays untouched; only the explicit remove deletes it.
 *
 * Relationships:
 *   - Shared by the signed-in handoff controller's download and the
 *     signed-out host's download, so both save the same zip instead of
 *     copying the builder.
 *   - Reads the stored draft through `examWorkspaceGuestDraftStorage.ts`;
 *     the zip itself is built with `fflate`, like the handoff download.
 */

import { strToU8, zipSync } from "fflate";

import type { StoredGuestDraft } from "./examWorkspaceGuestDraftStorage";

export type GuestDraftArchive = {
  blob: Blob;
  filename: string;
};

/**
 * Save the stored draft record and its stored picture bytes as one zip
 * `<titel>.zip` (`draft.json` plus `assets/<id>`), unchanged. Throws when a
 * picture byte cannot be read, so the caller shows the download failure.
 */
export async function buildGuestDraftArchive(stored: StoredGuestDraft): Promise<GuestDraftArchive> {
  const files: Record<string, Uint8Array> = {
    "draft.json": strToU8(JSON.stringify(stored.draft, null, 2)),
  };
  for (const [id, blob] of Object.entries(stored.assets)) {
    files[`assets/${id}`] = new Uint8Array(await blob.arrayBuffer());
  }
  const title = stored.draft.saved_document.title.trim();
  const filename = `${title === "" ? "Prov" : title}.zip`;
  return { blob: new Blob([zipSync(files)], { type: "application/zip" }), filename };
}
