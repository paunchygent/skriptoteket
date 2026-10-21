/**
 * Exam workspace picture service: the toolbar's picture control.
 *
 * Expected behavior (TASK-SKRIPT-39-10-04, unit U6):
 *   `createExamWorkspacePictureService` checks each file in order on the
 *   target: an accepted file is declared for the open exam and placed on the
 *   target (declare before place, one `placePicture` per `add`), clearing
 *   any refusal; the first refusal sets the notice and stops, placing
 *   nothing. `busy` is true during the read and false after, also after a
 *   throw. A disabled pane, no open document, a target that takes no
 *   pictures, or a second `add` while one runs does nothing.
 */

import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import type { Ref } from "vue";

import type { NativeExamAsset, NativeExamDocument } from "../../../api/examWorkspace";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { createExamWorkspacePictureService } from "./examWorkspacePictureService";
import type { PictureIntake } from "./examWorkspacePictureIntake";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

const TYPE_COPY = "Bilden lades inte till. Välj en PNG- eller JPEG-bild.";
const SIZE_COPY =
  "Bilden lades inte till. Provet får vara högst 20 MB med alla bilder. Välj en mindre bild.";

function asset(assetId: string): NativeExamAsset {
  return {
    asset_id: assetId,
    byte_length: 4,
    height: 1,
    media_type: "image/png",
    sha256: "a".repeat(64),
    width: 1,
  };
}

const BLOB = new Blob(["png!"], { type: "image/png" });
const ASSET_ID = "asset_0123456789abcdef";
const DOCUMENT = { assets: [] } as unknown as NativeExamDocument;

function stubTarget(acceptsPictures = true) {
  return {
    marks: ref([]) as Ref<BodyMark[]>,
    headingLevel: () => null,
    toggleMark: vi.fn(),
    toggleHeading: vi.fn(),
    makeGap: vi.fn(),
    acceptsPictures,
    pictureSelected: ref(false),
    placePicture: vi.fn((_assetId: string): void => undefined),
    release: vi.fn(),
  };
}

function setup(options?: {
  canEdit?: boolean;
  document?: NativeExamDocument | null;
  read?: (file: Blob, document: NativeExamDocument) => Promise<PictureIntake>;
}) {
  const newPictures = { declare: vi.fn() };
  const read =
    options?.read ??
    (async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }) as PictureIntake);
  const service = createExamWorkspacePictureService({
    document: () => (options?.document === undefined ? DOCUMENT : options.document),
    newPictures,
    canEdit: () => options?.canEdit ?? true,
    read: read as typeof import("./examWorkspacePictureIntake").readPicture,
  });
  return { newPictures, service };
}

function setupWithRead(
  read: (file: Blob, document: NativeExamDocument) => Promise<PictureIntake>,
  options?: { canEdit?: boolean; document?: NativeExamDocument | null },
) {
  const wrapped = vi.fn(read);
  const newPictures = { declare: vi.fn() };
  const service = createExamWorkspacePictureService({
    document: () => (options?.document === undefined ? DOCUMENT : options.document),
    newPictures,
    canEdit: () => options?.canEdit ?? true,
    read: wrapped as typeof import("./examWorkspacePictureIntake").readPicture,
  });
  return { newPictures, read: wrapped, service };
}

