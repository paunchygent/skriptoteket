/**
 * Exam workspace instruction editor, child delete.
 *
 * Expected behavior:
 *   A deluppgift's delete control always describes removing just that
 *   deluppgift. Even when it is the part's last question the delete keeps the
 *   part as an instruction block (G8), so its tooltip never advertises
 *   removing the instruction.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ExamWorkspaceInstructionEditor from "./ExamWorkspaceInstructionEditor.vue";
import { buildRecordedParent } from "./examWorkspaceParentDocument.specSupport";
import { settleEditors } from "./ExamWorkspaceRichTextEntry.specSupport";
import type { ExamWorkspaceItemEntry } from "./examWorkspaceListEntries";

const mounted: Array<VueWrapper> = [];

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.innerHTML = "";
});

function child(id: string, label: string): ExamWorkspaceItemEntry {
  return {
    aiKey: null,
    id,
    itemKind: "free_text",
    kind: "item",
    label,
    parentId: "parent_001",
    points: 1,
    problem: null,
    status: "ok",
    text: "Fråga",
    typeLabel: "Fritext",
  };
}

async function mountEditor(children: ExamWorkspaceItemEntry[]): Promise<VueWrapper> {
  const wrapper = mount(ExamWorkspaceInstructionEditor, {
    attachTo: document.body,
    props: {
      parent: buildRecordedParent(),
      label: "1",
      children,
      subtotal: children.length,
      printedTotal: null,
      disabled: false,
      notice: null,
    },
  });
  mounted.push(wrapper);
  await settleEditors();
  return wrapper;
}

describe("ExamWorkspaceInstructionEditor child delete control", () => {
  it("says it removes only the deluppgift, also for the part's last child", async () => {
    const wrapper = await mountEditor([child("item_001", "1a")]);

    const remove = wrapper.get('[data-test="exam-workspace-child-delete-item_001"]');
    expect(remove.attributes("title")).toBe("Ta bort deluppgiften");
    expect(remove.attributes("aria-label")).toBe("Ta bort deluppgiften");
  });

  it("uses the same delete-only label among several children", async () => {
    const wrapper = await mountEditor([child("item_001", "1a"), child("item_002", "1b")]);

    expect(wrapper.get('[data-test="exam-workspace-child-delete-item_001"]').attributes("title"))
      .toBe("Ta bort deluppgiften");
    expect(wrapper.get('[data-test="exam-workspace-child-delete-item_002"]').attributes("title"))
      .toBe("Ta bort deluppgiften");
  });
});
