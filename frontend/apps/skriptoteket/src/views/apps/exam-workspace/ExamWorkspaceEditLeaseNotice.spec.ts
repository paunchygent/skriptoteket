/**
 * Exam workspace edit lease notice.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4,
 * unit A3, copy decided by the user 2026-10-19):
 *   A read-only tab shows `Provet kan bara redigeras i den andra fliken
 *   tills du tar över.` with a `Ta över` action; pressing it emits the
 *   takeover the lease session runs. While the takeover waits the same slot
 *   shows `Väntar på att kunna redigera här …` and the button is disabled.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceEditLeaseNotice from "./ExamWorkspaceEditLeaseNotice.vue";

describe("ExamWorkspaceEditLeaseNotice", () => {
  it("shows the lease notice with a Ta över action", async () => {
    const wrapper = mount(ExamWorkspaceEditLeaseNotice, { props: { waiting: false } });

    expect(wrapper.get('[data-test="exam-workspace-edit-lease-text"]').text()).toBe(
      "Provet kan bara redigeras i den andra fliken tills du tar över.",
    );
    const action = wrapper.get('[data-test="exam-workspace-edit-lease-takeover"]');
    expect(action.text()).toBe("Ta över");
    expect(action.attributes("disabled")).toBeUndefined();

    await action.trigger("click");
    expect(wrapper.emitted("takeover")).toHaveLength(1);
  });

  it("shows the waiting text and disables Ta över while the takeover waits", () => {
    const wrapper = mount(ExamWorkspaceEditLeaseNotice, { props: { waiting: true } });

    expect(wrapper.get('[data-test="exam-workspace-edit-lease-text"]').text()).toBe(
      "Väntar på att kunna redigera här …",
    );
    expect(
      wrapper.get('[data-test="exam-workspace-edit-lease-takeover"]').attributes("disabled"),
    ).toBeDefined();
  });
});
