/**
 * Exam workspace instruction editor, pictures.
 *
 * Expected behavior:
 *   A declared picture in the instruction body renders as the picture when
 *   its asset URL is known, exactly as in a question text, and keeps the
 *   "Bild" placeholder atom when it is not.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceInstructionEditor from "./ExamWorkspaceInstructionEditor.vue";
import { buildRecordedParent } from "./examWorkspaceParentDocument.specSupport";

const URL = "https://gateway.test/assets/asset_001";

function mountEditor(assetUrls?: Record<string, string>) {
  const parent = buildRecordedParent();
  parent.instruction = [
    {
      heading_level: null,
      segments: [
        { kind: "text", marks: [], text: "Se " },
        { kind: "asset", asset_id: "asset_001" },
      ],
    },
  ];
  return mount(ExamWorkspaceInstructionEditor, {
    props: { parent, label: "1", children: [], subtotal: 0, printedTotal: null, disabled: false, notice: null, assetUrls },
  });
}

describe("ExamWorkspaceInstructionEditor pictures", () => {
  it("shows the declared picture in the instruction", () => {
    const wrapper = mountEditor({ asset_001: URL });

    expect(wrapper.get('[data-asset-id="asset_001"] img').attributes("src")).toBe(URL);
  });

  it("keeps the placeholder atom without a mapped URL", () => {
    const wrapper = mountEditor();

    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.find('[data-atom="asset"][data-asset-id="asset_001"]').exists()).toBe(true);
  });
});
