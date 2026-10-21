/**
 * Exam workspace rich-text editor: placing a picture, and dropping and
 * pasting picture files.
 *
 * Expected behavior:
 *   `placePicture` puts the picture in one transaction, so the owner records
 *   exactly one structural Ångra step, and where it lands is
 *   `examWorkspacePicturePlacement`'s decision. `pictureSelected` follows the
 *   selection: true while a whole picture is selected, false otherwise. With
 *   the `pictures` prop the surface hands dropped and pasted picture files to
 *   the injected picture service with this surface as the target, and a text
 *   paste still pastes text. Without the prop there is no drop or paste
 *   handling at all and the picture service is never called.
 *
 * The drop and paste props are invoked as ProseMirror invokes them
 * (`view.someProp`), with stub events: jsdom has neither real `DataTransfer`
 * nor a layout, so no real drag can be simulated.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
import { Slice } from "@tiptap/pm/model";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import type { NativeExamBodyParagraph, NativeExamBodySegment } from "../../../api/examWorkspace";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { provideExamWorkspacePictures } from "./examWorkspacePictureService";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { paste } from "./ExamWorkspaceRichTextEditor.specSupport";
import { EXAM_PICTURE_NODE } from "./examWorkspaceRichTextSchema";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextTarget, RichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

type Body = NativeExamBodyParagraph[];
type Surface = HTMLElement & { editor?: Editor };

type EditorProps = {
  body: Body;
  pictures?: boolean;
};

type Opened = {
  wrapper: VueWrapper;
  surface: Surface;
  editor: Editor;
  registry: RichTextTargetRegistry;
  updates: Array<[Body, boolean]>;
  add: ReturnType<typeof vi.fn>;
  last: () => Body;
  lastStructural: () => boolean;
};

function text(value: string): NativeExamBodySegment {
  return { kind: "text", text: value, marks: [], kept_gap_id: null };
}

function picture(assetId: string): NativeExamBodySegment {
  return { kind: "asset", asset_id: assetId };
}

function paragraph(...segments: NativeExamBodySegment[]): NativeExamBodyParagraph {
  return { heading_level: null, segments };
}

async function open(initial: EditorProps): Promise<Opened> {
  const updates: Array<[Body, boolean]> = [];
  const add = vi.fn(async () => undefined);
  let registry!: RichTextTargetRegistry;
  const Host = defineComponent({
    props: { editorProps: { type: Object, required: true } },
    setup(hostProps) {
      registry = provideRichTextTargetRegistry();
      provideExamWorkspaceHistoryKeys({
        undo: vi.fn(),
        redo: vi.fn(),
        canUndo: ref(false),
        canRedo: ref(false),
      });
      provideExamWorkspacePictures({
        busy: ref(false),
        notice: ref<ExamWorkspaceNotice | null>(null),
        add,
        dismissNotice: vi.fn(),
      });
      return () =>
        h(ExamWorkspaceRichTextEditor, {
          label: "Frågetext",
          testId: "pictures-editor",
          ...(hostProps.editorProps as EditorProps),
          onUpdate: (body: Body, structural: boolean) => updates.push([body, structural]),
        });
    },
  });
  const wrapper = mount(Host, { attachTo: document.body, props: { editorProps: initial } });
  await nextTick();
  await nextTick();
  const surface = wrapper.get("[data-test='pictures-editor']").element as Surface;
  if (!surface.editor) {
    throw new Error("the editor did not mount");
  }
  return {
    wrapper,
    surface,
    editor: surface.editor,
    registry,
    updates,
    add,
    last: () => {
      const latest = updates.at(-1);
      if (!latest) {
        throw new Error("the editor emitted no update");
      }
      return latest[0];
    },
    lastStructural: () => updates.at(-1)?.[1] ?? false,
  };
}

/** Focus the surface, as the teacher does, and read the target it registers. */
async function activate(current: Opened): Promise<RichTextTarget> {
  current.surface.focus();
  await nextTick();
  const target = current.registry.active.value;
  if (target === null) {
    throw new Error("the editor did not become the active target");
  }
  return target;
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

function pngFile(name = "bild.png", type = "image/png"): File {
  return new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], name, { type });
}

function pasteEvent(files: File[]): ClipboardEvent {
  return {
    clipboardData: { files, types: files.length > 0 ? ["Files"] : [] },
    preventDefault: vi.fn(),
  } as unknown as ClipboardEvent;
}

function dropEvent(files: File[]): DragEvent {
  return {
    dataTransfer: { files },
    clientX: 0,
    clientY: 0,
    preventDefault: vi.fn(),
  } as unknown as DragEvent;
}

