/**
 * Exam workspace picture service limit loading.
 *
 * Expected behavior (TASK-SKRIPT-39-10-04, unit U6):
 *   The service hands the server-owned whole-exam cap to each read, loads it
 *   once per service, shows the unavailable copy when the load fails (placing
 *   nothing) and asks again on the next `add`, and reads nothing when the
 *   opening changes while the limit loads.
 */

import { describe, expect, it, vi } from "vitest";

import { PICTURE_LIMIT_UNAVAILABLE_COPY } from "./examWorkspacePictureIntake";
import {
  FIRST_PICTURE,
  LIMIT,
  pictureFile,
  setupWithRead,
  stubTarget,
} from "./examWorkspacePictureService.specSupport";

describe("createExamWorkspacePictureService limit loading", () => {
  it("hands the loaded limit to the read", async () => {
    const { read, service } = setupWithRead(
      async () => ({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() }),
      { maxExamBytes: async () => 7_000_000 },
    );

    await service.add(stubTarget(), [pictureFile()]);

    expect(read.mock.calls[0]?.[2]).toEqual({ maxExamBytes: 7_000_000, replacing: null });
  });

  it("loads the limit once across two adds", async () => {
    const maxExamBytes = vi.fn(async () => LIMIT);
    const { service } = setupWithRead(
      async () => ({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() }),
      { maxExamBytes },
    );
    const file = pictureFile();

    await service.add(stubTarget(), [file]);
    await service.add(stubTarget(), [file]);

    expect(maxExamBytes).toHaveBeenCalledTimes(1);
  });

  it("shows the unavailable copy on a rejected load, places nothing, and asks again", async () => {
    const maxExamBytes = vi
      .fn<() => Promise<number>>()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue(LIMIT);
    const { newPictures, service } = setupWithRead(
      async () => ({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() }),
      { maxExamBytes },
    );
    const target = stubTarget();
    const file = pictureFile();

    await service.add(target, [file]);

    expect(service.notice.value).toEqual({ kind: "refused", text: PICTURE_LIMIT_UNAVAILABLE_COPY });
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
    expect(service.busy.value).toBe(false);

    await service.add(target, [file]);

    expect(maxExamBytes).toHaveBeenCalledTimes(2);
    expect(target.placePicture).toHaveBeenCalledTimes(1);
    expect(service.notice.value).toBeNull();
  });

  it("reads and places nothing when the opening changes while the limit loads", async () => {
    let resolveLimit!: (limit: number) => void;
    const maxExamBytes = vi.fn(() => new Promise<number>((resolve) => { resolveLimit = resolve; }));
    const { newPictures, read, service, scope } = setupWithRead(
      async () => ({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() }),
      { maxExamBytes },
    );
    const target = stubTarget();

    const pending = service.add(target, [pictureFile()]);
    scope.retire();
    resolveLimit(LIMIT);
    await pending;

    expect(read).not.toHaveBeenCalled();
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
    expect(service.notice.value).toBeNull();
    expect(service.busy.value).toBe(false);
  });
});
