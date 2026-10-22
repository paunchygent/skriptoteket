/**
 * Exam workspace picture control spec support.
 *
 * Domain purpose:
 *   The one shared setup the picture control specs mount through: coherent
 *   picture files built from the fixture bytes, the intake doubles that digest
 *   those bytes to their fixture asset records, typed documents, and the
 *   mount/target helpers for the real body editor and picture service.
 *
 * Relationships:
 *   - Consumed by `ExamWorkspacePictureControl` and its `.notices` and
 *     `.saves` splits; every split builds its scenario through this module so
 *     the fixtures stay identical.
 *   - Accepted-case pictures come from `examWorkspacePictureFixtures` (real
 *     bytes, digest-matched asset records); rejection cases keep their
 *     deliberately malformed files (a text file) where they are.
 *   - `vi.mock`/`vi.hoisted` blocks stay in each spec that needs them (Vitest
 *     hoists them per file); a helper that needs a mocked module takes it as
 *     a parameter.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
import { defineComponent, h, nextTick, ref } from "vue";
import { vi } from "vitest";

import type {
  NativeExamAsset,
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import { createExamWorkspaceNewPictures } from "./examWorkspaceNewPictures";
import { createExamWorkspacePictureService } from "./examWorkspacePictureService";
import { provideExamWorkspacePictures } from "./examWorkspacePictureService";
import type { ExamWorkspacePictureService } from "./examWorkspacePictureService";
import { readPicture } from "./examWorkspacePictureIntake";
import type { PictureIntakeDeps } from "./examWorkspacePictureIntake";
import { EXAM_PICTURE_NODE } from "./examWorkspaceRichTextSchema";
import type { RichTextTarget } from "./examWorkspaceRichTextTarget";
import { newTeacherItem, withBody } from "./examWorkspaceItemEdits";
import { plainBody } from "./examWorkspaceRichText";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import type { ExamWorkspaceItemEntry } from "./examWorkspaceListEntries";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import type { GuestEditLeaseChannel } from "./examWorkspaceGuestEditLease";
import { exam } from "./useExamWorkspaceEditing.history.specSupport";
import {
  RED_PNG_PICTURE,
  TRANSPARENT_PNG_PICTURE,
  WHITE_JPEG_PICTURE,
  type ExamWorkspacePictureFixture,
} from "./examWorkspacePictureFixtures.specSupport";

export const TYPE_COPY = "Bilden lades inte till. Välj en PNG- eller JPEG-bild.";
export const SIZE_COPY =
  "Bilden lades inte till. Provet får vara högst 20 MB med alla bilder. Välj en mindre bild.";
/** The server-owned limit the pane's store double reports for the mounted pane cases. */
export const LIMIT_BYTES = 20_000_000;

export function limitStore(): ExamWorkspaceStore {
  return {
    ...serverExamWorkspaceStore,
    shared: {
      ...serverExamWorkspaceStore.shared,
      getExamWorkspaceLimits: async () => ({ max_exam_bytes: LIMIT_BYTES }),
    },
  };
}

/**
 * jsdom's Blob has no `arrayBuffer`; equip each test file with one holding the
 * exact bytes, like the production file path provides.
 */
export function withBytes(file: File, bytes: Uint8Array): File {
  Object.defineProperty(file, "arrayBuffer", {
    configurable: true,
    value: async (): Promise<ArrayBuffer> => {
      const copy = new Uint8Array(bytes.length);
      copy.set(bytes);
      return copy.buffer;
    },
  });
  return file;
}

/** A chosen file holding a fixture's exact bytes, so the intake digests it to the fixture's asset. */
export function pictureFile(fixture: ExamWorkspacePictureFixture, name = "bild.png"): File {
  return withBytes(new File([fixture.bytes], name, { type: fixture.mediaType }), fixture.bytes);
}

export function textFile(name = "text.txt"): File {
  const bytes = new TextEncoder().encode("hej");
  return withBytes(new File([bytes as BlobPart], name, { type: "text/plain" }), bytes);
}

function bytesEqual(left: Uint8Array, right: Uint8Array): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

const KNOWN_PICTURES = [TRANSPARENT_PNG_PICTURE, RED_PNG_PICTURE, WHITE_JPEG_PICTURE];

/** The intake's stubbed platform for files outside the fixtures: an 8x8 picture, and a digest of the input bytes. */
export const stubDeps: PictureIntakeDeps = {
  decodeSize: async () => ({ width: 8, height: 8 }),
  digest: async (data: ArrayBuffer) => {
    const view = new Uint8Array(data);
    const out = new Uint8Array(32).fill(view.length);
    out[0] = view[view.length - 1] ?? 0;
    return out.buffer;
  },
};

function bufferOfHex(hex: string): ArrayBuffer {
  const bytes = new Uint8Array(hex.length / 2);
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = Number.parseInt(hex.slice(index * 2, index * 2 + 2), 16);
  }
  return bytes.buffer;
}

/**
 * Read through the real intake: a file built from a fixture's bytes is
 * checked with that fixture's pixel size and digest, so an accepted file
 * becomes its fixture's asset record; anything else uses the generic platform.
 */
