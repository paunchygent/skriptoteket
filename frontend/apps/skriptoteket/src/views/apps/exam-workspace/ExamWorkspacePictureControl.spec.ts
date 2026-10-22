/**
 * Exam workspace picture control: the question body editor.
 *
 * Expected behavior (TASK-SKRIPT-39-10-04, unit U6):
 *   - Insert at the caret puts the picture in its own paragraph and the
 *     emitted body declares the asset in the same update (the owner records
 *     both through `newPictures.withDeclared`).
 *   - Replace of a selected picture emits the new id in place ("Byt bild").
 *   - A refused type and a refused size emit no update and show the notice.
 *
 * The service is the real `createExamWorkspacePictureService` over the real
 * `readPicture` with the shared stubbed platform; the registry is the real
 * `createExamWorkspaceNewPictures`. Mounts are the real BodyEditor with the
 * service provided, as the editor pane provides it. Where a refusal shows and
 * clears, and how an accepted picture reaches the save, live in the
 * `.notices` and `.saves` splits.
 */

import type { VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import { buildGapItem } from "./ExamWorkspaceBodyEditor.specSupport";
import { RED_PNG_PICTURE, TRANSPARENT_PNG_PICTURE } from "./examWorkspacePictureFixtures.specSupport";
import { installGuestStoreObjectUrls } from "./examWorkspaceGuestStore.specSupport";
import {
  assetSegmentId,
  choosePicture,
  docWith,
  editorOf,
  freeTextItem,
  mountBody,
  pictureFile,
  picturePos,
  posIn,
  SIZE_COPY,
  standAloneService,
  textFile,
  TYPE_COPY,
} from "./examWorkspacePictureControl.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

installGuestStoreObjectUrls();

let mounted: VueWrapper | null = null;

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
});

/** The gap item's body with its picture segment pointing at the old fixture picture. */
function itemWithOldPicture(oldAssetId: string): NativeExamItem {
  const base = buildGapItem();
  return {
    ...base,
    body: base.body.map((paragraph) => ({
      ...paragraph,
      segments: paragraph.segments.map((segment) =>
        segment.kind === "asset" ? { kind: "asset" as const, asset_id: oldAssetId } : segment,
      ),
    })),
  };
}

describe("ExamWorkspacePictureControl", () => {
  it("inserts at the caret in its own paragraph and declares the asset in the same update", async () => {
    const item = freeTextItem();
    const { newPictures, service } = standAloneService(item);
    const wrapper = mountBody(item, service);
    mounted = wrapper;
    await nextTick();
    await nextTick();

    const editor = editorOf(wrapper, "exam-workspace-body-editor-surface");
    editor.commands.setTextSelection(posIn(editor, "antalet.", "antalet.".length));
    await choosePicture(wrapper, pictureFile(TRANSPARENT_PNG_PICTURE));

    const body = wrapper.findComponent(ExamWorkspaceBodyEditor);
    const updates = body.emitted("updateBody") as
      | Array<[string, NativeExamItem["body"], boolean]>
      | undefined;
    expect(updates).toHaveLength(1);
    const [, emittedBody, structural] = updates![0]!;
    expect(structural).toBe(true);
    expect(emittedBody).toHaveLength(3);
    expect(emittedBody[0]!.segments.map((segment) => segment.kind)).toEqual(["text"]);
    expect(emittedBody[1]!.segments).toHaveLength(1);
    const assetId = assetSegmentId(emittedBody);
    expect(assetId).toMatch(/^asset_[0-9a-f]{16}$/);

    const declared = newPictures.withDeclared(docWith({ ...item, body: emittedBody }));
    expect(declared.assets.map((entry) => entry.asset_id)).toEqual([assetId]);
    expect(newPictures.bytesFor(declared)[assetId!]).toBeInstanceOf(Blob);
  });

  it("replaces the selected picture in place and offers Byt bild", async () => {
    const oldAssetId = TRANSPARENT_PNG_PICTURE.asset.asset_id;
    const item = itemWithOldPicture(oldAssetId);
    const { newPictures, service } = standAloneService(item, [TRANSPARENT_PNG_PICTURE.asset]);
    const wrapper = mountBody(item, service, { [oldAssetId]: "blob:picture" });
    mounted = wrapper;
    await nextTick();
    await nextTick();

    const surface = wrapper.get('[data-test="exam-workspace-body-editor-surface"]').element as HTMLElement;
    surface.focus();
    await nextTick();
    const editor = editorOf(wrapper, "exam-workspace-body-editor-surface");
    editor.commands.setNodeSelection(picturePos(editor));
    await nextTick();
    expect(wrapper.get('[data-test="exam-workspace-picture-tool"]').attributes("aria-label")).toBe(
      "Byt bild",
    );

    await choosePicture(wrapper, pictureFile(RED_PNG_PICTURE, "ny.png"));

    const body = wrapper.findComponent(ExamWorkspaceBodyEditor);
    const updates = body.emitted("updateBody") as
      | Array<[string, NativeExamItem["body"], boolean]>
      | undefined;
    expect(updates).toHaveLength(1);
    const emittedBody = updates![0]![1];
    expect(emittedBody).toHaveLength(item.body.length);
    const replaced = assetSegmentId(emittedBody);
    expect(replaced).not.toBe(oldAssetId);
    expect(replaced).toMatch(/^asset_[0-9a-f]{16}$/);
    const declared = newPictures.withDeclared(docWith({ ...item, body: emittedBody }));
    expect(declared.assets.map((entry) => entry.asset_id)).toEqual([replaced]);
  });

  it("emits no update and keeps the notice on a refused file type", async () => {
    const item = freeTextItem();
    const { service } = standAloneService(item);
    const wrapper = mountBody(item, service);
    mounted = wrapper;
    await nextTick();
    await nextTick();

    await choosePicture(wrapper, textFile());

    const body = wrapper.findComponent(ExamWorkspaceBodyEditor);
    expect(body.emitted("updateBody")).toBeUndefined();
    expect(service.notice.value).toEqual({ kind: "refused", text: TYPE_COPY });
    expect(service.busy.value).toBe(false);
  });

  it("emits no update and keeps the notice on a refused file size", async () => {
    const item = freeTextItem();
    // The filler keeps the fixture's id and digest but inflates its byte
    // length to stand in for a nearly full exam; only a rejection case does this.
    const { service } = standAloneService(item, [
      { ...RED_PNG_PICTURE.asset, byte_length: 19_999_990 },
    ]);
    const wrapper = mountBody(item, service);
    mounted = wrapper;
    await nextTick();
    await nextTick();

    await choosePicture(wrapper, pictureFile(TRANSPARENT_PNG_PICTURE, "stor.png"));

    const body = wrapper.findComponent(ExamWorkspaceBodyEditor);
    expect(body.emitted("updateBody")).toBeUndefined();
    expect(service.notice.value).toEqual({ kind: "refused", text: SIZE_COPY });
  });
});
