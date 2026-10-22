/**
 * Exam workspace picture service spec support.
 *
 * Domain purpose:
 *   The one shared setup the picture service specs run through: coherent
 *   accepted pictures from the fixture bytes with their digest-matched asset
 *   records, a complete typed open document, and the target/opening doubles
 *   each `add` binds to.
 *
 * Relationships:
 *   - Consumed by `examWorkspacePictureService` and its `.limit` and
 *     `.lifetime` splits; every split builds its scenario through this module
 *     so the fixtures stay identical.
 *   - Accepted cases use the fixtures in `examWorkspacePictureFixtures`
 *     (real bytes, digest-matched asset records, `blob()`); files handed to an
 *     accepted read are built from a fixture's bytes. Rejection cases keep
 *     their deliberately malformed files (a text file) where they are.
 */

import { vi } from "vitest";
import { ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { createExamWorkspacePictureService } from "./examWorkspacePictureService";
import type { PictureIntake, PictureIntakeOptions } from "./examWorkspacePictureIntake";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  RED_PNG_PICTURE,
  TRANSPARENT_PNG_PICTURE,
  type ExamWorkspacePictureFixture,
} from "./examWorkspacePictureFixtures.specSupport";

export const TYPE_COPY = "Bilden lades inte till. Välj en PNG- eller JPEG-bild.";
export const SIZE_COPY =
  "Bilden lades inte till. Provet får vara högst 20 MB med alla bilder. Välj en mindre bild.";

/** The accepted picture every `add` declares, and the second one batch cases place after it. */
export const FIRST_PICTURE = TRANSPARENT_PNG_PICTURE;
export const SECOND_PICTURE = RED_PNG_PICTURE;

/** A complete typed open document; scenarios override only its assets. */
export const DOCUMENT: NativeExamDocument = buildParentDocument();
/** The server-owned limit the loader double reports; the service memoizes it per service. */
export const LIMIT = 20_000_000;

/** The chosen file's name, or "" for a bare Blob. */
export function nameOf(file: Blob): string {
  return file instanceof File ? file.name : "";
}

/** A chosen file holding a fixture's exact bytes. */
export function pictureFile(fixture: ExamWorkspacePictureFixture = FIRST_PICTURE, name = "bild.png"): File {
  const file = new File([fixture.bytes], name, { type: fixture.mediaType });
  // jsdom's Blob has no `arrayBuffer`; equip the file like the production file path provides.
  Object.defineProperty(file, "arrayBuffer", {
    configurable: true,
    value: async (): Promise<ArrayBuffer> => {
      const copy = new Uint8Array(fixture.bytes.length);
      copy.set(fixture.bytes);
      return copy.buffer;
    },
  });
  return file;
}

export function stubTarget(acceptsPictures = true) {
  return {
    marks: ref<BodyMark[]>([]),
    headingLevel: () => null,
    toggleMark: vi.fn(),
    toggleHeading: vi.fn(),
    makeGap: vi.fn(),
    acceptsPictures,
    selectedPictureId: ref<string | null>(null),
    placePicture: vi.fn((_assetId: string): void => undefined),
    isLive: vi.fn((): boolean => true),
    release: vi.fn(),
  };
}

/** One opening the service binds an `add` to; retiring swaps the live opening. */
export function liveOpening() {
  const first: ExamWorkspaceOpening = { lineageId: "lineage-a" };
  const second: ExamWorkspaceOpening = { lineageId: "lineage-b" };
  const state: { current: ExamWorkspaceOpening | null } = { current: first };
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

export function setup(options?: {
  canEdit?: boolean;
  document?: NativeExamDocument | null;
  read?: (file: Blob, document: NativeExamDocument) => Promise<PictureIntake>;
  maxExamBytes?: () => Promise<number>;
}) {
  const newPictures = { declare: vi.fn() };
  const scope = liveOpening();
  const read =
    options?.read ??
    (async () => ({ kind: "picture", asset: FIRST_PICTURE.asset, blob: FIRST_PICTURE.blob() }) as PictureIntake);
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

export function setupWithRead(
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
