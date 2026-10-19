/**
 * Exam workspace edit lease notice.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4,
 * unit K8):
 *   A read-only tab shows `Öppet i en annan flik` with a `Ta över` action;
 *   pressing it emits the takeover the lease session runs. While the
 *   takeover waits the button is disabled.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceEditLeaseNotice from "./ExamWorkspaceEditLeaseNotice.vue";

describe("ExamWorkspaceEditLeaseNotice", () => {
  it("shows Öppet i en annan flik with a Ta över action", async () => {
    const wrapper = mount(ExamWorkspaceEditLeaseNotice, { props: { waiting: false } });

    expect(wrapper.get('[data-test="exam-workspace-edit-lease-text"]').text()).toBe(
      "Öppet i en annan flik",
    );
    const action = wrapper.get('[data-test="exam-workspace-edit-lease-takeover"]');
    expect(action.text()).toBe("Ta över");
    expect(action.attributes("disabled")).toBeUndefined();

    await action.trigger("click");
    expect(wrapper.emitted("takeover")).toHaveLength(1);
  });

  it("disables Ta över while the takeover waits", () => {
    const wrapper = mount(ExamWorkspaceEditLeaseNotice, { props: { waiting: true } });

    expect(
      wrapper.get('[data-test="exam-workspace-edit-lease-takeover"]').attributes("disabled"),
    ).toBeDefined();
  });
});
