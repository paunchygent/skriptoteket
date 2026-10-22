/**
 * New-picture registry of the exam workspace (TASK-SKRIPT-39-10-04, unit U3).
 *
 * Expected behavior:
 *   A picture the teacher adds from a file is kept with its bytes and one
 *   object URL; the document edit that places it declares it in the same
 *   step, and its bytes stay available for the save that must carry them.
 */

import { beforeAll, describe, expect, it, vi } from "vitest";

import type { NativeExamAsset, NativeExamBodyParagraph, NativeExamDocument } from "../../../api/examWorkspace";
import { createExamWorkspaceNewPictures } from "./examWorkspaceNewPictures";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  RED_PNG_PICTURE,
  TRANSPARENT_PNG_PICTURE,
} from "./examWorkspacePictureFixtures.specSupport";

beforeAll(() => {
  let next = 0;
  vi.spyOn(URL, "createObjectURL").mockImplementation(() => `blob:mock-${(next += 1)}`);
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

function bodyWith(assetId: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] }];
}

function documentWith(assets: NativeExamAsset[], bodyAssetId: string | null): NativeExamDocument {
  const base = buildParentDocument();
  const body =
    bodyAssetId === null
      ? [{ heading_level: null, segments: [] }]
      : bodyWith(bodyAssetId);
  return {
    ...base,
    assets,
    items: base.items.map((item, index) => (index === 0 ? { ...item, body } : item)),
  };
}

describe("createExamWorkspaceNewPictures", () => {
  function setupSent() {
    let current: NativeExamDocument | null = null;
    const registry = createExamWorkspaceNewPictures(() => current);
    const asset = TRANSPARENT_PNG_PICTURE.asset;
    const bytes = TRANSPARENT_PNG_PICTURE.blob();
    registry.declare(asset, bytes);
    const declared = documentWith([asset], asset.asset_id);
    const undeclared = documentWith([], null);
    return {
      asset,
      bytes,
      declared,
      registry,
      setCurrent: (document: NativeExamDocument | null): void => {
        current = document;
      },
      undeclared,
    };
  }

  it("forgets sent for an undeclared picture but keeps its bytes for a re-add", () => {
    const { asset, bytes, declared, registry, setCurrent, undeclared } = setupSent();
    setCurrent(declared);
    registry.noteSent([asset.asset_id]);
    expect(registry.bytesFor(declared)).toEqual({});

    setCurrent(undeclared);
    registry.forgetUndeclared(undeclared);

    expect(registry.bytesFor(declared)).toEqual({ [asset.asset_id]: bytes });
  });

  it("keeps sent while the document still declares the picture", () => {
    const { asset, declared, registry, setCurrent } = setupSent();
    setCurrent(declared);
    registry.noteSent([asset.asset_id]);

    registry.forgetUndeclared(declared);

    expect(registry.bytesFor(declared)).toEqual({});
  });

  it("noteSent ignores an id the current document no longer declares", () => {
    const { asset, bytes, declared, registry, setCurrent, undeclared } = setupSent();
    setCurrent(undeclared);

    registry.noteSent([asset.asset_id]);

    expect(registry.bytesFor(declared)).toEqual({ [asset.asset_id]: bytes });
  });

  it("a null document clears every sent mark but keeps the bytes", () => {
    const { asset, bytes, declared, registry, setCurrent } = setupSent();
    setCurrent(declared);
    registry.noteSent([asset.asset_id]);

    setCurrent(null);
    registry.forgetUndeclared(null);

    expect(registry.bytesFor(declared)).toEqual({ [asset.asset_id]: bytes });
  });
  it("declares a referenced picture in the same document object step", () => {
    const registry = createExamWorkspaceNewPictures(() => null);
    const asset = TRANSPARENT_PNG_PICTURE.asset;
    registry.declare(asset, TRANSPARENT_PNG_PICTURE.blob());

    const next = registry.withDeclared(documentWith([], asset.asset_id));

    expect(next.assets).toEqual([asset]);
  });

  it("returns the same document when the picture is not referenced", () => {
    const registry = createExamWorkspaceNewPictures(() => null);
    registry.declare(TRANSPARENT_PNG_PICTURE.asset, TRANSPARENT_PNG_PICTURE.blob());
    const document = documentWith([], null);

    expect(registry.withDeclared(document)).toBe(document);
  });

  it("keeps one record and one URL when the same id is declared twice", () => {
    const registry = createExamWorkspaceNewPictures(() => null);
    const asset = TRANSPARENT_PNG_PICTURE.asset;
    registry.declare(asset, TRANSPARENT_PNG_PICTURE.blob());
    const first = registry.urls.value[asset.asset_id];
    const calls = vi.mocked(URL.createObjectURL).mock.calls.length;
    registry.declare({ ...asset, byte_length: 99 }, TRANSPARENT_PNG_PICTURE.blob());

    const next = registry.withDeclared(documentWith([], asset.asset_id));

    expect(next.assets).toEqual([asset]);
    expect(registry.urls.value[asset.asset_id]).toBe(first);
    expect(vi.mocked(URL.createObjectURL).mock.calls.length).toBe(calls);
  });

  it("bytesFor returns only unsent pictures the document declares", () => {
    const registry = createExamWorkspaceNewPictures(() => null);
    const declared = TRANSPARENT_PNG_PICTURE.asset;
    const undeclared = RED_PNG_PICTURE.asset;
    const first = TRANSPARENT_PNG_PICTURE.blob();
    const second = RED_PNG_PICTURE.blob();
    registry.declare(declared, first);
    registry.declare(undeclared, second);

    expect(registry.bytesFor(documentWith([declared], declared.asset_id))).toEqual({
      [declared.asset_id]: first,
    });
  });

  it("noteSent removes bytes from bytesFor but keeps the URL", () => {
    const asset = TRANSPARENT_PNG_PICTURE.asset;
    const document = documentWith([asset], asset.asset_id);
    const registry = createExamWorkspaceNewPictures(() => document);
    registry.declare(asset, TRANSPARENT_PNG_PICTURE.blob());
    const url = registry.urls.value[asset.asset_id];

    registry.noteSent([asset.asset_id]);

    expect(registry.bytesFor(document)).toEqual({});
    expect(registry.urls.value[asset.asset_id]).toBe(url);
  });

  it("reset revokes every URL and forgets every picture", () => {
    const registry = createExamWorkspaceNewPictures(() => null);
    const asset = TRANSPARENT_PNG_PICTURE.asset;
    registry.declare(asset, TRANSPARENT_PNG_PICTURE.blob());
    const url = registry.urls.value[asset.asset_id];
    const document = documentWith([asset], asset.asset_id);

    registry.reset();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith(url);
    expect(registry.urls.value).toEqual({});
    expect(registry.bytesFor(document)).toEqual({});
    const fresh = documentWith([], asset.asset_id);
    expect(registry.withDeclared(fresh)).toBe(fresh);
  });
});
