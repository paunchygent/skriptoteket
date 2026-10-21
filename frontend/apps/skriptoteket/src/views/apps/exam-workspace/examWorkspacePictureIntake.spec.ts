/**
 * Picture intake checks (TASK-SKRIPT-39-10-04, U2).
 *
 * Expected behavior:
 *   A chosen, dropped or pasted file is read by signature alone: PNG or JPEG
 *   bytes with a decodable non-empty pixel size become the picture's asset
 *   record (`asset_` plus the sha256 prefix) and a Blob typed by the sniffed
 *   media type. Any other signature, an empty file, or an undecodable picture
 *   is refused with the type copy; a picture that would push the whole exam
 *   file past the vault cap is refused with the size copy, unless the document
 *   already declares that picture. Nothing is changed: the caller records the
 *   asset and Blob, or shows the copy.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamAsset, NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  EXAM_FILE_MAX_BYTES,
  PICTURE_SIZE_REFUSED_COPY,
  PICTURE_TYPE_REFUSED_COPY,
  readPicture,
  type PictureIntakeDeps,
} from "./examWorkspacePictureIntake";

const PNG_SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
const JPEG_SIGNATURE = [0xff, 0xd8, 0xff];

const SHA_A = `a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90`;
const SHA_B = `00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff`;

/**
 * jsdom's Blob has no `arrayBuffer`; equip each test file with one holding the
 * exact bytes, like the production file path provides.
 */
function withBytes(blob: Blob, bytes: Uint8Array): Blob {
  Object.defineProperty(blob, "arrayBuffer", {
    configurable: true,
    value: async (): Promise<ArrayBuffer> => {
      const copy = new Uint8Array(bytes.length);
      copy.set(bytes);
      return copy.buffer;
    },
  });
  return blob;
}

function blobOf(values: number[], type?: string): Blob {
  const bytes = new Uint8Array(values);
  return withBytes(
    new Blob([bytes], type === undefined ? undefined : { type }),
    bytes,
  );
}

function pngBytes(payload: number[] = [1, 2, 3]): Blob {
  return blobOf([...PNG_SIGNATURE, ...payload]);
}

function jpegBytes(payload: number[] = [0xe0, 4, 5]): Blob {
  return blobOf([...JPEG_SIGNATURE, ...payload]);
}

function bufferOfHex(hex: string): ArrayBuffer {
  const bytes = new Uint8Array(hex.length / 2);
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = Number.parseInt(hex.slice(index * 2, index * 2 + 2), 16);
  }
  return bytes.buffer;
}

function stubDeps(size: { width: number; height: number } | null, shaHex: string): PictureIntakeDeps {
  return {
    decodeSize: async () => size,
    digest: async () => bufferOfHex(shaHex),
  };
}

function declaredAsset(overrides: Partial<NativeExamAsset> & { asset_id: string }): NativeExamAsset {
  return {
    byte_length: 10,
    height: 480,
    media_type: "image/png",
    sha256: SHA_A,
    width: 640,
    ...overrides,
  };
}

function documentWith(assets: NativeExamAsset[]): NativeExamDocument {
  return { ...buildParentDocument(), assets };
}

describe("readPicture accepted pictures", () => {
  it("accepts PNG bytes with its asset record and a PNG-typed Blob", async () => {
    const file = pngBytes();

    const result = await readPicture(file, documentWith([]), stubDeps({ width: 640, height: 480 }, SHA_A));

    expect(result.kind).toBe("picture");
    if (result.kind !== "picture") {
      return;
    }
    expect(result.asset).toEqual({
      asset_id: `asset_${SHA_A.slice(0, 16)}`,
      byte_length: PNG_SIGNATURE.length + 3,
      height: 480,
      media_type: "image/png",
      sha256: SHA_A,
      width: 640,
    });
    expect(result.blob.type).toBe("image/png");
    expect(result.blob.size).toBe(PNG_SIGNATURE.length + 3);
  });

  it("accepts JPEG bytes and lets the signature win over a lying name and type", async () => {
    const jpeg = jpegBytes();
    const png = new Uint8Array([...PNG_SIGNATURE, 1, 2, 3]);
    const renamedPng = withBytes(
      new File([pngBytes()], "bild.jpg", { type: "image/jpeg" }),
      png,
    );

    const jpegResult = await readPicture(jpeg, documentWith([]), stubDeps({ width: 10, height: 20 }, SHA_B));
    const renamedResult = await readPicture(
      renamedPng,
      documentWith([]),
      stubDeps({ width: 30, height: 40 }, SHA_A),
    );

    expect(jpegResult.kind).toBe("picture");
    if (jpegResult.kind === "picture") {
      expect(jpegResult.asset.media_type).toBe("image/jpeg");
      expect(jpegResult.blob.type).toBe("image/jpeg");
    }
    expect(renamedResult.kind).toBe("picture");
    if (renamedResult.kind === "picture") {
      expect(renamedResult.asset.media_type).toBe("image/png");
      expect(renamedResult.blob.type).toBe("image/png");
    }
  });
});