/** The value the surface's paste prop returns, or undefined when it has none. */
function pasteProp(editor: Editor, event: ClipboardEvent): boolean | void {
  return editor.view.someProp("handlePaste", (handle) => handle(editor.view, event, Slice.empty));
}

/** The value the surface's drop prop returns, or undefined when it has none. */
function dropProp(editor: Editor, event: DragEvent): boolean | void {
  return editor.view.someProp("handleDrop", (handle) =>
    handle(editor.view, event, Slice.empty, false),
  );
}

let opened: Opened | null = null;

async function openEditor(initial: EditorProps): Promise<Opened> {
  opened = await open(initial);
  return opened;
}

afterEach(() => {
  opened?.wrapper.unmount();
  opened = null;
  document.body.innerHTML = "";
});

describe("ExamWorkspaceRichTextEditor pictures", () => {
  describe("placePicture", () => {
    it("places the picture in one structural update", async () => {
      const current = await openEditor({ body: [paragraph(text("Slut"))], pictures: true });
      const target = await activate(current);
      current.editor.commands.setTextSelection(posIn(current.editor, "Slut", 4));

      target.placePicture("asset_new");

      expect(current.updates).toHaveLength(1);
      expect(current.lastStructural()).toBe(true);
      expect(current.last()).toEqual([
        paragraph(text("Slut")),
        paragraph(picture("asset_new")),
        paragraph(),
      ]);
    });

    it("reports a selected picture and hides it again when the selection moves into the text", async () => {
      const current = await openEditor({
        body: [paragraph(text("A"), picture("asset_old"), text("B"))],
        pictures: true,
      });
      const target = await activate(current);
      expect(target.pictureSelected.value).toBe(false);

      const at = picturePos(current.editor);
      current.editor.commands.setNodeSelection(at);
      expect(target.pictureSelected.value).toBe(true);

      current.editor.commands.setTextSelection(at - 1);
      expect(target.pictureSelected.value).toBe(false);

      current.editor.commands.setNodeSelection(at);
      target.placePicture("asset_new");
      expect(target.pictureSelected.value).toBe(true);
      expect(current.last()).toEqual([paragraph(text("A"), picture("asset_new"), text("B"))]);
    });

    it("accepts pictures only with the pictures prop", async () => {
      const without = await openEditor({ body: [paragraph(text("Text"))] });
      expect((await activate(without)).acceptsPictures).toBe(false);
      without.wrapper.unmount();
      opened = null;
      document.body.innerHTML = "";

      const withPictures = await openEditor({ body: [paragraph(text("Text"))], pictures: true });
      expect((await activate(withPictures)).acceptsPictures).toBe(true);
    });
  });

  describe("dropped and pasted files", () => {
    it("hands a pasted picture to the picture service with this surface as the target", async () => {
      const current = await openEditor({ body: [paragraph(text("Text"))], pictures: true });
      const target = await activate(current);
      const file = pngFile();

      const handled = pasteProp(current.editor, pasteEvent([file]));

      expect(handled).toBe(true);
      expect(current.add).toHaveBeenCalledTimes(1);
      expect(current.add.mock.calls[0]?.[0]).toBe(target);
      expect(current.add.mock.calls[0]?.[1]).toEqual([file]);
    });

    it("hands a dropped picture to the picture service with this surface as the target", async () => {
      const current = await openEditor({ body: [paragraph(text("Text"))], pictures: true });
      const target = await activate(current);
      const file = pngFile("foto.jpg", "image/jpeg");

      const handled = dropProp(current.editor, dropEvent([file]));

      expect(handled).toBe(true);
      expect(current.add).toHaveBeenCalledTimes(1);
      expect(current.add.mock.calls[0]?.[0]).toBe(target);
      expect(current.add.mock.calls[0]?.[1]).toEqual([file]);
    });

    it("still pastes text when the clipboard carries no picture", async () => {
      const current = await openEditor({ body: [paragraph(text("Text"))], pictures: true });
      await activate(current);

      paste(current.surface, "<p>Insatt</p>", "Insatt");

      expect(current.editor.getText()).toContain("Insatt");
      expect(current.add).not.toHaveBeenCalled();
    });

    it("handles no files at all without the pictures prop", async () => {
      const current = await openEditor({ body: [paragraph(text("Text"))] });
      await activate(current);

      expect(pasteProp(current.editor, pasteEvent([pngFile()]))).toBeUndefined();
      expect(dropProp(current.editor, dropEvent([pngFile()]))).toBeUndefined();
      expect(current.add).not.toHaveBeenCalled();
    });
  });
});
