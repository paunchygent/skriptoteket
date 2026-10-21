/**
 * Exam workspace picture intake.
 *
 * Domain purpose:
 *   The one check a chosen, dropped or pasted file passes before it enters an
 *   exam: read the file's bytes, sniff PNG or JPEG from the signature alone
 *   (never the name, extension or `file.type`), decode it for its pixel size,
 *   name it `asset_` plus its sha256 prefix, and refuse it with the exact
 *   inline copy when the type is wrong or the whole exam file would grow past
 *   the server's vault cap. It changes no state: the caller records the
 *   returned asset and Blob, or shows the returned copy.
 *
 * Relationships:
 *   - Consumed by the picture service (`examWorkspacePictureService`) for the
 *     toolbar, drop and paste paths; the registry and save seam take over
 *     once `readPicture` accepts a picture.
 *   - `NativeExamAsset` and `NativeExamDocument` come from `api/examWorkspace`;
 *     the size cap mirrors the server's `VAULT_MAX_FILE_BYTES`.
 */

import type { NativeExamAsset, NativeExamDocument } from "../../../api/examWorkspace";

/** Mirrors the server's `VAULT_MAX_FILE_BYTES` (src/skriptoteket/config.py), which caps the whole exam file; the exam workspace receives no setting that carries it. */
export const EXAM_FILE_MAX_BYTES = 20_000_000;

export const PICTURE_TYPE_REFUSED_COPY = "Bilden lades inte till. Välj en PNG- eller JPEG-bild.";
export const PICTURE_SIZE_REFUSED_COPY =
  "Bilden lades inte till. Provet får vara högst 20 MB med alla bilder. Välj en mindre bild.";

export type PictureIntake =
  | { kind: "picture"; asset: NativeExamAsset; blob: Blob }
  | { kind: "refused"; copy: string };

export type PictureIntakeDeps = {
  decodeSize: (blob: Blob) => Promise<{ width: number; height: number } | null>;
  digest: (bytes: ArrayBuffer) => Promise<ArrayBuffer>;
};

const PNG_SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
const JPEG_SIGNATURE = [0xff, 0xd8, 0xff];

function sniffMediaType(bytes: Uint8Array): "image/png" | "image/jpeg" | null {
  if (
    bytes.length >= PNG_SIGNATURE.length &&
    PNG_SIGNATURE.every((value, index) => bytes[index] === value)
  ) {
    return "image/png";
  }
  if (
    bytes.length >= JPEG_SIGNATURE.length &&
    JPEG_SIGNATURE.every((value, index) => bytes[index] === value)
  ) {
    return "image/jpeg";
  }
  return null;
}

function sha256Hex(digest: ArrayBuffer): string {
  return Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

export const browserPictureIntakeDeps: PictureIntakeDeps = {
  decodeSize: async (blob: Blob) => {
    try {
      const bitmap = await createImageBitmap(blob);
      const size = { width: bitmap.width, height: bitmap.height };
      bitmap.close();
      return size;
    } catch {
      return null;
    }
  },
  digest: (bytes: ArrayBuffer) => crypto.subtle.digest("SHA-256", bytes),
};

/**
 * Check a chosen, dropped or pasted file: PNG or JPEG bytes by signature with
 * a decodable non-empty pixel size become the picture's asset record and Blob;
 * anything else is refused with the exact inline copy. A picture the document
 * already declares adds no bytes, so the size check lets it through.
 */
export async function readPicture(
  file: Blob,
  document: NativeExamDocument,
  deps: PictureIntakeDeps = browserPictureIntakeDeps,
): Promise<PictureIntake> {
  const bytes = await file.arrayBuffer();
  if (bytes.byteLength === 0) {
    return { kind: "refused", copy: PICTURE_TYPE_REFUSED_COPY };
  }
  const view = new Uint8Array(bytes);
  const mediaType = sniffMediaType(view);
  if (mediaType === null) {
    return { kind: "refused", copy: PICTURE_TYPE_REFUSED_COPY };
  }
  const blob = new Blob([bytes], { type: mediaType });
  const size = await deps.decodeSize(blob);
  if (size === null || size.width <= 0 || size.height <= 0) {
    return { kind: "refused", copy: PICTURE_TYPE_REFUSED_COPY };
  }
  const sha256 = sha256Hex(await deps.digest(bytes));
  const assetId = `asset_${sha256.slice(0, 16)}`;
  if (!document.assets.some((asset) => asset.asset_id === assetId)) {
    const declared = document.assets.reduce((sum, asset) => sum + asset.byte_length, 0);
    const jsonLength = new TextEncoder().encode(JSON.stringify(document)).length;
    if (declared + bytes.byteLength + jsonLength > EXAM_FILE_MAX_BYTES) {
      return { kind: "refused", copy: PICTURE_SIZE_REFUSED_COPY };
    }
  }
  return {
    kind: "picture",
    asset: {
      asset_id: assetId,
      byte_length: bytes.byteLength,
      height: size.height,
      media_type: mediaType,
      sha256,
      width: size.width,
    },
    blob,
  };
}
