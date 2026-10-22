/**
 * Coherent picture fixtures for the exam workspace new-picture specs.
 *
 * Domain purpose:
 *   Give every accepted-case new-picture spec one shared set of real
 *   pictures. Each fixture holds actual image bytes, a Blob factory with the
 *   matching media type, and the typed asset record derived from those bytes,
 *   so the specs describe states the production boundary can accept.
 *
 * Relationships:
 *   - The new-picture specs import their accepted-case pictures from here
 *     instead of manufacturing digests, ids, or bytes.
 *   - Rejection cases keep their deliberately malformed doubles where they
 *     are; nothing here replaces them.
 *   - Each fixture states its bytes' sha256; `examWorkspacePictureFixtures.spec.ts`
 *     recomputes every digest with `crypto.subtle`, so a record that drifts
 *     from its bytes fails there.
 */

import type { NativeExamAsset } from "../../../api/examWorkspace";

function bytesFromBase64(base64: string): Uint8Array<ArrayBuffer> {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

export type ExamWorkspacePictureFixture = {
  readonly key: string;
  readonly base64: string;
  readonly bytes: Uint8Array<ArrayBuffer>;
  readonly mediaType: "image/png" | "image/jpeg";
  readonly width: number;
  readonly height: number;
  readonly asset: NativeExamAsset;
  blob(): Blob;
};

function pictureFixture(
  key: string,
  base64: string,
  mediaType: "image/png" | "image/jpeg",
  width: number,
  height: number,
  sha256: string,
): ExamWorkspacePictureFixture {
  const bytes = bytesFromBase64(base64);
  const asset: NativeExamAsset = {
    asset_id: `asset_${sha256.slice(0, 16)}`,
    byte_length: bytes.byteLength,
    height,
    media_type: mediaType,
    sha256,
    width,
  };
  return {
    asset,
    base64,
    bytes,
    height,
    key,
    mediaType,
    width,
    blob(): Blob {
      return new Blob([bytes], { type: mediaType });
    },
  };
}

/** Transparent 1x1 PNG. */
const TRANSPARENT_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

/** Red 1x1 PNG, byte-distinct from the transparent one. */
const RED_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

/** White 16x16 JPEG, encoded with ffmpeg from a solid white frame. */
const WHITE_JPEG_BASE64 =
  "/9j/4AAQSkZJRgABAgAAAQABAAD//gAQTGF2YzYwLjMxLjEwMgD/2wBDAAgEBAQEBAUFBQUFBQYGBgYGBgYGBgYGBgYHBwcICAgHBwcGBgcHCAgICAkJCQgICAgJCQoKCgwMCwsODg4RERT/xABLAAEBAAAAAAAAAAAAAAAAAAAABwEBAAAAAAAAAAAAAAAAAAAAABABAAAAAAAAAAAAAAAAAAAAABEBAAAAAAAAAAAAAAAAAAAAAP/AABEIABAAEAMBIgACEQADEQD/2gAMAwEAAhEDEQA/AL+AD//Z";

export const TRANSPARENT_PNG_PICTURE = pictureFixture(
  "transparent-png",
  TRANSPARENT_PNG_BASE64,
  "image/png",
  1,
  1,
  "c414cd0e204de974f73753c7e28d7638e7b3691bb8b1a2bab6b25bb7fed7ce77",
);

export const RED_PNG_PICTURE = pictureFixture(
  "red-png",
  RED_PNG_BASE64,
  "image/png",
  1,
  1,
  "6b7fa434f92a8b80aab02d9bf1a12e49ffcae424e4013a1c4f68b67e3d2bbcd0",
);

export const WHITE_JPEG_PICTURE = pictureFixture(
  "white-jpeg",
  WHITE_JPEG_BASE64,
  "image/jpeg",
  16,
  16,
  "d0f79ffe4f30c7e43637c8a2c6dd287cf39f2f52c796c09aa27c5b3b210ebc3d",
);

export const PICTURE_FIXTURES = [
  TRANSPARENT_PNG_PICTURE,
  RED_PNG_PICTURE,
  WHITE_JPEG_PICTURE,
] as const;
