/**
 * Exam workspace rich text entry.
 *
 * Expected behavior:
 *   One choice or matching entry edits as rich text: an edit emits the whole
 *   body and keeps the marks of the text it edits, and a disabled entry
 *   emits nothing.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEntry from "./ExamWorkspaceRichTextEntry.vue";

function mountEntry(body: NativeExamBodyParagraph[], disabled = false) {
  return mount(ExamWorkspaceRichTextEntry, {
    props: { body, disabled, label: "Text för svarsalternativ A", testId: "entry" },
  });
}

describe("ExamWorkspaceRichTextEntry", () => {
  it("emits the body keeping the mark of the edited text", async () => {
    const wrapper = mountEntry([
      {
        heading_level: null,
        segments: [
          { kind: "text", text: "Syre", marks: ["italic"] },
          { kind: "text", text: " och kväve", marks: [] },
        ],
      },
    ]);
    const element = wrapper.get('[data-test="entry"]').element as HTMLElement;
    const marked = element.querySelector('em[data-mark="italic"]')!.firstChild as Text;

    marked.data = "Syrgas";
    await wrapper.get('[data-test="entry"]').trigger("input");

    expect(wrapper.emitted("updateBody")).toEqual([
      [
        [
          {
            heading_level: null,
            segments: [
              { kind: "text", marks: ["italic"], text: "Syrgas" },
              { kind: "text", marks: [], text: " och kväve" },
            ],
          },
        ],
      ],
    ]);
  });

  it("emits nothing while the entry is disabled", async () => {
    const wrapper = mountEntry(
      [{ heading_level: null, segments: [{ kind: "text", text: "Syre", marks: [] }] }],
      true,
    );
    const element = wrapper.get('[data-test="entry"]').element as HTMLElement;
    (element.firstChild as Text).data = "Syrgas";
    await wrapper.get('[data-test="entry"]').trigger("input");

    expect(wrapper.emitted("updateBody")).toBeUndefined();
  });
});
