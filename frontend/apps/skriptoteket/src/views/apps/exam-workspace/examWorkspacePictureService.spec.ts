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
 *
 * Limit loading lives in `.limit`; stale intakes live in `.lifetime`.
 * Accepted pictures are the shared fixtures (real bytes, digest-matched
 * asset records); rejection cases keep their deliberately malformed files.
 */

import { describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { createExamWorkspacePictureService } from "./examWorkspacePictureService";
import type { PictureIntake } from "./examWorkspacePictureIntake";
import {
  DOCUMENT,
  FIRST_PICTURE,
  LIMIT,
  liveOpening,
  nameOf,
  pictureFile,
  SECOND_PICTURE,
  setup,
  setupWithRead,
  SIZE_COPY,
  stubTarget,
  TYPE_COPY,
} from "./examWorkspacePictureService.specSupport";

describe("createExamWorkspacePictureService", () => {
  it("declares then places an accepted file and clears the notice", async () => {
    const { newPictures, service } = setup();
    const target = stubTarget();
    service.notice.value = { kind: "refused", text: TYPE_COPY };

    await service.add(target, [pictureFile()]);

    expect(newPictures.declare).toHaveBeenCalledTimes(1);
    expect(newPictures.declare).toHaveBeenCalledWith(FIRST_PICTURE.asset, expect.any(Blob));
    expect(target.placePicture).toHaveBeenCalledTimes(1);
    expect(target.placePicture).toHaveBeenCalledWith(FIRST_PICTURE.asset.asset_id);
    const declareOrder = newPictures.declare.mock.invocationCallOrder[0]!;
    const placeOrder = target.placePicture.mock.invocationCallOrder[0]!;
    expect(declareOrder).toBeLessThan(placeOrder);
    expect(service.notice.value).toBeNull();
    expect(service.busy.value).toBe(false);
  });

  it("reports busy during the read and resets it after", async () => {
    let resolveRead!: (intake: PictureIntake) => void;
    const { read, service } = setupWithRead(
      () =>
        new Promise<PictureIntake>((resolve) => {
          resolveRead = resolve;
        }),
    );
    const target = stubTarget();

    const pending = service.add(target, [pictureFile()]);
    expect(service.busy.value).toBe(true);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
    resolveRead({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() });
    await pending;

    expect(service.busy.value).toBe(false);
    expect(target.placePicture).toHaveBeenCalledWith(FIRST_PICTURE.asset.asset_id);
  });

  it("resets busy after a throw", async () => {
    const { service } = setupWithRead(async () => {
      throw new Error("offline");
    });

    await expect(
      service.add(stubTarget(), [pictureFile()]),
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

    await service.add(target, [pictureFile(FIRST_PICTURE, "stor.png")]);

    expect(service.notice.value).toEqual({ kind: "refused", text: SIZE_COPY });
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
  });

  it("stops at the first refusal and reads nothing after it", async () => {
    const { newPictures, read, service } = setupWithRead(async (file) =>
      nameOf(file) === "dålig.gif"
        ? { kind: "refused", copy: TYPE_COPY }
        : {
            kind: "picture",
            asset: nameOf(file) === "andra.png" ? SECOND_PICTURE.asset : FIRST_PICTURE.asset,
            blob: (nameOf(file) === "andra.png" ? SECOND_PICTURE : FIRST_PICTURE).blob(),
          },
    );
    const target = stubTarget();

    await service.add(target, [
      pictureFile(FIRST_PICTURE, "första.png"),
      pictureFile(FIRST_PICTURE, "dålig.gif"),
      pictureFile(SECOND_PICTURE, "andra.png"),
    ]);

    expect(read).toHaveBeenCalledTimes(2);
    expect(target.placePicture).toHaveBeenCalledTimes(1);
    expect(target.placePicture).toHaveBeenCalledWith(FIRST_PICTURE.asset.asset_id);
    expect(service.notice.value).toEqual({ kind: "refused", text: TYPE_COPY });
    expect(newPictures.declare).toHaveBeenCalledTimes(1);
  });

  it("does nothing while disabled", async () => {
    const { newPictures, read, service } = setupWithRead(
      async () => ({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() }),
      { canEdit: false },
    );
    const target = stubTarget();

    await service.add(target, [pictureFile()]);

    expect(read).not.toHaveBeenCalled();
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
    expect(service.busy.value).toBe(false);
  });

  it("does nothing without an open document", async () => {
    const { newPictures, read, service } = setupWithRead(
      async () => ({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() }),
      { document: null },
    );

    await service.add(stubTarget(), [pictureFile()]);

    expect(read).not.toHaveBeenCalled();
    expect(newPictures.declare).not.toHaveBeenCalled();
  });

  it("does nothing on a target that takes no pictures", async () => {
    const { newPictures, read, service } = setupWithRead(async () => ({
      kind: "picture",
      asset: FIRST_PICTURE.asset,
      blob: FIRST_PICTURE.blob(),
    }));
    const target = stubTarget(false);

    await service.add(target, [pictureFile()]);

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
    const file = pictureFile();

    const first = service.add(target, [file]);
    await service.add(target, [file]);
    await vi.waitFor(() => expect(read).toHaveBeenCalledTimes(1));
    resolveRead({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() });
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

  it("passes the selected picture id as replacing, and null without a selection", async () => {
    const { read, service } = setupWithRead(
      async () => ({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() }),
    );
    const selected = stubTarget();
    selected.selectedPictureId.value = SECOND_PICTURE.asset.asset_id;
    const plain = stubTarget();
    const file = pictureFile();

    await service.add(selected, [file]);
    await service.add(plain, [file]);

    expect(read).toHaveBeenCalledTimes(2);
    expect(read.mock.calls[0]?.[2]).toEqual({
      maxExamBytes: LIMIT,
      replacing: SECOND_PICTURE.asset.asset_id,
    });
    expect(read.mock.calls[1]?.[2]).toEqual({ maxExamBytes: LIMIT, replacing: null });
  });

  it("checks each later file against the document the earlier picture changed", async () => {
    const first: NativeExamDocument = { ...DOCUMENT, assets: [] };
    const second: NativeExamDocument = { ...DOCUMENT, assets: [FIRST_PICTURE.asset] };
    let current = first;
    const read = vi.fn(async (_file: Blob, _document: NativeExamDocument): Promise<PictureIntake> => {
      const placed = read.mock.calls.length === 1 ? FIRST_PICTURE : SECOND_PICTURE;
      return { kind: "picture", asset: placed.asset, blob: placed.blob() };
    });
    const target = stubTarget();
    target.placePicture.mockImplementation(() => {
      current = second;
    });
    const scope = liveOpening();
    const service = createExamWorkspacePictureService({
      document: () => current,
      newPictures: { declare: vi.fn() },
      canEdit: () => true,
      opening: scope.opening,
      isOpen: scope.isOpen,
      maxExamBytes: async () => LIMIT,
      read: read as typeof import("./examWorkspacePictureIntake").readPicture,
    });

    await service.add(target, [pictureFile(FIRST_PICTURE, "a.png"), pictureFile(SECOND_PICTURE, "b.png")]);

    expect(read.mock.calls.map((call) => call[1])).toEqual([first, second]);
    expect(target.placePicture.mock.calls).toEqual([
      [FIRST_PICTURE.asset.asset_id],
      [SECOND_PICTURE.asset.asset_id],
    ]);
  });

  it("does nothing without an opening", async () => {
    const maxExamBytes = vi.fn(async () => LIMIT);
    const { newPictures, read, service, scope } = setupWithRead(
      async () => ({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() }),
      { maxExamBytes },
    );
    scope.close();
    const target = stubTarget();

    await service.add(target, [pictureFile()]);

    expect(maxExamBytes).not.toHaveBeenCalled();
    expect(read).not.toHaveBeenCalled();
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
  });
});
