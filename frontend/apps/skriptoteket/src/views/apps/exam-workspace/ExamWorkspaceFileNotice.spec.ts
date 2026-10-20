/**
 * Exam workspace shared file notice (TASK-SKRIPT-41-02-06, U3).
 *
 * Expected behavior:
 *   Each reason shows its own sentence: a refused browser draft names the
 *   browser, a full Mina filer names the retry, and an unreadable saved
 *   exam names Mina filer. Every reason renders glyph-only download and
 *   remove actions; only a full Mina filer renders the retry glyph first.
 *   Every button carries its name in tooltip and aria-label only, with no
 *   visible text; while busy every button is disabled; clicks emit the
 *   matching event.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceFileNotice from "./ExamWorkspaceFileNotice.vue";
import {
  EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_GUEST_VAULT_FULL_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_RETRY_NAME,
  EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY,
} from "./examWorkspaceFileNoticeCopy";

describe("ExamWorkspaceFileNotice", () => {
  it("shows the refused-draft sentence with download and remove glyphs only", () => {
    const wrapper = mount(ExamWorkspaceFileNotice, {
      props: { busy: false, reason: "guest_permanent" },
    });

    expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY,
    );
    const buttons = wrapper.findAll("button");
    expect(buttons.map((button) => button.attributes("data-test"))).toEqual([
      "exam-workspace-file-notice-download",
      "exam-workspace-file-notice-remove",
    ]);
    expect(wrapper.find('[data-test="exam-workspace-file-notice-retry"]').exists()).toBe(false);
    for (const button of buttons) {
      expect(button.text().trim()).toBe("");
    }
    const download = wrapper.get('[data-test="exam-workspace-file-notice-download"]');
    expect(download.attributes("title")).toBe(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME);
    expect(download.attributes("aria-label")).toBe(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME);
    const remove = wrapper.get('[data-test="exam-workspace-file-notice-remove"]');
    expect(remove.attributes("title")).toBe(EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME);
    expect(remove.attributes("aria-label")).toBe(EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME);
  });

  it("shows the vault-full sentence with retry first, then download and remove", () => {
    const wrapper = mount(ExamWorkspaceFileNotice, {
      props: { busy: false, reason: "guest_vault_full" },
    });

    expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_GUEST_VAULT_FULL_COPY,
    );
    const buttons = wrapper.findAll("button");
    expect(buttons.map((button) => button.attributes("data-test"))).toEqual([
      "exam-workspace-file-notice-retry",
      "exam-workspace-file-notice-download",
      "exam-workspace-file-notice-remove",
    ]);
    for (const button of buttons) {
      expect(button.text().trim()).toBe("");
      expect(button.attributes("title")).toBe(button.attributes("aria-label"));
    }
    const retry = wrapper.get('[data-test="exam-workspace-file-notice-retry"]');
    expect(retry.attributes("title")).toBe(EXAM_WORKSPACE_FILE_NOTICE_RETRY_NAME);
    const remove = wrapper.get('[data-test="exam-workspace-file-notice-remove"]');
    expect(remove.attributes("title")).toBe(EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME);
    expect(remove.attributes("aria-label")).toBe(EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME);
  });

  it("shows the unreadable-saved-exam sentence with Mina filer remove glyphs only", () => {
    const wrapper = mount(ExamWorkspaceFileNotice, {
      props: { busy: false, reason: "saved_unreadable" },
    });

    expect(wrapper.get('[data-test="exam-workspace-file-notice-text"]').text()).toBe(
      EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY,
    );
    const buttons = wrapper.findAll("button");
    expect(buttons.map((button) => button.attributes("data-test"))).toEqual([
      "exam-workspace-file-notice-download",
      "exam-workspace-file-notice-remove",
    ]);
    expect(wrapper.find('[data-test="exam-workspace-file-notice-retry"]').exists()).toBe(false);
    for (const button of buttons) {
      expect(button.text().trim()).toBe("");
    }
    const download = wrapper.get('[data-test="exam-workspace-file-notice-download"]');
    expect(download.attributes("title")).toBe(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME);
    expect(download.attributes("aria-label")).toBe(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME);
    const remove = wrapper.get('[data-test="exam-workspace-file-notice-remove"]');
    expect(remove.attributes("title")).toBe("Flytta provet till papperskorgen");
    expect(remove.attributes("aria-label")).toBe("Flytta provet till papperskorgen");
    expect(remove.text().trim()).toBe("");
  });

  it("disables every button while busy", () => {
    for (const reason of ["guest_permanent", "guest_vault_full", "saved_unreadable"] as const) {
      const wrapper = mount(ExamWorkspaceFileNotice, {
        props: { busy: true, reason },
      });

      const buttons = wrapper.findAll("button");
      expect(buttons.length).toBeGreaterThan(0);
      for (const button of buttons) {
        expect(button.attributes("disabled")).toBeDefined();
      }
    }
  });

  it("emits the matching event for each action", async () => {
    const wrapper = mount(ExamWorkspaceFileNotice, {
      props: { busy: false, reason: "guest_vault_full" },
    });

    await wrapper.get('[data-test="exam-workspace-file-notice-retry"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-file-notice-download"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-file-notice-remove"]').trigger("click");

    expect(wrapper.emitted("retry")).toHaveLength(1);
    expect(wrapper.emitted("download")).toHaveLength(1);
    expect(wrapper.emitted("remove")).toHaveLength(1);
  });
});
