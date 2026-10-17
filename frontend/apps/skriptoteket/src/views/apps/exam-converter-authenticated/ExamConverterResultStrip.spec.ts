import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamConverterResultStrip from "./ExamConverterResultStrip.vue";
import type { ExamConverterResultStripState } from "./useExamConverterConversionState";

const outcomes: ExamConverterResultStripState[] = [
  {
    status: "failed",
    tone: "error",
    title: "Konverteringen av provet misslyckades",
    detail: null,
    nextAction: "Kontrollera provfilen och försök igen.",
    actionLabel: null,
    progress: null,
  },
  {
    status: "running",
    tone: "info",
    title: "Konverterar provet...",
    detail: null,
    nextAction: null,
    actionLabel: null,
    progress: null,
  },
  {
    status: "success",
    tone: "success",
    title: "Provet är konverterat",
    detail: null,
    nextAction: null,
    actionLabel: null,
    progress: null,
  },
  {
    status: "partial",
    tone: "warning",
    title: "Konverteringen av provet lyckades delvis",
    detail: null,
    nextAction: null,
    actionLabel: null,
    progress: null,
  },
];

describe("ExamConverterResultStrip announcements", () => {
  it.each(outcomes)("announces $status with the appropriate urgency", (result) => {
    const wrapper = mount(ExamConverterResultStrip, { props: { result } });
    const failed = result.status === "failed";
    const notice = wrapper.get(`[role="${failed ? "alert" : "status"}"]`);

    expect(notice.text()).toContain(result.title);
    expect(notice.attributes("aria-live")).toBe(failed ? "assertive" : "polite");
    if (failed) {
      expect(notice.attributes("aria-atomic")).toBe("true");
      expect(notice.text()).toContain(result.nextAction);
    } else {
      expect(wrapper.find('[role="alert"]').exists()).toBe(false);
      expect(wrapper.find('[aria-live="assertive"]').exists()).toBe(false);
    }
    wrapper.unmount();
  });
});
