/**
 * Exam workspace picture intake.
 *
 * Domain purpose:
 *   The one check a chosen, dropped or pasted file passes before it enters an
 *   exam: read the file's bytes, sniff PNG or JPEG from the signature alone
 *   (never the name, extension or `file.type`), decode it for its pixel size,
 *   name it `asset_` plus its sha256 prefix, and refuse it with the exact
 *   inline copy when the type is wrong or the whole exam file would grow past
 *   the passed cap. It changes no state: the caller records the
 *   returned asset and Blob, or shows the returned copy.
 *
 * Relationships:
 *   - Consumed by the picture service (`examWorkspacePictureService`) for the
 *     toolbar, drop and paste paths; the registry and save seam take over
 *     once `readPicture` accepts a picture.
 *   - `NativeExamAsset` and `NativeExamDocument` come from `api/examWorkspace`;
 *     the size cap comes from the server's limits route through the caller:
 *     this module owns no limit number.
 */

import type { NativeExamAsset, NativeExamDocument } from "../../../api/examWorkspace";
import { examWorkspaceAssetReferenceCounts } from "./examWorkspaceStructure";

export const PICTURE_TYPE_REFUSED_COPY = "Bilden lades inte till. Välj en PNG- eller JPEG-bild.";

/** The inline refusal while the server-owned limit cannot be read: the picture is held back, never guessed at. */
export const PICTURE_LIMIT_UNAVAILABLE_COPY = "Bilden lades inte till. Försök igen.";

/** The size refusal for `maxExamBytes`, formatted in Swedish megabytes (20_000_000 → "20", 2_500_000 → "2,5"). */
export function pictureSizeRefusedCopy(maxExamBytes: number): string {
  const mb = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 1 }).format(
    maxExamBytes / 1_000_000,
  );
  return `Bilden lades inte till. Provet får vara högst ${mb} MB med alla bilder. Välj en mindre bild.`;
}

export type PictureIntake =
  | { kind: "picture"; asset: NativeExamAsset; blob: Blob }
  | { kind: "refused"; copy: string };

export type PictureIntakeDeps = {
  decodeSize: (blob: Blob) => Promise<{ width: number; height: number } | null>;
  digest: (bytes: ArrayBuffer) => Promise<ArrayBuffer>;
};

/** The intake's per-call authority: the server-owned whole-exam cap and the selected picture a replace removes. */
export type PictureIntakeOptions = {
  /** The whole-exam byte cap from the server's limits route; the only size authority. */
  maxExamBytes: number;
  /** The selected picture's asset id when replacing, else null. */
  replacing: string | null;
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
 * already declares adds no bytes, and a replacement credits the replaced
 * picture's bytes when its selected reference is the only one left, so the
 * size check sees the prospective result. An unreadable file is refused with
 * the type copy. Nothing is changed: the caller records the
 * asset and Blob, or shows the copy.
 */
export async function readPicture(
  file: Blob,
  document: NativeExamDocument,
  options: PictureIntakeOptions,
  deps: PictureIntakeDeps = browserPictureIntakeDeps,
): Promise<PictureIntake> {
  let bytes: ArrayBuffer;
  try {
    bytes = await file.arrayBuffer();
  } catch (error) {
    if (error instanceof DOMException) {
      return { kind: "refused", copy: PICTURE_TYPE_REFUSED_COPY };
    }
    throw error;
  }
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
    const { replacing, maxExamBytes } = options;
    const replaced =
      replacing === null
        ? undefined
        : document.assets.find((asset) => asset.asset_id === replacing);
    const removedBytes =
      replaced !== undefined &&
      replacing !== null &&
      replacing !== assetId &&
      examWorkspaceAssetReferenceCounts(document).get(replacing) === 1
        ? replaced.byte_length
        : 0;
    const jsonLength = new TextEncoder().encode(JSON.stringify(document)).length;
    if (declared + bytes.byteLength - removedBytes + jsonLength > maxExamBytes) {
      return { kind: "refused", copy: pictureSizeRefusedCopy(maxExamBytes) };
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
