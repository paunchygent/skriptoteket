/**
 * Exam workspace question-text editor, DOCX picture rendering.
 *
 * Expected behavior:
 *   A picture stays one fixed atom with its `data-asset-id` identity. A known
 *   asset URL renders the actual picture inside the atom and an unknown URL
 *   keeps the "Bild" placeholder, never text. A URL that arrives, changes or
 *   goes away updates the live atom in place, without a document change and
 *   so without a body edit. The question editor passes its URL map through.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { buildGapItem, mountEditor, surface } from "./ExamWorkspaceBodyEditor.specSupport";
import type { MountedBodyEditor } from "./ExamWorkspaceBodyEditor.specSupport";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

const ASSET_ID = "asset_001";
const ASSET_URL =
  "https://gateway.test/api/v1/apps/documents.conversion_hub/exam-workspace/documents/doc_001/assets/asset_001";

function assetAtom(wrapper: MountedBodyEditor): HTMLElement {
  return wrapper.get(`[data-atom="asset"][data-asset-id="${ASSET_ID}"]`).element as HTMLElement;
}

describe("ExamWorkspaceBodyEditor picture rendering", () => {
  it("renders the mapped picture inside the atom at its position in the text", async () => {
    const wrapper = await mountEditor(buildGapItem(), { assetUrls: { [ASSET_ID]: ASSET_URL } });

    const atom = assetAtom(wrapper);
    const image = atom.querySelector("img")!;
    expect(image.getAttribute("src")).toBe(ASSET_URL);
    expect(image.getAttribute("alt")).toBe("");
    expect(atom.getAttribute("role")).toBe("img");
    expect(atom.getAttribute("aria-label")).toBe("Bild");
    expect(atom.childNodes).toHaveLength(1);
    expect(atom.previousSibling?.textContent).toBe("Se ");
    expect(wrapper.emitted("updateBody")).toBeUndefined();
    wrapper.unmount();
  });

  it("keeps the Bild placeholder while the URL map has no entry", async () => {
    const wrapper = await mountEditor(buildGapItem(), { assetUrls: {} });

    const atom = assetAtom(wrapper);
    expect(atom.querySelector("img")).toBeNull();
    expect(atom.getAttribute("data-label")).toBe("Bild");
    expect(surface(wrapper).textContent).not.toContain("Bild");
    wrapper.unmount();
  });

  it("draws a URL that arrives, changes and goes away in the same atom", async () => {
    const wrapper = await mountEditor(buildGapItem(), { assetUrls: {} });
    const atom = assetAtom(wrapper);
    const text = atom.previousSibling;

    await wrapper.setProps({ assetUrls: { [ASSET_ID]: ASSET_URL } });
    expect(assetAtom(wrapper)).toBe(atom);
    expect(atom.querySelector("img")?.getAttribute("src")).toBe(ASSET_URL);

    await wrapper.setProps({ assetUrls: { [ASSET_ID]: `${ASSET_URL}?v=2` } });
    expect(atom.querySelector("img")?.getAttribute("src")).toBe(`${ASSET_URL}?v=2`);
    expect(assetAtom(wrapper)).toBe(atom);
    expect(atom.previousSibling).toBe(text);

    await wrapper.setProps({ assetUrls: {} });
    expect(atom.querySelector("img")).toBeNull();
    expect(wrapper.emitted("updateBody")).toBeUndefined();
    wrapper.unmount();
  });

  it("passes the asset URL map through the question editor to the body editor", async () => {
    const wrapper = mount(ExamWorkspaceQuestionEditor, {
      global: { plugins: [examWorkspaceProvidersPlugin()] },
      props: {
        assetUrls: { [ASSET_ID]: ASSET_URL },
        item: buildGapItem(),
        label: "1",
        origin: "digiexam_import",
        parent: null,
        child: null,
        converting: false,
        disabled: false,
        notice: null,
        importOpen: false,
      },
      attachTo: document.body,
    });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.get(`[data-asset-id="${ASSET_ID}"] img`).attributes("src")).toBe(ASSET_URL);
    wrapper.unmount();
  });

  it("sets a hostile URL as one attribute and never as HTML", async () => {
    const hostileUrl = `${ASSET_URL}" onerror="globalThis.__examPicturePwned=1`;
    const wrapper = await mountEditor(buildGapItem(), { assetUrls: { [ASSET_ID]: hostileUrl } });

    const atom = assetAtom(wrapper);
    const image = atom.querySelector("img")!;
    expect(image.getAttribute("src")).toBe(hostileUrl);
    expect(image.hasAttribute("onerror")).toBe(false);
    expect(atom.querySelectorAll("script")).toHaveLength(0);
    expect(atom.children).toHaveLength(1);
    expect(image.getAttribute("draggable")).toBe("false");
    wrapper.unmount();
  });
});
