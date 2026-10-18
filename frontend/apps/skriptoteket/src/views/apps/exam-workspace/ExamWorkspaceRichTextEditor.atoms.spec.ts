/**
 * Exam workspace rich-text editor: paste and gaps.
 *
 * Expected behavior (TASK-SKRIPT-40-04-06 D1):
 *   A paste keeps no gap, picture or formatting the vocabulary does not
 *   hold. A gap opens on a click or on Enter and Space when it is selected,
 *   only while gaps are interactive and the editor is enabled; a picture
 *   never opens. Gap labels and picture URLs are drawn in place without a
 *   document update.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import type { Body } from "./ExamWorkspaceRichTextEditor.specSupport";
import {
  atomPos,
  gap,
  mountEditor,
  paragraph,
  paste,
  picture,
  posIn,
  press,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";

describe("ExamWorkspaceRichTextEditor", () => {
  afterEach(releaseEditor);

  describe("paste", () => {
    it("inserts no gap from a pasted fragment that carries a gap element, and keeps the surrounding text", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 1));
      paste(
        opened.surface,
        '<p>x<span data-atom="gap" data-gap-id="gap_009"></span>y<span data-atom="asset" data-asset-id="asset_9"></span>z</p>',
      );
      expect(opened.updates.length).toBeGreaterThan(0);
      const [pasted] = opened.last();
      expect(pasted.segments.every((segment) => segment.kind === "text")).toBe(true);
      expect(opened.surface.querySelector("[data-atom]")).toBeNull();
      expect(opened.editor.getText()).toBe("axyzb");
    });

    it("drops the formatting the vocabulary does not keep", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 1));
      paste(opened.surface, '<p><a href="https://example.test">link</a> <code>code</code> <b>bold</b></p>');
      const all = opened.last().flatMap((entry) => entry.segments);
      expect(all.some((segment) => segment.kind === "text" && segment.text.includes("bold") && segment.marks.includes("bold"))).toBe(true);
      expect(opened.surface.querySelector("a, code")).toBeNull();
    });
  });


  describe("gaps", () => {
    const GAP_BODY: Body = [paragraph(text("a"), gap("gap_001"), text("b"), picture("asset_1"))];

    it("opens a gap that is clicked when gaps are interactive", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      const gapPos = atomPos(opened.editor, "examGap");
      const node = opened.editor.state.doc.nodeAt(gapPos);
      // jsdom has no hit testing, so the pointer cannot choose the target: the
      // view's own click handlers run with the gap as the clicked node.
      const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
        handler(opened.editor.view, gapPos, node!, gapPos, new MouseEvent("click"), true),
      );
      expect(handled).toBe(true);
      expect(opened.activations).toHaveLength(1);
      expect(opened.activations[0][0]).toBe("gap_001");
      expect(opened.activations[0][1]).toBe(opened.surface.querySelector("[data-atom='gap']"));
    });

    it("never opens a picture", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      const picturePos = atomPos(opened.editor, "examPicture");
      const node = opened.editor.state.doc.nodeAt(picturePos);
      const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
        handler(opened.editor.view, picturePos, node!, picturePos, new MouseEvent("click"), true),
      );
      expect(handled).toBeFalsy();
      opened.editor.commands.setNodeSelection(picturePos);
      press(opened.surface, "Enter");
      press(opened.surface, " ");
      expect(opened.activations).toHaveLength(0);
    });

    it("opens a node-selected gap on Enter and on Space and does not type into the document", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      opened.editor.commands.setNodeSelection(atomPos(opened.editor, "examGap"));
      expect(press(opened.surface, "Enter").defaultPrevented).toBe(true);
      expect(press(opened.surface, " ").defaultPrevented).toBe(true);
      expect(opened.activations.map(([id]) => id)).toEqual(["gap_001", "gap_001"]);
      expect(opened.updates).toHaveLength(0);
    });

    it("does not split the paragraph when Enter is pressed on a gap that is not interactive", async () => {
      const opened = await mountEditor({ body: GAP_BODY });
      const gapPos = atomPos(opened.editor, "examGap");
      const node = opened.editor.state.doc.nodeAt(gapPos);
      const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
        handler(opened.editor.view, gapPos, node!, gapPos, new MouseEvent("click"), true),
      );
      expect(handled).toBeFalsy();
      opened.editor.commands.setNodeSelection(gapPos);
      press(opened.surface, "Enter");
      expect(opened.activations).toHaveLength(0);
    });

    it("opens nothing while disabled", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true, disabled: true });
      const gapPos = atomPos(opened.editor, "examGap");
      const node = opened.editor.state.doc.nodeAt(gapPos);
      expect(
        opened.editor.view.someProp("handleClickOn", (handler) =>
          handler(opened.editor.view, gapPos, node!, gapPos, new MouseEvent("click"), true),
        ),
      ).toBeFalsy();
      opened.editor.commands.setNodeSelection(gapPos);
      press(opened.surface, "Enter");
      expect(opened.activations).toHaveLength(0);
    });

    it("passes the gap's own element on a click and on Enter", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      const gapPos = atomPos(opened.editor, "examGap");
      const node = opened.editor.state.doc.nodeAt(gapPos);
      opened.editor.view.someProp("handleClickOn", (handler) =>
        handler(opened.editor.view, gapPos, node!, gapPos, new MouseEvent("click"), true),
      );
      opened.editor.commands.setNodeSelection(gapPos);
      press(opened.surface, "Enter");
      const gapElement = opened.surface.querySelector("[data-atom='gap']");
      expect(opened.activations).toHaveLength(2);
      for (const [, element] of opened.activations) {
        expect(element).toBeInstanceOf(HTMLElement);
        expect(element).toBe(gapElement);
      }
    });

    it("opens nothing when the view has no element for the gap", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      const gapPos = atomPos(opened.editor, "examGap");
      const node = opened.editor.state.doc.nodeAt(gapPos);
      vi.spyOn(opened.editor.view, "nodeDOM").mockReturnValue(null);
      const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
        handler(opened.editor.view, gapPos, node!, gapPos, new MouseEvent("click"), true),
      );
      expect(handled).toBeFalsy();
      opened.editor.commands.setNodeSelection(gapPos);
      press(opened.surface, " ");
      expect(opened.activations).toHaveLength(0);
    });

    it("draws a changed label and an arriving picture URL in place without an update", async () => {
      const opened = await mountEditor({ body: GAP_BODY, gapsInteractive: true });
      const gapElement = opened.surface.querySelector("[data-atom='gap']") as HTMLElement;
      const pictureElement = opened.surface.querySelector("[data-atom='asset']") as HTMLElement;
      expect(gapElement.dataset.label).toBe("Lucka");
      expect(gapElement.dataset.empty).toBe("true");
      expect(pictureElement.querySelector("img")).toBeNull();

      await opened.setProps({
        gapStates: { gap_001: { label: "Lucka 1", accessibleLabel: "Lucka 1, svar saknas", empty: false } },
      });
      expect(gapElement.dataset.label).toBe("Lucka 1");
      expect(gapElement.getAttribute("aria-label")).toBe("Lucka 1, svar saknas");
      expect(gapElement.dataset.empty).toBeUndefined();

      await opened.setProps({
        gapStates: { gap_001: { label: "Lucka 1", accessibleLabel: "Lucka 1", empty: false } },
        assetUrls: { asset_1: "blob:picture-1" },
      });
      const image = opened.surface.querySelector("[data-atom='asset'] img") as HTMLImageElement | null;
      expect(image?.getAttribute("src")).toBe("blob:picture-1");
      expect(opened.updates).toHaveLength(0);
    });
  });
});
