/**
 * Exam workspace picture control: the service, the toolbar and the four editors.
 *
 * Expected behavior (TASK-SKRIPT-39-10-04, unit U6):
 *   - Insert at the caret puts the picture in its own paragraph and the
 *     emitted body declares the asset in the same update (the owner records
 *     both through `newPictures.withDeclared`).
 *   - Replace of a selected picture emits the new id in place ("Byt bild").
 *   - A refused type and a refused size emit no update and show the notice.
 *   - The signed-in pane carries an accepted picture to the autosave once,
 *     shows a refusal at the top of the editor, clears it on dismiss and on
 *     selection change; the guest workspace carries it through the
 *     production `useExamWorkspaceEditing` with the guest store.
 *
 * The service is the real `createExamWorkspacePictureService` over the real
 * `readPicture` with stubbed decode and digest doubles; the registry is the
 * real `createExamWorkspaceNewPictures`. Mounts are the real BodyEditor and
 * ExamInstructionEditor with the service provided, as the editor pane
 * provides it.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";
import type { Ref } from "vue";

import type { NativeExamAsset, NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import { buildGapItem } from "./ExamWorkspaceBodyEditor.specSupport";
import ExamWorkspaceEditorPane from "./ExamWorkspaceEditorPane.vue";
import ExamWorkspaceExamInstructionEditor from "./ExamWorkspaceExamInstructionEditor.vue";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { buildRecordedParent } from "./examWorkspaceParentDocument.specSupport";
import { createExamWorkspaceNewPictures } from "./examWorkspaceNewPictures";
import { createExamWorkspacePictureService } from "./examWorkspacePictureService";
import { provideExamWorkspacePictures } from "./examWorkspacePictureService";
import type { ExamWorkspacePictureService } from "./examWorkspacePictureService";
import { readPicture } from "./examWorkspacePictureIntake";
import type { PictureIntake, PictureIntakeDeps } from "./examWorkspacePictureIntake";
import { EXAM_PICTURE_NODE } from "./examWorkspaceRichTextSchema";
import type { RichTextTarget } from "./examWorkspaceRichTextTarget";
import { newTeacherItem, withBody } from "./examWorkspaceItemEdits";
import { plainBody } from "./examWorkspaceRichText";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import type { ExamWorkspaceItemEntry } from "./examWorkspaceListEntries";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import {
  createGuestPublicApiMocks,
  createIds,
  DOCUMENT_ID,
  exam as guestExam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  liveAdmission,
} from "./examWorkspaceGuestStore.specSupport";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import { createExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./examWorkspaceGuestDraftStorage";
import { createInMemoryGuestEditLeaseStorage } from "./examWorkspaceGuestEditLeaseMemory";
import type { GuestEditLeaseChannel } from "./examWorkspaceGuestEditLease";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { exam, inScope, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";

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

const TYPE_COPY = "Bilden lades inte till. Välj en PNG- eller JPEG-bild.";
const SIZE_COPY =
  "Bilden lades inte till. Provet får vara högst 20 MB med alla bilder. Välj en mindre bild.";

let mounted: VueWrapper | null = null;

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
  stopScopes();
  vi.unstubAllGlobals();
});

/** PNG bytes with a trailing marker, so each file digests to its own asset id. */
function pngBytes(marker: number): Uint8Array {
  return new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, marker]);
}

/**
 * jsdom's Blob has no `arrayBuffer`; equip each test file with one holding the
 * exact bytes, like the production file path provides.
 */
