/**
 * Exam workspace picture fixtures: every accepted-case picture is coherent
 * (TASK-SKRIPT-39-10-04, review F8).
 *
 * Expected behavior:
 *   Each fixture's asset record matches its bytes: the sha256 is the digest
 *   of the bytes and the asset id carries the digest prefix, so the specs
 *   that reuse these fixtures describe pictures the production boundary
 *   accepts.
 */

import { describe, expect, it } from "vitest";

import { PICTURE_FIXTURES } from "./examWorkspacePictureFixtures.specSupport";

function toHex(digest: ArrayBuffer): string {
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

describe("exam workspace picture fixtures", () => {
  it.each([...PICTURE_FIXTURES])("$key matches its bytes", async (fixture) => {
    const digest = toHex(await crypto.subtle.digest("SHA-256", fixture.bytes));

    expect(fixture.asset.sha256).toBe(digest);
    expect(fixture.asset.asset_id).toBe(`asset_${digest.slice(0, 16)}`);
    expect(fixture.asset.byte_length).toBe(fixture.bytes.byteLength);
  });

  it.each([...PICTURE_FIXTURES])("$key serves a Blob of its own bytes", (fixture) => {
    const blob = fixture.blob();

    expect(blob.type).toBe(fixture.mediaType);
    expect(blob.size).toBe(fixture.bytes.byteLength);
  });

  it("holds at least two distinct PNGs and one JPEG", () => {
    const pngs = PICTURE_FIXTURES.filter((fixture) => fixture.mediaType === "image/png");
    const jpegs = PICTURE_FIXTURES.filter((fixture) => fixture.mediaType === "image/jpeg");

    expect(pngs.length).toBeGreaterThanOrEqual(2);
    expect(jpegs.length).toBeGreaterThanOrEqual(1);
    const digests = new Set(PICTURE_FIXTURES.map((fixture) => fixture.asset.sha256));
    expect(digests.size).toBe(PICTURE_FIXTURES.length);
  });
});
