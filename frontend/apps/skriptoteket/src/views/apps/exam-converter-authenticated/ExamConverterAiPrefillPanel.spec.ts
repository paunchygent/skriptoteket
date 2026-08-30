import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamConverterAiPrefillPanel from "./ExamConverterAiPrefillPanel.vue";

describe("ExamConverterAiPrefillPanel", () => {
  it("renders the approved equal two-action token surface", async () => {
    const wrapper = mount(ExamConverterAiPrefillPanel, {
      props: {
        disabled: false,
        focus: "questions",
        reviewCount: 12,
      },
    });

    const actions = wrapper.get('[data-test="exam-converter-ai-prefill-actions"]');
    expect(actions.classes()).toContain("grid-cols-2");
    expect(actions.findAll("button")).toHaveLength(2);
    expect(wrapper.get('[data-test="exam-converter-open-ai-prefill-action"]').classes())
      .toContain("btn-primary");
    expect(wrapper.get('[data-test="exam-converter-accept-all-ai-prefill-action"]').classes())
      .toContain("btn-ghost");
    expect(wrapper.get('[data-test="exam-converter-open-ai-prefill-action"]').find(".lucide-clipboard-list").exists())
      .toBe(true);
    expect(wrapper.get('[data-test="exam-converter-accept-all-ai-prefill-action"]').find(".lucide-check").exists())
      .toBe(true);
    expect(wrapper.text()).toContain("12 frågor att granska.");

    await wrapper.get('[data-test="exam-converter-open-ai-prefill-action"]').trigger("click");
    await wrapper.get('[data-test="exam-converter-accept-all-ai-prefill-action"]').trigger("click");

    expect(wrapper.emitted("openQuestions")).toHaveLength(1);
    expect(wrapper.emitted("acceptAllAdvisoryCandidates")).toHaveLength(1);
  });

  it("disables both actions while persistence is running", () => {
    const wrapper = mount(ExamConverterAiPrefillPanel, {
      props: {
        disabled: true,
        focus: "candidate",
        reviewCount: 2,
      },
    });

    expect(wrapper.get('[data-test="exam-converter-open-ai-prefill-action"]').attributes())
      .toHaveProperty("disabled");
    expect(wrapper.get('[data-test="exam-converter-accept-all-ai-prefill-action"]').attributes())
      .toHaveProperty("disabled");
  });
});