function withBytes(file: File, bytes: Uint8Array): File {
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

function pngFile(marker: number, name = "bild.png"): File {
  const bytes = pngBytes(marker);
  return withBytes(new File([bytes as BlobPart], name, { type: "image/png" }), bytes);
}

function textFile(name = "text.txt"): File {
  const bytes = new TextEncoder().encode("hej");
  return withBytes(new File([bytes as BlobPart], name, { type: "text/plain" }), bytes);
}

/** The intake's stubbed platform: an 8x8 picture, and a digest of the input bytes. */
const stubDeps: PictureIntakeDeps = {
  decodeSize: async () => ({ width: 8, height: 8 }),
  digest: async (data: ArrayBuffer) => {
    const view = new Uint8Array(data);
    const out = new Uint8Array(32).fill(view.length);
    out[0] = view[view.length - 1] ?? 0;
    return out.buffer;
  },
};

function read(file: Blob, document: NativeExamDocument): Promise<PictureIntake> {
  return readPicture(file, document, stubDeps);
}

function docWith(item: NativeExamItem, assets: NativeExamAsset[] = []): NativeExamDocument {
  return {
    ...exam("Prov", 1),
    assets,
    items: [item],
  };
}

/** A no-op guest lease channel: takeover answers arrive only via the heartbeat poll. */
function channel(): GuestEditLeaseChannel {
  return {
    addEventListener() {},
    close() {},
    postMessage() {},
    removeEventListener() {},
  };
}

/** Choose `file` in the host's picture control. */
async function choosePicture(host: VueWrapper, file: File): Promise<void> {
  const input = host.get('[data-test="exam-workspace-picture-input"]');
  Object.defineProperty(input.element as HTMLInputElement, "files", {
    value: [file],
    configurable: true,
  });
  await input.trigger("change");
  await flushPromises();
  await nextTick();
}

function editorOf(host: VueWrapper, testId: string): Editor {
  const surface = host.get(`[data-test="${testId}"]`).element as HTMLElement & { editor?: Editor };
  if (!surface.editor) {
    throw new Error(`no editor behind ${testId}`);
  }
  return surface.editor;
}

/** The position of the first picture atom. */
function picturePos(editor: Editor): number {
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
function posIn(editor: Editor, needle: string, offset: number): number {
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

function freeTextItem(): NativeExamItem {
  return withBody(newTeacherItem("item_001", 1, "free_text"), plainBody("Diagrammet visar antalet."));
}

function standAloneService(item: NativeExamItem, assets: NativeExamAsset[] = []) {
  const document = ref<NativeExamDocument | null>(docWith(item, assets));
  const newPictures = createExamWorkspaceNewPictures();
  const service = createExamWorkspacePictureService({
    document: () => document.value,
    newPictures,
    canEdit: () => true,
    read,
  });
  return { document, newPictures, service };
}

function mountBody(item: NativeExamItem, service: ExamWorkspacePictureService, assetUrls: Record<string, string> = {}) {
  // eslint-disable-next-line vue/one-component-per-file -- spec host with the provided service
  const Host = defineComponent({
    setup() {
      provideExamWorkspacePictures(service);
      return () => h(ExamWorkspaceBodyEditor, { item, assetUrls });
    },
  });
  mounted = mount(Host, { attachTo: document.body });
  return mounted;
}

function stubTarget() {
  const placePicture = vi.fn((_assetId: string): void => undefined);
  const target: RichTextTarget = {
    marks: ref([]) as Ref<BodyMark[]>,
    headingLevel: () => null,
    toggleMark: vi.fn(),
    toggleHeading: vi.fn(),
    makeGap: vi.fn(),
    acceptsPictures: true,
    selectedPictureId: ref(null),
    placePicture,
    release: vi.fn(),
  };
  return { placePicture, target };
}

describe("ExamWorkspacePictureControl", () => {
  it("inserts at the caret in its own paragraph and declares the asset in the same update", async () => {
    const item = freeTextItem();
    const { newPictures, service } = standAloneService(item);
    const wrapper = mountBody(item, service);
    await nextTick();
    await nextTick();

    const editor = editorOf(wrapper, "exam-workspace-body-editor-surface");
    editor.commands.setTextSelection(posIn(editor, "antalet.", "antalet.".length));
    await choosePicture(wrapper, pngFile(1));

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
    const assetId = (emittedBody[1]!.segments[0] as { asset_id: string }).asset_id;
    expect(assetId).toMatch(/^asset_[0-9a-f]{16}$/);

    const declared = newPictures.withDeclared(docWith({ ...item, body: emittedBody }));
    expect(declared.assets.map((entry) => entry.asset_id)).toEqual([assetId]);
    expect(newPictures.bytesFor(declared)[assetId]).toBeInstanceOf(Blob);
  });

  it("replaces the selected picture in place and offers Byt bild", async () => {
    const item = buildGapItem();
    const { newPictures, service } = standAloneService(item);
    const wrapper = mountBody(item, service, { asset_001: "blob:picture" });
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

    await choosePicture(wrapper, pngFile(2));

    const body = wrapper.findComponent(ExamWorkspaceBodyEditor);
    const updates = body.emitted("updateBody") as
      | Array<[string, NativeExamItem["body"], boolean]>
      | undefined;
    expect(updates).toHaveLength(1);
    const emittedBody = updates![0]![1];
    expect(emittedBody).toHaveLength(item.body.length);
    const replaced = emittedBody[1]!.segments[1] as { asset_id: string };
    expect(replaced.asset_id).not.toBe("asset_001");
    expect(replaced.asset_id).toMatch(/^asset_[0-9a-f]{16}$/);
    const declared = newPictures.withDeclared(docWith({ ...item, body: emittedBody }));
    expect(declared.assets.map((entry) => entry.asset_id)).toEqual([replaced.asset_id]);
  });

  it("emits no update and keeps the notice on a refused file type", async () => {
    const item = freeTextItem();
    const { service } = standAloneService(item);
    const wrapper = mountBody(item, service);
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
    const { service } = standAloneService(item, [
      {
        asset_id: "asset_ffff",
        byte_length: 19_999_990,
        height: 1,
        media_type: "image/png",
        sha256: "f".repeat(64),
        width: 1,
      },
    ]);
    const wrapper = mountBody(item, service);
    await nextTick();
    await nextTick();

    await choosePicture(wrapper, pngFile(3));

    const body = wrapper.findComponent(ExamWorkspaceBodyEditor);
    expect(body.emitted("updateBody")).toBeUndefined();
    expect(service.notice.value).toEqual({ kind: "refused", text: SIZE_COPY });
  });

  it("inserts into the exam instruction and shows a refused file as the notice", async () => {
    const parent = buildRecordedParent();
    const { newPictures, service } = standAloneService(freeTextItem());
    // eslint-disable-next-line vue/one-component-per-file -- spec host with the provided service
    const Host = defineComponent({
      setup() {
        provideExamWorkspacePictures(service);
        return () =>
          h(ExamWorkspaceExamInstructionEditor, {
            instructions: parent.instruction,
            disabled: false,
            notice: service.notice.value,
          });
      },
    });
    mounted = mount(Host, { attachTo: document.body });
    await nextTick();
    await nextTick();

    await choosePicture(mounted, pngFile(4));

    const editor = mounted.findComponent(ExamWorkspaceExamInstructionEditor);
    const updates = editor.emitted("updateInstructions") as
      | Array<[NativeExamItem["body"], boolean]>
      | undefined;
    expect(updates).toHaveLength(1);
    const [emittedBody] = updates![0]!;
    const assetId = (
      emittedBody
        .flatMap((paragraph) => paragraph.segments)
        .find((segment) => segment.kind === "asset") as unknown as { asset_id: string } | undefined
    )?.asset_id;
    expect(assetId).toMatch(/^asset_[0-9a-f]{16}$/);
    const assetParagraphs = emittedBody.filter((paragraph) =>
      paragraph.segments.some((segment) => segment.kind === "asset"),
    );
    expect(assetParagraphs).toHaveLength(1);
    expect(assetParagraphs[0]!.segments).toHaveLength(1);
    const declared = newPictures.withDeclared({ ...exam("Prov", 0), instructions: emittedBody });
    expect(declared.assets.map((entry) => entry.asset_id)).toEqual([assetId]);

    await choosePicture(mounted, textFile());
    expect((editor.emitted("updateInstructions") as Array<unknown> | undefined)?.length).toBe(1);
    expect(service.notice.value).toEqual({ kind: "refused", text: TYPE_COPY });
    expect(mounted.get('[data-test="exam-workspace-delete-notice"]').text()).toContain(TYPE_COPY);
  });

  it("shows the refusal at the top of the question editor", async () => {
    const item = freeTextItem();
    const { service } = standAloneService(item);
    // eslint-disable-next-line vue/one-component-per-file -- spec host with the provided service
    const Host = defineComponent({
      setup() {
        provideExamWorkspacePictures(service);
        return () =>
          h(ExamWorkspaceQuestionEditor, {
            item,
            label: "1",
            origin: "created",
            parent: null,
            child: null,
            converting: false,
            disabled: false,
            notice: service.notice.value,
            importOpen: false,
          });
      },
    });
    mounted = mount(Host, {
      attachTo: document.body,
      global: { plugins: [examWorkspaceProvidersPlugin()] },
    });
    await nextTick();
    await nextTick();

    await choosePicture(mounted, textFile());

    expect(mounted.get('[data-test="exam-workspace-delete-notice"]').text()).toContain(TYPE_COPY);
    expect(mounted.findComponent(ExamWorkspaceBodyEditor).emitted("updateBody")).toBeUndefined();
  });

  it("carries an accepted picture to the signed-in autosave from the pane", async () => {
    vi.stubGlobal(
      "createImageBitmap",
      async () => ({ width: 8, height: 8, close: () => undefined }),
    );
    const { editing } = await openEditing(api);
    const stored = () => editing.workspaceDocument.value!;
    const selected = () => stored().items.find((entry) => entry.item_id === "item_001")!;
    const entryFor = (item: NativeExamItem): ExamWorkspaceItemEntry => ({
      kind: "item",
      id: item.item_id,
      label: "1",
      parentId: null,
      text: "Fråga",
      typeLabel: "Fritext",
      itemKind: item.kind,
      points: 2,
      problem: null,
      aiKey: null,
      status: "ok",
    });
    mounted = mount(ExamWorkspaceEditorPane, {
      attachTo: document.body,
      global: { plugins: [examWorkspaceProvidersPlugin()] },
      props: {
        editing,
        workspaceDocument: stored(),
        examInstructionsSelected: false,
        selectedParent: null,
        selectedParentEntry: null,
        parentChildren: [],
        entries: [entryFor(selected())],
        selectedItem: selected(),
        itemEntry: entryFor(selected()),
        itemParent: null,
        itemChild: null,
        itemNotice: null,
        converting: false,
        disabled: false,
        importOpen: false,
        openDrawerShown: true,
      },
    });
    await nextTick();
    await nextTick();

    await choosePicture(mounted, pngFile(6));

    await vi.waitFor(() => expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalled());
    const sent = api.storeExamWorkspaceUndoStep.mock.calls[0]![1] as {
      document: NativeExamDocument;
      newPictures: Record<string, Blob>;
    };
    const assetIds = Object.keys(sent.newPictures);
    expect(assetIds).toHaveLength(1);
    expect(sent.newPictures[assetIds[0]!]!).toBeInstanceOf(Blob);
    expect(sent.document.assets.map((entry) => entry.asset_id)).toEqual(assetIds);
    expect(stored().assets.map((entry) => entry.asset_id)).toEqual(assetIds);
  });

  it("shows, dismisses and clears the pane refusal on selection change", async () => {
    const { editing } = await openEditing(api);
    const stored = () => editing.workspaceDocument.value!;
    const selected = () => stored().items.find((entry) => entry.item_id === "item_001")!;
    const other = () => stored().items.find((entry) => entry.item_id === "item_002")!;
    const entryFor = (item: NativeExamItem, label: string): ExamWorkspaceItemEntry => ({
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
    });
    mounted = mount(ExamWorkspaceEditorPane, {
      attachTo: document.body,
      global: { plugins: [examWorkspaceProvidersPlugin()] },
      props: {
        editing,
        workspaceDocument: stored(),
        examInstructionsSelected: false,
        selectedParent: null,
        selectedParentEntry: null,
        parentChildren: [],
        entries: [entryFor(selected(), "1"), entryFor(other(), "2")],
        selectedItem: selected(),
        itemEntry: entryFor(selected(), "1"),
        itemParent: null,
        itemChild: null,
        itemNotice: null,
        converting: false,
        disabled: false,
        importOpen: false,
        openDrawerShown: true,
      },
    });
    await nextTick();
    await nextTick();

    await choosePicture(mounted, textFile());
    expect(mounted.get('[data-test="exam-workspace-delete-notice"]').text()).toContain(TYPE_COPY);

    await mounted.get('[data-test="exam-workspace-delete-notice-close"]').trigger("click");
    expect(mounted.find('[data-test="exam-workspace-delete-notice"]').exists()).toBe(false);

    await choosePicture(mounted, textFile());
    expect(mounted.find('[data-test="exam-workspace-delete-notice"]').exists()).toBe(true);

    await mounted.setProps({ selectedItem: other(), itemEntry: entryFor(other(), "2") });
    await nextTick();
    expect(mounted.find('[data-test="exam-workspace-delete-notice"]').exists()).toBe(false);
  });

  it("carries an accepted picture to the guest draft store through the guest editing session", async () => {
    const leaseStorage = createInMemoryGuestEditLeaseStorage();
    const publicMocks = createGuestPublicApiMocks();
    const storage = createExamWorkspaceGuestDraftStorage({
      port: createInMemoryExamWorkspaceGuestDraftStorage({ lease: leaseStorage }),
    });
    const guest = createGuestExamWorkspaceStore({
      api: publicMocks,
      ids: createIds(),
      leaseStorage,
      onLimit: vi.fn(),
      storage,
    });
    publicMocks.createPublicExamWorkspaceBlank.mockResolvedValue({
      document: guestExam("Original"),
      export_blockers: [],
    });
    await guest.startBlank(null, liveAdmission());
    const editing = inScope(() =>
      useExamWorkspaceEditing(guest.store, nullRouteProjection(), {
        guestStorage: leaseStorage,
        openGuestChannel: channel,
        tabId: LEASE_TAB_ID,
      }),
    );
    const opened = await guest.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    editing.applyCommandResponse(opened);
    await vi.waitFor(() => expect(editing.editingLocked.value).toBe(false));

    const service = createExamWorkspacePictureService({
      document: () => editing.workspaceDocument.value,
      newPictures: editing.newPictures,
      canEdit: () => true,
      read,
    });
    const { placePicture, target } = stubTarget();
    await service.add(target, [pngFile(7)]);
    expect(placePicture).toHaveBeenCalledTimes(1);
    const assetId = placePicture.mock.calls[0]![0] as string;
    expect(assetId).toMatch(/^asset_[0-9a-f]{16}$/);

    editing.updateItemBody("item_001", [
      { heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] },
    ], true);
    expect(await editing.save()).toBe(true);

    const draft = await storage.load();
    expect(draft?.assets[assetId]).toBeInstanceOf(Blob);
    expect(editing.workspaceDocument.value?.assets.map((entry) => entry.asset_id)).toContain(assetId);
    expect(editing.assetUrls.value[assetId]).toBe("blob:picture");
  });
});