describe("readPicture refused type", () => {
  it("refuses GIF bytes, a text file named bild.png, and an empty file", async () => {
    const gif = blobOf([0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 1, 2, 3], "image/gif");
    const textBytes = new TextEncoder().encode("det här är ingen bild");
    const text = withBytes(new File([textBytes], "bild.png", { type: "image/png" }), textBytes);
    const empty = blobOf([]);

    for (const file of [gif, text, empty]) {
      const result = await readPicture(file, documentWith([]), stubDeps({ width: 1, height: 1 }, SHA_A));
      expect(result).toEqual({ kind: "refused", copy: PICTURE_TYPE_REFUSED_COPY });
    }
  });

  it("refuses PNG-signature garbage the decoder rejects, and zero pixel sizes", async () => {
    const garbage = pngBytes([9, 9, 9]);

    const undecodable = await readPicture(garbage, documentWith([]), stubDeps(null, SHA_A));
    const zeroWidth = await readPicture(
      garbage,
      documentWith([]),
      stubDeps({ width: 0, height: 10 }, SHA_A),
    );
    const zeroHeight = await readPicture(
      garbage,
      documentWith([]),
      stubDeps({ width: 10, height: 0 }, SHA_A),
    );

    expect(undecodable).toEqual({ kind: "refused", copy: PICTURE_TYPE_REFUSED_COPY });
    expect(zeroWidth).toEqual({ kind: "refused", copy: PICTURE_TYPE_REFUSED_COPY });
    expect(zeroHeight).toEqual({ kind: "refused", copy: PICTURE_TYPE_REFUSED_COPY });
  });
});

describe("readPicture size limit", () => {
  it("refuses a picture that would push the exam file past the vault cap", async () => {
    const almostFull = documentWith([declaredAsset({ asset_id: "asset_other", byte_length: EXAM_FILE_MAX_BYTES - 50 })]);

    const result = await readPicture(
      pngBytes(new Array(100).fill(7)),
      almostFull,
      stubDeps({ width: 640, height: 480 }, SHA_A),
    );

    expect(result).toEqual({ kind: "refused", copy: PICTURE_SIZE_REFUSED_COPY });
  });

  it("accepts the same over-limit picture when the document already declares it", async () => {
    const assetId = `asset_${SHA_A.slice(0, 16)}`;
    const full = documentWith([
      declaredAsset({ asset_id: assetId, byte_length: EXAM_FILE_MAX_BYTES - 50 }),
    ]);

    const result = await readPicture(
      pngBytes(new Array(100).fill(7)),
      full,
      stubDeps({ width: 640, height: 480 }, SHA_A),
    );

    expect(result.kind).toBe("picture");
    if (result.kind === "picture") {
      expect(result.asset.asset_id).toBe(assetId);
    }
  });
});

const hasSubtle =
  typeof globalThis.crypto !== "undefined" &&
  typeof globalThis.crypto.subtle?.digest === "function";

(globalThis.crypto?.subtle ? it : it.skip)("digests with the real crypto.subtle", async () => {
  const payload = [...PNG_SIGNATURE, 11, 22, 33];
  const file = blobOf(payload);
  const expected = Array.from(
    new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", new Uint8Array(payload))),
  )
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");

  const result = await readPicture(file, documentWith([]), {
    decodeSize: async () => ({ width: 3, height: 4 }),
    digest: (bytes) => globalThis.crypto.subtle.digest("SHA-256", bytes),
  });

  expect(hasSubtle).toBe(true);
  expect(result.kind).toBe("picture");
  if (result.kind === "picture") {
    expect(result.asset.sha256).toBe(expected);
    expect(result.asset.asset_id).toBe(`asset_${expected.slice(0, 16)}`);
  }
});