export async function read(file: Blob, document: NativeExamDocument) {
  let matched: ExamWorkspacePictureFixture | null = null;
  try {
    const view = new Uint8Array(await file.arrayBuffer());
    matched = KNOWN_PICTURES.find((candidate) => bytesEqual(view, candidate.bytes)) ?? null;
  } catch {
    matched = null;
  }
  const picture = matched;
  const deps: PictureIntakeDeps =
    picture === null
      ? stubDeps
      : {
          decodeSize: async () => ({ width: picture.width, height: picture.height }),
          digest: async () => bufferOfHex(picture.asset.sha256),
        };
  return readPicture(file, document, { maxExamBytes: LIMIT_BYTES, replacing: null }, deps);
}

export function docWith(item: NativeExamItem, assets: NativeExamAsset[] = []): NativeExamDocument {
  return {
    ...exam("Prov", 1),
    assets,
    items: [item],
  };
}

/** A no-op guest lease channel: takeover answers arrive only via the heartbeat poll. */
export function channel(): GuestEditLeaseChannel {
  return {
    addEventListener() {},
    close() {},
    postMessage() {},
    removeEventListener() {},
  };
}

/** Choose `file` in the host's picture control. */
export async function choosePicture(host: VueWrapper, file: File): Promise<void> {
  const input = host.get('[data-test="exam-workspace-picture-input"]');
  Object.defineProperty(input.element as HTMLInputElement, "files", {
    value: [file],
    configurable: true,
  });
  await input.trigger("change");
  await flushPromises();
  await nextTick();
}

export function editorOf(host: VueWrapper, testId: string): Editor {
  const surface = host.get(`[data-test="${testId}"]`).element as HTMLElement & { editor?: Editor };
  if (!surface.editor) {
    throw new Error(`no editor behind ${testId}`);
  }
  return surface.editor;
}

/** The position of the first picture atom. */
export function picturePos(editor: Editor): number {
  let found = -1;
  editor.state.doc.descendants((node, pos) => {
    if (found < 0 && node.type.name === EXAM_PICTURE_NODE) {
      found = pos;
    }
    return found < 0;
  });
  if (found < 0) {
    throw new Error("no picture");
  }
  return found;
}

/** Position `offset` characters into the first text node that contains `needle`. */
export function posIn(editor: Editor, needle: string, offset: number): number {
  let found = -1;
  editor.state.doc.descendants((node, pos) => {
    if (found < 0 && node.isText && node.text?.includes(needle)) {
      found = pos + (node.text.indexOf(needle) + offset);
    }
    return found < 0;
  });
  if (found < 0) {
    throw new Error(`no text "${needle}"`);
  }
  return found;
}

/** The first asset segment's id in `body`, narrowed through the segment union. */
export function assetSegmentId(
  body: NativeExamItem["body"] | NativeExamBodyParagraph[],
): string | undefined {
  for (const paragraph of body) {
    for (const segment of paragraph.segments) {
      if (segment.kind === "asset") {
        return segment.asset_id;
      }
    }
  }
  return undefined;
}

export function freeTextItem(): NativeExamItem {
  return withBody(newTeacherItem("item_001", 1, "free_text"), plainBody("Diagrammet visar antalet."));
}

export function standAloneService(item: NativeExamItem, assets: NativeExamAsset[] = []) {
  const document = ref<NativeExamDocument | null>(docWith(item, assets));
  const newPictures = createExamWorkspaceNewPictures(() => document.value);
  const opening = { lineageId: "control-lineage" };
  const service = createExamWorkspacePictureService({
    document: () => document.value,
    newPictures,
    canEdit: () => true,
    opening: () => opening,
    isOpen: (candidate) => candidate === opening,
    maxExamBytes: async () => LIMIT_BYTES,
    read,
  });
  return { document, newPictures, service };
}

export function mountBody(item: NativeExamItem, service: ExamWorkspacePictureService, assetUrls: Record<string, string> = {}) {
  const Host = defineComponent({
    setup() {
      provideExamWorkspacePictures(service);
      return () => h(ExamWorkspaceBodyEditor, { item, assetUrls });
    },
  });
  return mount(Host, { attachTo: document.body });
}

export function stubTarget() {
  const placePicture = vi.fn((_assetId: string): void => undefined);
  const target: RichTextTarget = {
    marks: ref<BodyMark[]>([]),
    headingLevel: () => null,
    toggleMark: vi.fn(),
    toggleHeading: vi.fn(),
    makeGap: vi.fn(),
    acceptsPictures: true,
    selectedPictureId: ref<string | null>(null),
    placePicture,
    isLive: () => true,
    release: vi.fn(),
  };
  return { placePicture, target };
}

/** One pane entry for `item`, like the editor pane lists its questions. */
export function entryFor(item: NativeExamItem, label = "1"): ExamWorkspaceItemEntry {
  return {
    kind: "item",
    id: item.item_id,
    label,
    parentId: null,
    text: "Fråga",
    typeLabel: "Fritext",
    itemKind: item.kind,
    points: 2,
    problem: null,
    aiKey: null,
    status: "ok",
  };
}
