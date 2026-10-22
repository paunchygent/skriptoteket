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
import { PICTURE_LIMIT_UNAVAILABLE_COPY } from "./examWorkspacePictureIntake";
import type { PictureIntake, PictureIntakeOptions } from "./examWorkspacePictureIntake";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";

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
/** The server-owned limit the loader double reports; the service memoizes it per service. */
const LIMIT = 20_000_000;

function stubTarget(acceptsPictures = true) {
  return {
    marks: ref([]) as Ref<BodyMark[]>,
    headingLevel: () => null,
    toggleMark: vi.fn(),
    toggleHeading: vi.fn(),
    makeGap: vi.fn(),
    acceptsPictures,
    selectedPictureId: ref(null),
    placePicture: vi.fn((_assetId: string): void => undefined),
    isLive: vi.fn((): boolean => true),
    release: vi.fn(),
  };
}

/** One opening the service binds an `add` to; retiring swaps the live opening. */
function liveOpening() {
  const first: ExamWorkspaceOpening = { lineageId: "lineage-a" };
  const second: ExamWorkspaceOpening = { lineageId: "lineage-b" };
  const state = { current: first as ExamWorkspaceOpening | null };
  return {
    first,
    second,
    opening: (): ExamWorkspaceOpening | null => state.current,
    isOpen: (opening: ExamWorkspaceOpening): boolean => state.current === opening,
    retire: (): void => {
      state.current = second;
    },
    close: (): void => {
      state.current = null;
    },
    state,
  };
}

function setup(options?: {
  canEdit?: boolean;
  document?: NativeExamDocument | null;
  read?: (file: Blob, document: NativeExamDocument) => Promise<PictureIntake>;
  maxExamBytes?: () => Promise<number>;
}) {
  const newPictures = { declare: vi.fn() };
  const scope = liveOpening();
  const read =
    options?.read ??
    (async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }) as PictureIntake);
  const service = createExamWorkspacePictureService({
    document: () => (options?.document === undefined ? DOCUMENT : options.document),
    newPictures,
    canEdit: () => options?.canEdit ?? true,
    opening: scope.opening,
    isOpen: scope.isOpen,
    maxExamBytes: options?.maxExamBytes ?? (async () => LIMIT),
    read: read as typeof import("./examWorkspacePictureIntake").readPicture,
  });
  return { newPictures, service, scope };
}

function setupWithRead(
  read: (
    file: Blob,
    document: NativeExamDocument,
    options: PictureIntakeOptions,
  ) => Promise<PictureIntake>,
  options?: {
    canEdit?: boolean;
    document?: NativeExamDocument | null;
    maxExamBytes?: () => Promise<number>;
    scope?: ReturnType<typeof liveOpening>;
  },
) {
  const wrapped = vi.fn(read);
  const newPictures = { declare: vi.fn() };
  const scope = options?.scope ?? liveOpening();
  const service = createExamWorkspacePictureService({
    document: () => (options?.document === undefined ? DOCUMENT : options.document),
    newPictures,
    canEdit: () => options?.canEdit ?? true,
    opening: scope.opening,
    isOpen: scope.isOpen,
    maxExamBytes: options?.maxExamBytes ?? (async () => LIMIT),
    read: wrapped as typeof import("./examWorkspacePictureIntake").readPicture,
  });
  return { newPictures, read: wrapped, service, scope };
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
    const { read, service } = setupWithRead(
      () =>
        new Promise<PictureIntake>((resolve) => {
          resolveRead = resolve;
        }),
    );
    const target = stubTarget();

    const pending = service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);
    expect(service.busy.value).toBe(true);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
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
    await vi.waitFor(() => expect(read).toHaveBeenCalledTimes(1));
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

  it("passes the selected picture id as replacing, and null without a selection", async () => {
    const { read, service } = setupWithRead(
      async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }),
    );
    const selected = stubTarget();
    (selected.selectedPictureId as Ref<string | null>).value = "asset_old";
    const plain = stubTarget();
    const file = new File(["png!"], "bild.png", { type: "image/png" });

    await service.add(selected, [file]);
    await service.add(plain, [file]);

    expect(read).toHaveBeenCalledTimes(2);
    expect(read.mock.calls[0]?.[2]).toEqual({ maxExamBytes: LIMIT, replacing: "asset_old" });
    expect(read.mock.calls[1]?.[2]).toEqual({ maxExamBytes: LIMIT, replacing: null });
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

    await service.add(target, [new File(["a"], "a.png"), new File(["b"], "b.png")]);

    expect(read.mock.calls.map((call) => call[1])).toEqual([first, second]);
    expect(target.placePicture.mock.calls).toEqual([["asset_first"], ["asset_second"]]);
  });

  it("does nothing without an opening", async () => {
    const maxExamBytes = vi.fn(async () => LIMIT);
    const { newPictures, read, service, scope } = setupWithRead(
      async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }),
      { maxExamBytes },
    );
    scope.close();
    const target = stubTarget();

    await service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);

    expect(maxExamBytes).not.toHaveBeenCalled();
    expect(read).not.toHaveBeenCalled();
    expect(newPictures.declare).not.toHaveBeenCalled();
    expect(target.placePicture).not.toHaveBeenCalled();
  });
});

