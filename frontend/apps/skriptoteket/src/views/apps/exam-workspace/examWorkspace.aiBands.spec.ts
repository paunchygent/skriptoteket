/**
 * Exam workspace question-text toolbar class.
 *
 * Expected behavior (TASK-SKRIPT-40-04-26 D7):
 *   Only the question-text toolbar reserves the horizontal scrollbar's height
 *   and carries `xw-toolbar--question`, which is what the stylesheet's band
 *   rules key the toolbar AI group's reserved scrollbar to. The stylesheet
 *   rules themselves are read in the node half,
 *   `examWorkspace.aiBands.node.spec.ts`, because a unit test cannot evaluate
 *   media queries.
 *
 * Relationships:
 *   - Proves the rendered class through the two hosts that carry it: the
 *     question body editor marks its toolbar, an instruction editor does not.
 *   - The classes themselves belong to `ExamWorkspaceQuestionAiGroup.vue`;
 *     this half never renders or reads that component, only the toolbar
 *     classes its stylesheet keys on.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { buildGapItem, mountEditor } from "./ExamWorkspaceBodyEditor.specSupport";
import ExamWorkspaceInstructionEditor from "./ExamWorkspaceInstructionEditor.vue";
import { buildRecordedParent } from "./examWorkspaceParentDocument.specSupport";
import { settleEditors } from "./ExamWorkspaceRichTextEntry.specSupport";

let mounted: VueWrapper | null = null;

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
});

describe("the question-text toolbar's question class", () => {
  it("marks the body editor's toolbar", async () => {
    mounted = await mountEditor(buildGapItem());

    const toolbar = mounted.get('[role="toolbar"]');
    expect(toolbar.classes()).toContain("xw-toolbar");
    expect(toolbar.classes()).toContain("xw-toolbar--question");
  });

  it("leaves an instruction editor's toolbar unmarked", async () => {
    mounted = mount(ExamWorkspaceInstructionEditor, {
      attachTo: document.body,
      props: {
        parent: buildRecordedParent(),
        label: "1",
        children: [],
        subtotal: 0,
        disabled: false,
        notice: null,
      },
    });
    await settleEditors();

    const toolbar = mounted.get('[role="toolbar"]');
    expect(toolbar.classes()).toContain("xw-toolbar");
    expect(toolbar.classes()).not.toContain("xw-toolbar--question");
  });
});
