/**
 * Exam workspace question-text editor, DOCX picture rendering.
 *
 * Expected behavior:
 *   An image atom stays one fixed, non-editable atom with its
 *   `data-atom`/`data-asset-id` identity. A known asset URL renders the
 *   actual picture inside the atom and an unknown URL keeps the "Bild"
 *   placeholder, never text. A URL that arrives or changes updates the live
 *   atom in place, so the paragraph DOM, its caret nodes and every sibling
 *   paragraph stay untouched. A rendered image is still protected from
 *   removal and dragging, and its source is set as an attribute, never as
 *   interpolated HTML.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import { buildGapItem, paragraph } from "./ExamWorkspaceBodyEditor.specSupport";
import ExamWorkspaceItemEditor from "./ExamWorkspaceItemEditor.vue";
import { partsFromParagraphElement, segmentsFromParts } from "./examWorkspaceBodySegments";

const ASSET_ID = "asset_001";
const ASSET_URL =
  "https://gateway.test/api/v1/apps/documents.conversion_hub/exam-workspace/documents/doc_001/assets/asset_001";

function mountPictureEditor(
  item: NativeExamItem = buildGapItem(),
  assetUrls?: Record<string, string>,
) {
  return mount(ExamWorkspaceBodyEditor, { props: { item, assetUrls }, attachTo: document.body });
}

function assetAtom(wrapper: ReturnType<typeof mountPictureEditor>): HTMLElement {
  return wrapper.get(`[data-atom="asset"][data-asset-id="${ASSET_ID}"]`).element as HTMLElement;
}

describe("ExamWorkspaceBodyEditor picture rendering", () => {
  it("renders the mapped picture inside the atom at its model position", () => {
    const wrapper = mountPictureEditor(buildGapItem(), { [ASSET_ID]: ASSET_URL });

    const atom = assetAtom(wrapper);
    const image = wrapper.get(`[data-asset-id="${ASSET_ID}"] img`);
    expect(image.attributes("src")).toBe(ASSET_URL);
    expect(image.attributes("alt")).toBe("");
    expect(atom.getAttribute("contenteditable")).toBe("false");
    expect(atom.getAttribute("data-atom")).toBe("asset");
    expect(atom.getAttribute("data-asset-id")).toBe(ASSET_ID);
    expect(atom.getAttribute("role")).toBe("img");
    expect(atom.getAttribute("aria-label")).toBe("Bild");
    expect(atom.hasAttribute("data-label")).toBe(false);
    expect(paragraph(wrapper, 1).textContent).toBe("Se ");
    expect(atom.childNodes).toHaveLength(1);
    wrapper.unmount();
  });

  it("keeps the picture out of the text model so a round-trip carries one asset and no label", () => {
    const wrapper = mountPictureEditor(buildGapItem(), { [ASSET_ID]: ASSET_URL });

    const segments = segmentsFromParts(partsFromParagraphElement(paragraph(wrapper, 1)));

    expect(segments).toEqual([
      { kind: "text", marks: [], text: "Se " },
      { kind: "asset", asset_id: ASSET_ID },
    ]);
    expect(paragraph(wrapper, 1).textContent).not.toContain("Bild");
    wrapper.unmount();
  });

  it("keeps the Bild placeholder and claims no picture while the URL map has no entry", () => {
    const wrapper = mountPictureEditor();

    const atom = assetAtom(wrapper);
    expect(atom.querySelector("img")).toBeNull();
    expect(atom.getAttribute("data-label")).toBe("Bild");
    expect(atom.getAttribute("aria-label")).toBe("Bild");
    expect(paragraph(wrapper, 1).textContent).toBe("Se ");
    wrapper.unmount();
  });

  it("updates the live atom when a URL arrives without detaching the paragraph or its caret nodes", async () => {
    const wrapper = mountPictureEditor();
    const element = paragraph(wrapper, 1);
    const atom = assetAtom(wrapper);
    const textBefore = element.firstChild;

    await wrapper.setProps({ assetUrls: { [ASSET_ID]: ASSET_URL } });
    await wrapper.vm.$nextTick();

    expect(paragraph(wrapper, 1)).toBe(element);
    expect(assetAtom(wrapper)).toBe(atom);
    expect(element.firstChild).toBe(textBefore);
    expect(atom.querySelector("img")!.getAttribute("src")).toBe(ASSET_URL);
    wrapper.unmount();
  });

  it("changes a known picture source in place without replacing the atom, image or neighbouring text", async () => {
    const updatedUrl = `${ASSET_URL}?v=2`;
    const wrapper = mountPictureEditor(buildGapItem(), { [ASSET_ID]: ASSET_URL });
    const element = paragraph(wrapper, 1);
    const atom = assetAtom(wrapper);
    const image = atom.querySelector("img")!;
    const textBefore = element.firstChild;

    await wrapper.setProps({ assetUrls: { [ASSET_ID]: updatedUrl } });
    await wrapper.vm.$nextTick();

    expect(assetAtom(wrapper)).toBe(atom);
    expect(atom.querySelector("img")).toBe(image);
    expect(image.getAttribute("src")).toBe(updatedUrl);
    expect(element.firstChild).toBe(textBefore);
    wrapper.unmount();
  });

  it("restores the placeholder in place when the URL map loses the asset", async () => {
    const wrapper = mountPictureEditor(buildGapItem(), { [ASSET_ID]: ASSET_URL });
    const atom = assetAtom(wrapper);

    await wrapper.setProps({ assetUrls: {} });
    await wrapper.vm.$nextTick();

    expect(assetAtom(wrapper)).toBe(atom);
    expect(atom.querySelector("img")).toBeNull();
    expect(atom.getAttribute("data-label")).toBe("Bild");
    wrapper.unmount();
  });

  it("passes the asset URL map through the item editor to the body editor", () => {
    const wrapper = mount(ExamWorkspaceItemEditor, {
      props: {
        assetUrls: { [ASSET_ID]: ASSET_URL },
        attentionCount: 0,
        detailsOpen: false,
        item: buildGapItem(),
        position: 1,
        showNavigation: false,
        total: 1,
      },
    });

    expect(wrapper.get(`[data-asset-id="${ASSET_ID}"] img`).attributes("src")).toBe(ASSET_URL);
    wrapper.unmount();
  });

  it("refuses a cut whose range covers the rendered picture", () => {
    const wrapper = mountPictureEditor(buildGapItem(), { [ASSET_ID]: ASSET_URL });
    const element = paragraph(wrapper, 1);
    const atom = assetAtom(wrapper);
    const range = document.createRange();
    range.selectNode(atom);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);

    const event = new InputEvent("beforeinput", {
      bubbles: true,
      cancelable: true,
      inputType: "deleteByCut",
    });
    element.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(atom.isConnected).toBe(true);
    wrapper.unmount();
  });

  it("still refuses removal and dragging of an atom that renders a real picture", async () => {
    const wrapper = mountPictureEditor(buildGapItem(), { [ASSET_ID]: ASSET_URL });
    const element = paragraph(wrapper, 1);
    const image = element.querySelector(`[data-asset-id="${ASSET_ID}"] img`)!;

    const dragStart = new Event("dragstart", { bubbles: true, cancelable: true });
    image.dispatchEvent(dragStart);
    expect(dragStart.defaultPrevented).toBe(true);

    image.closest(`[data-asset-id="${ASSET_ID}"]`)!.remove();
    element.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    expect(element.querySelector(`[data-asset-id="${ASSET_ID}"] img`)).not.toBeNull();
    wrapper.unmount();
  });

  it("emits the picture atom unchanged when neighbouring text is edited", () => {
    const wrapper = mountPictureEditor(buildGapItem(), { [ASSET_ID]: ASSET_URL });
    const element = paragraph(wrapper, 1);
    (element.firstChild as Text).data = "Titta på ";
    element.dispatchEvent(new Event("input", { bubbles: true }));

    expect(wrapper.emitted("updateParagraphSegments")).toEqual([
      ["item_001", 1, [{ kind: "text", marks: [], text: "Titta på " }, { kind: "asset", asset_id: ASSET_ID }]],
    ]);
    wrapper.unmount();
  });

  it("sets a hostile URL as one attribute and never as HTML", () => {
    const hostileUrl = `${ASSET_URL}" onerror="globalThis.__examPicturePwned=1`;
    const wrapper = mountPictureEditor(buildGapItem(), { [ASSET_ID]: hostileUrl });

    const atom = assetAtom(wrapper);
    const image = atom.querySelector("img")!;
    expect(image.getAttribute("src")).toBe(hostileUrl);
    expect(image.hasAttribute("onerror")).toBe(false);
    expect(atom.querySelectorAll("script")).toHaveLength(0);
    expect(atom.children).toHaveLength(1);
    expect(image.getAttribute("draggable")).toBe("false");
    wrapper.unmount();
  });

  it("constrains the picture to the paragraph width instead of overflowing it", () => {
    const wrapper = mountPictureEditor(buildGapItem(), { [ASSET_ID]: ASSET_URL });

    const atom = assetAtom(wrapper);
    const image = atom.querySelector("img")!;
    expect(atom.classList).toContain("max-w-full");
    expect(image.classList).toContain("max-w-full");
    expect(image.classList).toContain("h-auto");
    wrapper.unmount();
  });
});
