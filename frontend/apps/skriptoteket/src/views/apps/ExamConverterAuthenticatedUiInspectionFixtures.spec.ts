/**
 * Exam Converter authenticated UI-inspection fixture behavior.
 *
 * Slice purpose:
 *   Keep internal-browser inspection states durable so agents can review the
 *   real authenticated Exam Converter UI without unsupported local file upload.
 *
 * Expected behavior:
 *   The dev/test fixture route renders the production shell components with a
 *   fixture-backed post-conversion projection, keeps production runtime actions
 *   separate, and preserves dense workspace layout states for live inspection.
 *
 * Recommended implementation shape:
 *   Use a guarded fixture catalog and pass the fixture id as a route prop to
 *   the real authenticated view. Do not use query hooks or browser-local state
 *   mutation.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import {
  getExamConverterUiInspectionFixture,
  isExamConverterUiInspectionEnabled,
} from "./exam-converter-authenticated/examConverterUiInspectionFixtures";

describe("ExamConverterAuthenticatedView UI inspection fixtures", () => {
  it("guards the fixture catalog to dev/test surfaces", () => {
    expect(isExamConverterUiInspectionEnabled({ DEV: false, MODE: "production" })).toBe(
      false,
    );
    expect(isExamConverterUiInspectionEnabled({ DEV: false, MODE: "test" })).toBe(true);
    expect(isExamConverterUiInspectionEnabled({ DEV: true, MODE: "development" })).toBe(
      true,
    );
    expect(getExamConverterUiInspectionFixture("not-a-fixture")).toBeNull();
  });

  it("renders the all-complete QTI-blocked state without question-review work", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView, {
      props: { inspectionFixtureId: "complete-qti-blocked" },
    });

    await flushPromises();

    expect(wrapper.get('[data-test="exam-converter-host-frame"]').attributes()).toMatchObject({
      "data-inspection-fixture-id": "complete-qti-blocked",
    });
    expect(wrapper.text()).toContain("Provet är konverterat");
    expect(wrapper.text()).not.toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.find('[data-test="exam-converter-review-decision-gate"]').exists()).toBe(
      false,
    );
    expect(wrapper.find('[data-test="exam-converter-files-readiness-list"]').exists()).toBe(
      true,
    );
    expect(wrapper.get('[data-test="exam-converter-file-row-qti_package"]').text()).toContain(
      "Kunde inte skapas",
    );
    expect(wrapper.get('[data-test="exam-converter-file-reason-qti_package"]').text()).toBe(
      "QTI-filen kunde inte skapas. Granska rapporten.",
    );
    expect(wrapper.text()).not.toContain("Orsak:");
    expect(wrapper.text()).not.toContain("qti_package_export_disabled");
    expect(wrapper.text()).not.toContain("unsupported_target_shape");
  });

  it("renders missing-facit review state through the same question shell", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView, {
      props: { inspectionFixtureId: "missing-facit" },
    });

    await flushPromises();

    expect(wrapper.find('[data-test="exam-converter-question-review-shell"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-test="exam-converter-review-decision-gate"]').exists()).toBe(
      true,
    );
    expect(wrapper.get('[data-test="exam-converter-review-questions-action"]').text()).toContain(
      "Granska",
    );
    expect(wrapper.text()).toContain("Vilket påstående beskriver DNA bäst?");
  });

  it("renders producer-returned persisted corrections for browser proof", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView, {
      props: { inspectionFixtureId: "persisted-corrections" },
    });

    await flushPromises();

    expect(wrapper.text()).toContain("Vilket påstående beskriver DNA bäst?");
    expect(wrapper.find('[data-test="exam-converter-review-decision-gate"]').exists()).toBe(
      false,
    );
    expect(wrapper.get('[data-test="exam-converter-effective-answer-key-summary"]').text()).toContain(
      "2",
    );
    expect(
      wrapper.get('[data-test="exam-converter-effective-choice-2"]').classes(),
    ).not.toContain("bg-success");
    expect(
      wrapper.get('[data-test="exam-converter-effective-choice-ordinal-2"]').classes(),
    ).toContain("bg-success");
  });

  it("renders provider-only advisory failure with the approved retry affordance", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView, {
      props: { inspectionFixtureId: "provider-only-advisory-failure" },
    });

    await flushPromises();

    const retryPanel = wrapper.get('[data-test="exam-converter-advisory-retry-panel"]');
    const retryButton = wrapper.get('[data-test="exam-converter-advisory-retry-action"]');
    expect(retryPanel.text()).toContain("Det gick inte att ta fram ett facitförslag.");
    expect(retryButton.text()).toBe("Försök igen");
    expect(retryButton.html()).toContain("lucide-refresh-cw");
    expect(retryPanel.text()).not.toContain("AI");
    expect(retryPanel.text()).not.toContain("provider");
  });
});
