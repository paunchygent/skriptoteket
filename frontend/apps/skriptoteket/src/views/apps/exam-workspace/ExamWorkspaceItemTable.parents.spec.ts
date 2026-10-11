/**
 * Exam workspace question list and item editor with parents.
 *
 * Expected behavior:
 *   The list shows a parent's shared instruction and total points once, above
 *   the first child, and "Totalt –" while a child lacks points. Standalone
 *   questions carry no parent block. The editor tells a child its position
 *   and that it cannot be moved, removed or retyped here, offers no control
 *   for those changes, and says nothing of the kind for a standalone question.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceItemEditor from "./ExamWorkspaceItemEditor.vue";
import ExamWorkspaceItemTable from "./ExamWorkspaceItemTable.vue";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { PARENT_CHILD_LOCKED_COPY } from "./examWorkspaceParents";
import { toExamWorkspaceItemRows } from "./examWorkspaceRows";

function mountTable(document = buildParentDocument()) {
  return mount(ExamWorkspaceItemTable, {
    props: {
      exportBlockersByItemId: {},
      proposalItemIds: [],
      readinessByItemId: {},
      rows: toExamWorkspaceItemRows(document.items, document.parents),
      selectedItemId: "item_001",
    },
  });
}

function mountEditorFor(itemId: string) {
  const document = buildParentDocument();
  const rows = toExamWorkspaceItemRows(document.items, document.parents);
  const row = rows.find((candidate) => candidate.itemId === itemId)!;
  return mount(ExamWorkspaceItemEditor, {
    props: {
      attentionCount: 0,
      detailsOpen: false,
      item: document.items.find((item) => item.item_id === itemId)!,
      parentChild: row.parentChild,
      position: row.sequence,
      showNavigation: false,
      total: rows.length,
    },
  });
}

describe("ExamWorkspaceItemTable with a parent", () => {
  it("renders the shared instruction once, above the first child, with the summed points", () => {
    const document = buildParentDocument();
    const wrapper = mountTable(document);

    const blocks = wrapper.findAll('[data-test^="exam-workspace-parent-parent_"]');
    expect(blocks).toHaveLength(1);
    const instructionLines = wrapper.findAll('[data-test="exam-workspace-parent-instruction-line"]');
    expect(instructionLines.map((line) => line.text())).toEqual(document.parents[0]!.instruction);
    expect(wrapper.text().split(document.parents[0]!.instruction[0]!)).toHaveLength(2);
    expect(wrapper.get('[data-test="exam-workspace-parent-points"]').text()).toBe("Totalt 3 poäng");

    const firstChildRow = wrapper.get('[data-test="exam-workspace-item-row-item_001"]');
    const block = blocks[0]!.element;
    expect(
      block.compareDocumentPosition(firstChildRow.element) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(blocks[0]!.element.parentElement).toBe(firstChildRow.element.parentElement);
  });

  it("shows a dash instead of a sum while a child lacks points", () => {
    const document = buildParentDocument();
    const wrapper = mountTable({
      ...document,
      items: document.items.map((item) =>
        item.item_id === "item_003" ? { ...item, points: null } : item,
      ),
    });

    expect(wrapper.get('[data-test="exam-workspace-parent-points"]').text()).toBe("Totalt –");
  });

  it("holds gap-fill children and a single-choice child under one parent block", () => {
    const document = buildParentDocument();
    const mixed = {
      ...document,
      parents: [{ ...document.parents[0]!, item_ids: document.items.map((item) => item.item_id) }],
    };
    expect(new Set(mixed.items.map((item) => item.kind))).toEqual(
      new Set(["gap_fill", "single_choice"]),
    );
    const rows = toExamWorkspaceItemRows(mixed.items, mixed.parents);
    const wrapper = mountTable(mixed);

    expect(wrapper.findAll('[data-test^="exam-workspace-parent-parent_"]')).toHaveLength(1);
    expect(rows.map((row) => row.parentChild?.childIndex)).toEqual([0, 1, 2, 3]);
    expect(rows.map((row) => row.parentChild?.childCount)).toEqual([4, 4, 4, 4]);
  });

  it("shows no parent block on a document without parents", () => {
    const wrapper = mountTable({ ...buildParentDocument(), parents: [] });

    expect(wrapper.find('[data-test^="exam-workspace-parent-"]').exists()).toBe(false);
  });
});

describe("ExamWorkspaceItemEditor for a child and a standalone question", () => {
  it("tells a child its place and that it cannot be moved, removed or retyped", () => {
    const wrapper = mountEditorFor("item_002");

    const note = wrapper.get('[data-test="exam-workspace-parent-child-note"]').text();
    expect(note).toContain("Deluppgift 2 av 3");
    expect(note).toContain(PARENT_CHILD_LOCKED_COPY);
  });

  it("offers neither a child nor a standalone question a delete, move or type control", () => {
    for (const itemId of ["item_002", "item_004"]) {
      const labels = mountEditorFor(itemId)
        .findAll("button, select")
        .map((control) => (control.attributes("aria-label") ?? control.text()).toLowerCase());

      expect(labels.filter((label) => /ta bort|flytta|radera|byt typ|typ av/.test(label))).toEqual([]);
    }
  });

  it("shows a standalone question no parent note", () => {
    expect(
      mountEditorFor("item_004").find('[data-test="exam-workspace-parent-child-note"]').exists(),
    ).toBe(false);
  });
});