describe("createExamWorkspacePictureService limit loading", () => {
  it("hands the loaded limit to the read", async () => {
    const { read, service } = setupWithRead(
      async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }),
      { maxExamBytes: async () => 7_000_000 },
    );

    await service.add(stubTarget(), [new File(["png!"], "bild.png", { type: "image/png" })]);

    expect(read.mock.calls[0]?.[2]).toEqual({ maxExamBytes: 7_000_000, replacing: null });
  });

  it("loads the limit once across two adds", async () => {
    const maxExamBytes = vi.fn(async () => LIMIT);
    const { service } = setupWithRead(
      async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }),
      { maxExamBytes },
    );
    const file = new File(["png!"], "bild.png", { type: "image/png" });

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
      async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }),
      { maxExamBytes },
    );
    const target = stubTarget();
    const file = new File(["png!"], "bild.png", { type: "image/png" });

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
      async () => ({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB }),
      { maxExamBytes },
    );
    const target = stubTarget();

    const pending = service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);
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

describe("createExamWorkspacePictureService stale intakes", () => {
  it("retires the intake when the opening changes while a read is pending", async () => {
    let resolveRead!: (intake: PictureIntake) => void;
    const { newPictures, read, service, scope } = setupWithRead(
      () => new Promise<PictureIntake>((resolve) => { resolveRead = resolve; }),
    );
    const target = stubTarget();

    const pending = service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
    scope.retire();
    resolveRead({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB });
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

    const pending = service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
    canEdit = false;
    resolveRead({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB });
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

    const pending = service.add(target, [new File(["png!"], "bild.png", { type: "image/png" })]);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
    target.isLive.mockReturnValue(false);
    resolveRead({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB });
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
      new File(["a"], "a.png", { type: "image/png" }),
      new File(["b"], "b.png", { type: "image/png" }),
    ]);
    await vi.waitFor(() => expect(read).toHaveBeenCalledTimes(1));
    resolveFirst({ kind: "picture", asset: asset(ASSET_ID), blob: BLOB });
    await pending;

    expect(read).toHaveBeenCalledTimes(1);
    expect(target.placePicture).toHaveBeenCalledTimes(1);
    expect(target.placePicture).toHaveBeenCalledWith(ASSET_ID);
    expect(newPictures.declare).toHaveBeenCalledTimes(1);
    expect(service.notice.value).toBeNull();
  });

  it("keeps the notice unchanged when a refusal arrives after the opening changed", async () => {
    let resolveRead!: (intake: PictureIntake) => void;
    const { read, service, scope } = setupWithRead(
      () => new Promise<PictureIntake>((resolve) => { resolveRead = resolve; }),
    );
    const target = stubTarget();
    service.notice.value = { kind: "refused", text: TYPE_COPY } as ExamWorkspaceNotice;

    const pending = service.add(target, [new File(["hej"], "text.txt", { type: "text/plain" })]);
    await vi.waitFor(() => expect(read).toHaveBeenCalled());
    scope.retire();
    resolveRead({ kind: "refused", copy: SIZE_COPY });
    await pending;

    expect(service.notice.value).toEqual({ kind: "refused", text: TYPE_COPY });
    expect(target.placePicture).not.toHaveBeenCalled();
  });
});
