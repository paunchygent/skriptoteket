/**
 * Exam workspace picture service stale intakes.
 *
 * Expected behavior (TASK-SKRIPT-39-10-04, unit U6, repair R5 for review F3):
 *   One `add` belongs to the opening it started in: a read that resolves
 *   after the opening changed, after editing was disabled, or after the
 *   target stopped being live declares nothing, places nothing, and leaves
 *   the notice unchanged. A batch stops at the same boundary without reading
 *   the next file.
 */

import { describe, expect, it, vi } from "vitest";

import { createExamWorkspacePictureService } from "./examWorkspacePictureService";
import type { PictureIntake } from "./examWorkspacePictureIntake";
import {
  DOCUMENT,
  FIRST_PICTURE,
  LIMIT,
  liveOpening,
  pictureFile,
  setupWithRead,
  SIZE_COPY,
  stubTarget,
  TYPE_COPY,
} from "./examWorkspacePictureService.specSupport";

describe("createExamWorkspacePictureService stale intakes", () => {
  it("retires the intake when the opening changes while a read is pending", async () => {
    let resolveRead!: (intake: PictureIntake) => void;
    const { newPictures, read, service, scope } = setupWithRead(
      () => new Promise<PictureIntake>((resolve) => { resolveRead = resolve; }),
    );
    const target = stubTarget();

    const pending = service.add(target, [pictureFile()]);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
    scope.retire();
    resolveRead({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() });
    await pending;

    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
    expect(service.notice.value).toBeNull();
    expect(service.busy.value).toBe(false);
  });

  it("retires the intake when editing is disabled while a read is pending", async () => {
    let canEdit = true;
    let resolveRead!: (intake: PictureIntake) => void;
    const scope = liveOpening();
    const newPictures = { declare: vi.fn() };
    const read = vi.fn(
      () => new Promise<PictureIntake>((resolve) => { resolveRead = resolve; }),
    );
    const service = createExamWorkspacePictureService({
      document: () => DOCUMENT,
      newPictures,
      canEdit: () => canEdit,
      opening: scope.opening,
      isOpen: scope.isOpen,
      maxExamBytes: async () => LIMIT,
      read: read as typeof import("./examWorkspacePictureIntake").readPicture,
    });
    const target = stubTarget();

    const pending = service.add(target, [pictureFile()]);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
    canEdit = false;
    resolveRead({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() });
    await pending;

    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
    expect(service.notice.value).toBeNull();
  });

  it("retires the intake when the target stops being live while a read is pending", async () => {
    let resolveRead!: (intake: PictureIntake) => void;
    const { newPictures, read, service } = setupWithRead(
      () => new Promise<PictureIntake>((resolve) => { resolveRead = resolve; }),
    );
    const target = stubTarget();

    const pending = service.add(target, [pictureFile()]);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
    target.isLive.mockReturnValue(false);
    resolveRead({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() });
    await pending;

    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
    expect(service.notice.value).toBeNull();
  });

  it("places only the first file when the opening changes mid-batch and never reads the second", async () => {
    let resolveFirst!: (intake: PictureIntake) => void;
    const { newPictures, read, service, scope } = setupWithRead(
      () => new Promise<PictureIntake>((resolve) => { resolveFirst = resolve; }),
    );
    const target = stubTarget();
    target.placePicture.mockImplementation(() => {
      scope.retire();
    });

    const pending = service.add(target, [
      pictureFile(FIRST_PICTURE, "a.png"),
      pictureFile(FIRST_PICTURE, "b.png"),
    ]);
    await vi.waitFor(() => expect(read).toHaveBeenCalledTimes(1));
    resolveFirst({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() });
    await pending;

    expect(read).toHaveBeenCalledTimes(1);
    expect(target.placePicture).toHaveBeenCalledTimes(1);
    expect(target.placePicture).toHaveBeenCalledWith(FIRST_PICTURE.asset.asset_id);
    expect(newPictures.declare).toHaveBeenCalledTimes(1);
    expect(service.notice.value).toBeNull();
  });

  it("keeps the notice unchanged when a refusal arrives after the opening changed", async () => {
    let resolveRead!: (intake: PictureIntake) => void;
    const { read, service, scope } = setupWithRead(
      () => new Promise<PictureIntake>((resolve) => { resolveRead = resolve; }),
    );
    const target = stubTarget();
    service.notice.value = { kind: "refused", text: TYPE_COPY };

    const pending = service.add(target, [new File(["hej"], "text.txt", { type: "text/plain" })]);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
    scope.retire();
    resolveRead({ kind: "refused", copy: SIZE_COPY });
    await pending;

    expect(service.notice.value).toEqual({ kind: "refused", text: TYPE_COPY });
    expect(target.placePicture).not.toHaveBeenCalled();
  });
});
