/**
 * Exam workspace guest handoff notice (TASK-SKRIPT-41-02-05, U3).
 *
 * Expected behavior:
 *   A permanently refused browser draft shows one sentence and two
 *   glyph-only actions (download, remove); a full Mina filer shows its own
 *   sentence and three glyph-only actions in order (retry, download,
 *   remove). Every button carries its name in tooltip and aria-label only,
 *   with no visible text; while busy every button is disabled; clicks emit
 *   the matching event.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceGuestHandoffNotice from "./ExamWorkspaceGuestHandoffNotice.vue";
import {
  EXAM_WORKSPACE_GUEST_HANDOFF_DOWNLOAD_NAME,
  EXAM_WORKSPACE_GUEST_HANDOFF_PERMANENT_COPY,
  EXAM_WORKSPACE_GUEST_HANDOFF_REMOVE_NAME,
  EXAM_WORKSPACE_GUEST_HANDOFF_RETRY_NAME,
  EXAM_WORKSPACE_GUEST_HANDOFF_VAULT_FULL_COPY,
} from "./examWorkspaceGuestHandoffCopy";

describe("ExamWorkspaceGuestHandoffNotice", () => {
  it("shows the permanent sentence with download and remove glyphs only", () => {
    const wrapper = mount(ExamWorkspaceGuestHandoffNotice, {
      props: { busy: false, reason: "permanent" },
    });

    expect(wrapper.get('[data-test="exam-workspace-guest-handoff-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_GUEST_HANDOFF_PERMANENT_COPY,
    );
    const buttons = wrapper.findAll("button");
    expect(buttons.map((button) => button.attributes("data-test"))).toEqual([
      "exam-workspace-guest-handoff-download",
      "exam-workspace-guest-handoff-remove",
    ]);
    expect(wrapper.find('[data-test="exam-workspace-guest-handoff-retry"]').exists()).toBe(false);
    for (const button of buttons) {
      expect(button.text().trim()).toBe("");
    }
    const download = wrapper.get('[data-test="exam-workspace-guest-handoff-download"]');
    expect(download.attributes("title")).toBe(EXAM_WORKSPACE_GUEST_HANDOFF_DOWNLOAD_NAME);
    expect(download.attributes("aria-label")).toBe(EXAM_WORKSPACE_GUEST_HANDOFF_DOWNLOAD_NAME);
    const remove = wrapper.get('[data-test="exam-workspace-guest-handoff-remove"]');
    expect(remove.attributes("title")).toBe(EXAM_WORKSPACE_GUEST_HANDOFF_REMOVE_NAME);
    expect(remove.attributes("aria-label")).toBe(EXAM_WORKSPACE_GUEST_HANDOFF_REMOVE_NAME);
  });

  it("shows the vault-full sentence with retry first, then download and remove", () => {
    const wrapper = mount(ExamWorkspaceGuestHandoffNotice, {
      props: { busy: false, reason: "vault_full" },
    });

    expect(wrapper.get('[data-test="exam-workspace-guest-handoff-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_GUEST_HANDOFF_VAULT_FULL_COPY,
    );
    const buttons = wrapper.findAll("button");
    expect(buttons.map((button) => button.attributes("data-test"))).toEqual([
      "exam-workspace-guest-handoff-retry",
      "exam-workspace-guest-handoff-download",
      "exam-workspace-guest-handoff-remove",
    ]);
    for (const button of buttons) {
      expect(button.text().trim()).toBe("");
      expect(button.attributes("title")).toBe(button.attributes("aria-label"));
    }
    const retry = wrapper.get('[data-test="exam-workspace-guest-handoff-retry"]');
    expect(retry.attributes("title")).toBe(EXAM_WORKSPACE_GUEST_HANDOFF_RETRY_NAME);
  });

  it("disables every button while busy", () => {
    const wrapper = mount(ExamWorkspaceGuestHandoffNotice, {
      props: { busy: true, reason: "vault_full" },
    });

    const buttons = wrapper.findAll("button");
    expect(buttons).toHaveLength(3);
    for (const button of buttons) {
      expect(button.attributes("disabled")).toBeDefined();
    }
  });

  it("emits the matching event for each action", async () => {
    const wrapper = mount(ExamWorkspaceGuestHandoffNotice, {
      props: { busy: false, reason: "vault_full" },
    });

    await wrapper.get('[data-test="exam-workspace-guest-handoff-retry"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-guest-handoff-download"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-guest-handoff-remove"]').trigger("click");

    expect(wrapper.emitted("retry")).toHaveLength(1);
    expect(wrapper.emitted("download")).toHaveLength(1);
    expect(wrapper.emitted("remove")).toHaveLength(1);
  });
});
