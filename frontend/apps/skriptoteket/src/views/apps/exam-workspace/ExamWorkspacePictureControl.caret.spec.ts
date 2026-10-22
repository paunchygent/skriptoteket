/**
 * Exam workspace picture control caret: after a mid-text picture insert, the caret stays after the picture.
 *
 * Expected behavior (TASK-SKRIPT-39-10-04, walk repair W1):
 *   - The question text is one paragraph ("Kaffe och te") plus an empty
 *     paragraph. The caret sits before "och" when a picture is added through
 *     "Lägg till bild".
 *   - The picture lands in its own paragraph between "Kaffe " and "och te",
 *     and the caret stays at the start of the "och te" paragraph through the
 *     structural autosave and its install.
 *   - Typing one character lands it at the caret (the start of "och te");
 *     the trailing empty paragraph stays empty.
 *
 * The mount runs the real editing pipeline (real `useExamWorkspaceEditing`,
 * real picture service over the real intake, the real body editor fed from
 * the working copy), with the stored-step double answering like the server:
 * it round-trips the stored document through the server's paragraph shape
 * (`segments` before `heading_level`, as pydantic serializes
 * `NativeParagraph`), so the install carries the normalized copy.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, nextTick } from "vue";

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import { createExamWorkspacePictureService } from "./examWorkspacePictureService";
import { provideExamWorkspacePictures } from "./examWorkspacePictureService";
import { installGuestStoreObjectUrls } from "./examWorkspaceGuestStore.specSupport";
import { exam, openEditing } from "./useExamWorkspaceEditing.history.specSupport";
import {
  choosePicture,
  editorOf,
  LIMIT_BYTES,
  pictureFile,
  posIn,
  read,
} from "./examWorkspacePictureControl.specSupport";
import { TRANSPARENT_PNG_PICTURE } from "./examWorkspacePictureFixtures.specSupport";

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

/** A text run as the server serializes it: `kind` first, `kept_gap_id` last. */
function serverText(value: string): NativeExamBodySegment {
  return { kind: "text", text: value, marks: [], kept_gap_id: null };
}

/** A paragraph as the server serializes `NativeParagraph`: `segments` before `heading_level`. */
function serverParagraph(...segments: NativeExamBodySegment[]): NativeExamBodyParagraph {
  return { segments, heading_level: null };
}

/** One stored segment rebuilt in the server's field order. */
function serverSegment(segment: NativeExamBodySegment): NativeExamBodySegment {
  if (segment.kind === "text") {
    return { kind: "text", text: segment.text, marks: [...segment.marks], kept_gap_id: segment.kept_gap_id ?? null };
  }
  if (segment.kind === "gap") {
    return { kind: "gap", gap_id: segment.gap_id };
  }
  return { kind: "asset", asset_id: segment.asset_id };
}

/**
 * The stored document as the server answers it: parsed into the pydantic
 * models and serialized back, so every paragraph carries `segments` before
 * `heading_level` even when the teacher's copy was built `heading_level` first.
 */
function serverDocument(document: NativeExamDocument): NativeExamDocument {
  return {
    ...document,
    items: document.items.map((item: NativeExamItem) => ({
      ...item,
      body: item.body.map((paragraph) => ({
        segments: paragraph.segments.map(serverSegment),
        heading_level: paragraph.heading_level,
      })),
    })),
  };
}

let mounted: VueWrapper | null = null;

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
  vi.stubGlobal(
    "createImageBitmap",
    async () => ({ width: 8, height: 8, close: () => undefined }),
  );
});

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
});

describe("ExamWorkspacePictureControl caret", () => {
  it("keeps the caret just after a mid-text picture through the autosave install", async () => {
    const baseline = exam("Kaffe", 1);
    baseline.items[0] = {
      ...baseline.items[0]!,
      body: [serverParagraph(serverText("Kaffe och te")), serverParagraph()],
    };
    const { editing } = await openEditing(api, baseline);

    // The stored-step double answers with the server-normalized copy.
    const inner = api.storeExamWorkspaceUndoStep.getMockImplementation();
    if (!inner) {
      throw new Error("expected the step store double");
    }
    api.storeExamWorkspaceUndoStep.mockImplementation(async (lineage: string, request: { document: NativeExamDocument }) => {
      const answered = await (inner as (lineage: string, request: unknown) => Promise<{ document: NativeExamDocument }>)(
        lineage,
        request,
      );
      return { ...answered, document: serverDocument(answered.document) };
    });

    const service = createExamWorkspacePictureService({
      document: () => editing.workspaceDocument.value,
      newPictures: editing.newPictures,
      canEdit: () => true,
      opening: () => editing.openExam.value,
      isOpen: editing.isOpen,
      maxExamBytes: async () => LIMIT_BYTES,
      read,
    });
    const Host = defineComponent({
      setup() {
        provideExamWorkspacePictures(service);
        const item = computed(
          () => editing.workspaceDocument.value?.items.find((entry) => entry.item_id === "item_001"),
        );
        return () => {
          const current = item.value;
          if (!current) {
            return h("div");
          }
          return h(ExamWorkspaceBodyEditor, {
            item: current,
            assetUrls: editing.assetUrls.value,
            onUpdateBody: (itemId: string, body: NativeExamBodyParagraph[], structural: boolean) =>
              editing.updateItemBody(itemId, body, structural),
          });
        };
      },
    });
    const wrapper = mount(Host, { attachTo: document.body });
    mounted = wrapper;
    await nextTick();
    await nextTick();

    const editor = editorOf(wrapper, "exam-workspace-body-editor-surface");
    // The teacher works in the surface, so it is the toolbar's active target;
    // without focus the control falls back to the surface end.
    (wrapper.get('[data-test="exam-workspace-body-editor-surface"]').element as HTMLElement).focus();
    await nextTick();
    editor.commands.setTextSelection(posIn(editor, "och", 0));

    await choosePicture(wrapper, pictureFile(TRANSPARENT_PNG_PICTURE, "kaffe.png"));

    await vi.waitFor(() => expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalled());
    await flushPromises();
    await nextTick();
    await nextTick();

    const body = wrapper.findComponent(ExamWorkspaceBodyEditor);
    const updates = body.emitted("updateBody") as
      | Array<[string, NativeExamBodyParagraph[], boolean]>
      | undefined;
    if (!updates || updates.length === 0) {
      throw new Error("the picture insert emitted no update");
    }
    const emittedBody = updates[0]![1];
    const returnedBody = editing.workspaceDocument.value?.items.find(
      (entry) => entry.item_id === "item_001",
    )?.body;
    expect(returnedBody).toEqual(emittedBody);

    const assetId = emittedBody[1]?.segments[0];
    expect(emittedBody).toHaveLength(4);
    expect(emittedBody[0]!.segments).toEqual([serverText("Kaffe ")]);
    expect(assetId?.kind).toBe("asset");
    expect(emittedBody[2]!.segments).toEqual([serverText("och te")]);
    expect(emittedBody[3]!.segments).toEqual([]);

    // The caret stays a text cursor at the start of the second half.
    const selection = editor.state.selection;
    expect(selection.empty).toBe(true);
    expect(selection.from).toBe(posIn(editor, "och te", 0));

    editor.commands.insertContent("!");
    await nextTick();
    await flushPromises();

    const finalBody = editing.workspaceDocument.value?.items.find(
      (entry) => entry.item_id === "item_001",
    )?.body;
    expect(finalBody?.[2]?.segments).toEqual([serverText("!och te")]);
    expect(finalBody?.[3]?.segments).toEqual([]);
  });
});
