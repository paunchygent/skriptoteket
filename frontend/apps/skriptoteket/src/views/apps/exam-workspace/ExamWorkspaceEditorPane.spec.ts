/**
 * Exam workspace editor pane with shared instructions.
 *
 * Expected behavior:
 *   The exam's shared instructions render once, read-only, above the question
 *   list with their pictures resolved through the protected URL map, and are
 *   absent when the document has none.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceEditorPane from "./ExamWorkspaceEditorPane.vue";
import { examWorkspaceSharedParagraphs } from "./examWorkspaceSharedInstruction";

const ASSET_ID = "asset_0123456789abcdef";
const PROTECTED_URL =
  "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/lineage-1/assets/asset_0123456789abcdef?revision=3";

function sharedInstruction(): NativeExamBodyParagraph[] {
  return [
    {
      segments: [
        { kind: "text", text: "Betrakta diagrammet." },
        { asset_id: ASSET_ID, kind: "asset" },
      ],
    },
  ];
}

function mountPane(globalInstructions = examWorkspaceSharedParagraphs(sharedInstruction(), {
  [ASSET_ID]: PROTECTED_URL,
})) {
  return mount(ExamWorkspaceEditorPane, {
    props: {
      assetUrls: { [ASSET_ID]: PROTECTED_URL },
      detailsOpen: false,
      disabled: false,
      exportBlockersByItemId: {},
      globalInstructions,
      itemCount: 0,
      itemRows: [],
      layout: "desktop",
      readinessByItemId: {},
      selectedItem: null,
      selectedItemId: null,
      selectedItemLocked: false,
      selectedPosition: 0,
    },
  });
}

describe("ExamWorkspaceEditorPane shared instructions", () => {
  it("renders the exam's shared instruction once, above the question list, with its picture", () => {
    const wrapper = mountPane();

    const blocks = wrapper.findAll('[data-test="exam-workspace-global-instruction"]');
    expect(blocks).toHaveLength(1);
    const table = wrapper.get('[data-test="exam-workspace-item-table"]');
    expect(
      blocks[0]!.element.compareDocumentPosition(table.element) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      wrapper.get('[data-test="exam-workspace-shared-instruction-image"]').attributes("src"),
    ).toBe(PROTECTED_URL);
  });

  it("renders no shared instruction when the document has none", () => {
    const wrapper = mountPane([]);

    expect(wrapper.find('[data-test="exam-workspace-global-instruction"]').exists()).toBe(false);
  });
});
