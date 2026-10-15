/**
 * Exam workspace phone question bar AI key status.
 *
 * Expected behavior:
 *   The picker states the current question's AI key status with one IconAi and
 *   its accessible label: "Tolkad av AI" or "Förslag från AI". The attention
 *   warning stays beside it, and a question without an AI mark keeps the
 *   reserved slot with no glyph so the picker text stays in place.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { IconAi, IconWarning } from "../../../components/icons";
import ExamWorkspacePhoneQuestionBar from "./ExamWorkspacePhoneQuestionBar.vue";

function mountBar(aiKeyLabel: string | null, needsAttention = false) {
  return mount(ExamWorkspacePhoneQuestionBar, {
    props: {
      aiKeyLabel,
      needsAttention,
      position: 2,
      sheetOpen: false,
      total: 5,
    },
  });
}

describe("ExamWorkspacePhoneQuestionBar AI key status", () => {
  it("shows the AI glyph with its accessible status for an interpreted key", () => {
    const wrapper = mountBar("Tolkad av AI");

    const mark = wrapper.get('[data-test="exam-workspace-phone-ai-key"]');
    expect(mark.attributes("role")).toBe("img");
    expect(mark.attributes("aria-label")).toBe("Tolkad av AI");
    expect(mark.attributes("title")).toBe("Tolkad av AI");
    expect(mark.text()).toBe("");
    expect(mark.findComponent(IconAi).exists()).toBe(true);
    expect(wrapper.findAllComponents(IconAi)).toHaveLength(1);
  });

  it("labels an invented key as a proposal and keeps the attention warning", () => {
    const wrapper = mountBar("Förslag från AI", true);

    expect(wrapper.get('[data-test="exam-workspace-phone-ai-key"]').attributes("aria-label")).toBe(
      "Förslag från AI",
    );
    expect(wrapper.findComponent(IconWarning).exists()).toBe(true);
  });

  it("keeps the reserved slot and no glyph when the current key has no AI mark", () => {
    const wrapper = mountBar(null);

    expect(wrapper.find('[data-test="exam-workspace-phone-ai-slot"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-phone-ai-key"]').exists()).toBe(false);
    expect(wrapper.findAllComponents(IconAi)).toHaveLength(0);
  });
});