describe("createExamWorkspacePictureService", () => {
  it("declares then places an accepted file and clears the notice", async () => {
    const { newPictures, service } = setup();
    const target = stubTarget();
    service.notice.value = { kind: "refused", text: TYPE_COPY } as ExamWorkspaceNotice;

    await service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);

    expect(newPictures.declare).toHaveBeenCalledTimes(1);
    expect(newPictures.declare).toHaveBeenCalledWith(asset(ASSET_ID), BLOB);
    expect(target.placePicture).toHaveBeenCalledTimes(1);
    expect(target.placePicture).toHaveBeenCalledWith(ASSET_ID);
    const declareOrder = newPictures.declare.mock.invocationCallOrder[0]!;
    const placeOrder = target.placePicture.mock.invocationCallOrder[0]!;
    expect(declareOrder).toBeLessThan(placeOrder);
    expect(service.notice.value).toBeNull();
    expect(service.busy.value).toBe(false);
  });

  it("reports busy during the read and resets it after", async () => {
    let resolveRead!: (intake: PictureIntake) => void;
    const { service } = setupWithRead(
      () =>
        new Promise<PictureIntake>((resolve) => {
          resolveRead = resolve;
        }),
    );
    const target = stubTarget();

    const pending = service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);
    expect(service.busy.value).toBe(true);
    resolveRead({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB });
    await pending;

    expect(service.busy.value).toBe(false);
    expect(target.placePicture).toHaveBeenCalledWith(ASSET_ID);
  });

  it("resets busy after a throw", async () => {
    const { service } = setupWithRead(async () => {
      throw new Error("offline");
    });

    await expect(
      service.add(stubTarget(), [new File(["png!"], "bild.png", { type: "image/png" })]),
    ).rejects.toThrow("offline");
    expect(service.busy.value).toBe(false);
    expect(service.notice.value).toBeNull();
  });

  it("sets the notice and places nothing on a refused type", async () => {
    const { newPictures, service } = setupWithRead(async () => ({ kind: "refused", copy: TYPE_COPY }));
    const target = stubTarget();

    await service.add(target, [new File(["hej"], "text.txt", { type: "text/plain" })]);

    expect(service.notice.value).toEqual({ kind: "refused", text: TYPE_COPY });
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
    expect(service.busy.value).toBe(false);
  });

  it("sets the notice and places nothing on a refused size", async () => {
    const { newPictures, service } = setupWithRead(async () => ({ kind: "refused", copy: SIZE_COPY }));
    const target = stubTarget();

    await service.add(target, [new File(["png!"], "stor.png", { type: "image/png" })]);

    expect(service.notice.value).toEqual({ kind: "refused", text: SIZE_COPY });
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
  });

  it("stops at the first refusal and reads nothing after it", async () => {
    const second = asset("asset_fedcba9876543210");
    const { newPictures, read, service } = setupWithRead(async (file) =>
      (file as File).name === "dålig.gif"
        ? { kind: "refused", copy: TYPE_COPY }
        : { kind: "picture", asset: (file as File).name === "andra.png" ? second : asset(ASSET_ID), blob: BLOB },
    );
    const target = stubTarget();

    await service.add(target, [
      new File(["1"], "första.png", { type: "image/png" }),
      new File(["2"], "dålig.gif", { type: "image/gif" }),
      new File(["3"], "andra.png", { type: "image/png" }),
    ]);

    expect(read).toHaveBeenCalledTimes(2);
    expect(target.placePicture).toHaveBeenCalledTimes(1);
    expect(target.placePicture).toHaveBeenCalledWith(ASSET_ID);
    expect(service.notice.value).toEqual({ kind: "refused", text: TYPE_COPY });
    expect(newPictures.declare).toHaveBeenCalledTimes(1);
  });

  it("does nothing while disabled", async () => {
    const { newPictures, read, service } = setupWithRead(
      async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }),
      { canEdit: false },
    );
    const target = stubTarget();

    await service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);

    expect(read).not.toHaveBeenCalled();
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
    expect(service.busy.value).toBe(false);
  });

  it("does nothing without an open document", async () => {
    const { newPictures, read, service } = setupWithRead(
      async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }),
      { document: null },
    );

    await service.add(stubTarget(), [new File(["png!"], "bild.png", { type: "image/png" })]);

    expect(read).not.toHaveBeenCalled();
    expect(newPictures.declare).not.toHaveBeenCalled();
  });

  it("does nothing on a target that takes no pictures", async () => {
    const { newPictures, read, service } = setupWithRead(async () => ({
      kind: "picture",
      asset: asset(ASSET_ID),
      blob: BLOB,
    }));
    const target = stubTarget(false);

    await service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);

    expect(read).not.toHaveBeenCalled();
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
  });

  it("ignores a second add while one runs", async () => {
    let resolveRead!: (intake: PictureIntake) => void;
    const { read, service } = setupWithRead(
      () =>
        new Promise<PictureIntake>((resolve) => {
          resolveRead = resolve;
        }),
    );
    const target = stubTarget();
    const file = new File(["png!"], "bild.png", { type: "image/png" });

    const first = service.add(target, [file]);
    await service.add(target, [file]);
    expect(read).toHaveBeenCalledTimes(1);
    resolveRead({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB });
    await first;

    expect(read).toHaveBeenCalledTimes(1);
    expect(target.placePicture).toHaveBeenCalledTimes(1);
  });

  it("dismissNotice clears the refusal", async () => {
    const { service } = setupWithRead(async () => ({ kind: "refused", copy: TYPE_COPY }));

    await service.add(stubTarget(), [new File(["hej"], "text.txt", { type: "text/plain" })]);
    expect(service.notice.value).not.toBeNull();
    service.dismissNotice();
    expect(service.notice.value).toBeNull();
  });

  it("checks each later file against the document the earlier picture changed", async () => {
    const first = { assets: [] } as unknown as NativeExamDocument;
    const second = { assets: [asset("asset_first")] } as unknown as NativeExamDocument;
    let current = first;
    const read = vi.fn(async (_file: Blob, _document: NativeExamDocument) => {
      const placed = read.mock.calls.length === 1 ? "asset_first" : "asset_second";
      return { kind: "picture", asset: asset(placed), blob: BLOB } as PictureIntake;
    });
    const target = stubTarget();
    target.placePicture.mockImplementation(() => {
      current = second;
    });
    const service = createExamWorkspacePictureService({
      document: () => current,
      newPictures: { declare: vi.fn() },
      canEdit: () => true,
      read: read as typeof import("./examWorkspacePictureIntake").readPicture,
    });

    await service.add(target, [new File(["a"], "a.png"), new File(["b"], "b.png")]);

    expect(read.mock.calls.map((call) => call[1])).toEqual([first, second]);
    expect(target.placePicture.mock.calls).toEqual([["asset_first"], ["asset_second"]]);
  });
});
