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

beforeAll(() => {
  let next = 0;
  vi.spyOn(URL, "createObjectURL").mockImplementation(() => `blob:mock-${(next += 1)}`);
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

function picture(id: string): NativeExamAsset {
  return {
    asset_id: id,
    byte_length: 10,
    height: 20,
    media_type: "image/png",
    sha256: "a".repeat(64),
    width: 30,
  };
}

function blob(): Blob {
  return new Blob(["bytes"], { type: "image/png" });
}

function bodyWith(assetId: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] }];
}

function documentWith(assets: NativeExamAsset[], bodies: NativeExamBodyParagraph[][]): NativeExamDocument {
  return {
    assets,
    document_id: "doc-1",
    instructions: [],
    items: [
      {
        ai_suggestion: null,
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
        body: bodies[0] ?? [],
        choices: [],
        conflicting_source_points: [],
        criteria: [],
        facit_text: null,
        gaps: [],
        import_record: null,
        item_id: "item_001",
        kept_gaps: [],
        kind: "free_text",
        leftover_points_text: null,
        match_left: [],
        match_right: [],
        points: null,
        points_estimated: false,
        print_order: [],
        printed_label: null,
        retry_source: null,
        review: { confidence: 1, parse_origin: "teacher_created", reasons: [], state: "review_complete" },
        sequence: 1,
        source_anchor: null,
        source_points: null,
        suggested_kind: null,
        tick_points: null,
        writing_lines: null,
      },
    ],
    origin: {
      extractor_version: "none",
      kind: "docx_import",
      source_filename: "blank.zip",
      source_sha256: "b".repeat(64),
    },
    parents: [],
    revision: 1,
    header: { tags: [] },
    schema_version: "native_exam_document_v11",
    title: "Exam",
  };
}

describe("createExamWorkspaceNewPictures", () => {
  function setupSent() {
    let current: NativeExamDocument | null = null;
    const registry = createExamWorkspaceNewPictures(() => current);
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    const bytes = blob();
    registry.declare(asset, bytes);
    const declared = documentWith([asset], [bodyWith(asset.asset_id)]);
    const undeclared = documentWith([], [[{ heading_level: null, segments: [] }]]);
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
    const registry = createExamWorkspaceNewPictures();
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    registry.declare(asset, blob());

    const next = registry.withDeclared(documentWith([], [bodyWith(asset.asset_id)]));

    expect(next.assets).toEqual([asset]);
  });

  it("returns the same document when the picture is not referenced", () => {
    const registry = createExamWorkspaceNewPictures();
    registry.declare(picture("asset_aaaaaaaaaaaaaaaa"), blob());
    const document = documentWith([], [[{ heading_level: null, segments: [] }]]);

    expect(registry.withDeclared(document)).toBe(document);
  });

  it("keeps one record and one URL when the same id is declared twice", () => {
    const registry = createExamWorkspaceNewPictures();
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    registry.declare(asset, blob());
    const first = registry.urls.value[asset.asset_id];
    const calls = vi.mocked(URL.createObjectURL).mock.calls.length;
    registry.declare({ ...asset, byte_length: 99 }, blob());

    const next = registry.withDeclared(documentWith([], [bodyWith(asset.asset_id)]));

    expect(next.assets).toEqual([asset]);
    expect(registry.urls.value[asset.asset_id]).toBe(first);
    expect(vi.mocked(URL.createObjectURL).mock.calls.length).toBe(calls);
  });

  it("bytesFor returns only unsent pictures the document declares", () => {
    const registry = createExamWorkspaceNewPictures();
    const declared = picture("asset_aaaaaaaaaaaaaaaa");
    const undeclared = picture("asset_bbbbbbbbbbbbbbbb");
    const first = blob();
    const second = blob();
    registry.declare(declared, first);
    registry.declare(undeclared, second);

    expect(registry.bytesFor(documentWith([declared], [bodyWith(declared.asset_id)]))).toEqual({
      [declared.asset_id]: first,
    });
  });

  it("noteSent removes bytes from bytesFor but keeps the URL", () => {
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    const document = documentWith([asset], [bodyWith(asset.asset_id)]);
    const registry = createExamWorkspaceNewPictures(() => document);
    registry.declare(asset, blob());
    const url = registry.urls.value[asset.asset_id];

    registry.noteSent([asset.asset_id]);

    expect(registry.bytesFor(document)).toEqual({});
    expect(registry.urls.value[asset.asset_id]).toBe(url);
  });

  it("reset revokes every URL and forgets every picture", () => {
    const registry = createExamWorkspaceNewPictures();
    const asset = picture("asset_aaaaaaaaaaaaaaaa");
    registry.declare(asset, blob());
    const url = registry.urls.value[asset.asset_id];
    const document = documentWith([asset], [bodyWith(asset.asset_id)]);

    registry.reset();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith(url);
    expect(registry.urls.value).toEqual({});
    expect(registry.bytesFor(document)).toEqual({});
    const fresh = documentWith([], [bodyWith(asset.asset_id)]);
    expect(registry.withDeclared(fresh)).toBe(fresh);
  });
});
