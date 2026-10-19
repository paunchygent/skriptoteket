/**
 * Exam workspace gap popover: accepted answers as one row per answer.
 *
 * Expected behavior:
 *   The text-gap section edits accepted answers as one row per answer: the
 *   heading drops the old comma wording, commas stay ordinary characters in a
 *   value, editing a row then leaving the popover commits the full list
 *   exactly once, Enter in a row adds a row without closing, Escape after
 *   typing closes discarded with no commit even when a `change` fires late,
 *   and "Visa som text" follows unsaved typing and commits before it emits.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamGap } from "../../../api/examWorkspace";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import { documentControl, popoverRoot } from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";

const ITEM_ID = "item_001";
const GAP_ID = "gap_002";
const GAP_NUMBER = 2;

function mountPopover(gap: NativeExamGap) {
  return mount(ExamWorkspaceGapPopover, {
    attachTo: document.body,
    props: {
      anchor: document.body,
      gap,
      gapId: GAP_ID,
      gapNumber: GAP_NUMBER,
      itemId: ITEM_ID,
    },
  });
}

function rowInputs(): HTMLInputElement[] {
  return Array.from(
    document.querySelectorAll<HTMLInputElement>(
      `[data-test="exam-workspace-gap-values-${GAP_ID}-input"]`,
    ),
  );
}

function firstRow() {
  return documentControl<HTMLInputElement>(
    `[data-test="exam-workspace-gap-values-${GAP_ID}-input"]`,
  );
}

type CommitEvent = [string, string, string[]];

function commits(wrapper: ReturnType<typeof mountPopover>): CommitEvent[] {
  return wrapper.emitted<CommitEvent>("commit") ?? [];
}

function many(count: number): string[] {
  return Array.from({ length: count }, (_, index) => `svar ${index + 1}`);
}

describe("ExamWorkspaceGapPopover accepted answers", () => {
  it("heads the rows without the old comma wording and labels the list", () => {
    const wrapper = mountPopover(buildGap(GAP_ID, ["ett"]));

    expect(popoverRoot().textContent).toContain("Lucka 2 – godkända svar");
    expect(popoverRoot().textContent).not.toContain("kommaseparerade");
    expect(
      document.querySelector(`[data-test="exam-workspace-gap-values-${GAP_ID}"]`)?.getAttribute(
        "aria-label",
      ),
    ).toBe("Godkända svar för lucka 2");
    wrapper.unmount();
  });

  it("renders three saved values as three focused rows", () => {
    const wrapper = mountPopover(buildGap(GAP_ID, ["ett", "två", "tre"]));

    const rows = rowInputs();
    expect(rows).toHaveLength(3);
    expect(rows.map((row) => row.value)).toEqual(["ett", "två", "tre"]);
    expect(rows.map((row) => row.getAttribute("aria-label"))).toEqual(["Svar 1", "Svar 2", "Svar 3"]);
    expect(document.activeElement).toBe(rows[0]);
    expect(rows[0]?.selectionStart).toBe(0);
    expect(rows[0]?.selectionEnd).toBe("ett".length);
    wrapper.unmount();
  });

  it("commits the full list exactly once when focus leaves the popover", async () => {
    const wrapper = mountPopover(buildGap(GAP_ID, ["ett"]));
    const row = firstRow();
    row.element.value = "etta";
    await row.trigger("input");

    row.element.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
    row.element.dispatchEvent(new Event("change", { bubbles: true }));
    await wrapper.vm.$nextTick();

    expect(commits(wrapper)).toEqual([[ITEM_ID, GAP_ID, ["etta"]]]);
    expect(wrapper.emitted("close")).toEqual([[false]]);
    wrapper.unmount();
  });

  it("keeps a comma inside one value instead of splitting it", async () => {
    const wrapper = mountPopover(buildGap(GAP_ID, ["Stockholm"]));
    const row = firstRow();
    row.element.value = "Stockholm, Sverige";
    await row.trigger("input");
    await row.trigger("change");

    expect(commits(wrapper)).toEqual([[ITEM_ID, GAP_ID, ["Stockholm, Sverige"]]]);
    expect(rowInputs()).toHaveLength(1);
    wrapper.unmount();
  });

  it("adds a row on Enter without closing or committing", async () => {
    const wrapper = mountPopover(buildGap(GAP_ID, ["ett"]));
    const row = firstRow();
    row.element.value = "etta";
    await row.trigger("input");
    await row.trigger("keydown", { key: "Enter" });
    await wrapper.vm.$nextTick();

    expect(rowInputs()).toHaveLength(2);
    expect(rowInputs()[1]).toBe(document.activeElement);
    expect(wrapper.emitted("commit")).toBeUndefined();
    expect(wrapper.emitted("close")).toBeUndefined();
    wrapper.unmount();
  });

  it("discards on Escape with no commit even when a change fires late", async () => {
    const wrapper = mountPopover(buildGap(GAP_ID, ["ett"]));
    const row = firstRow();
    row.element.value = "kasta";
    await row.trigger("input");
    await row.trigger("keydown", { key: "Escape" });

    expect(wrapper.emitted("close")).toEqual([[true]]);

    row.element.dispatchEvent(new Event("change", { bubbles: true }));
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("commit")).toBeUndefined();
    wrapper.unmount();
  });

  it("disables Visa som text with no answers and enables it on unsaved typing", async () => {
    const wrapper = mountPopover(buildGap(GAP_ID, []));
    const button = documentControl<HTMLButtonElement>(
      '[data-test="exam-workspace-gap-as-text"]',
    );
    expect(button.element.disabled).toBe(true);

    const row = firstRow();
    row.element.value = "hundra";
    await row.trigger("input");

    expect(button.element.disabled).toBe(false);
    expect(
      document.querySelector('[data-test="exam-workspace-gap-as-text-disabled"]'),
    ).toBeNull();
    expect(wrapper.emitted("commit")).toBeUndefined();
    wrapper.unmount();
  });

  it("commits pending rows before it emits Visa som text", async () => {
    const wrapper = mountPopover(buildGap(GAP_ID, []));
    const row = firstRow();
    row.element.value = "hundra";
    await row.trigger("input");

    await documentControl('[data-test="exam-workspace-gap-as-text"]').trigger("click");

    expect(commits(wrapper)).toEqual([[ITEM_ID, GAP_ID, ["hundra"]]]);
    expect(wrapper.emitted("showGapAsText")).toEqual([[ITEM_ID, GAP_ID]]);
    const recorded = Object.keys(wrapper.emitted());
    expect(recorded.indexOf("commit")).toBeLessThan(recorded.indexOf("showGapAsText"));
    wrapper.unmount();
  });

  it("disables add at 100 rows with its tooltip", () => {
    const wrapper = mountPopover(buildGap(GAP_ID, many(100)));
    const add = documentControl<HTMLButtonElement>(
      `[data-test="exam-workspace-gap-values-${GAP_ID}-add"]`,
    );
    expect(rowInputs()).toHaveLength(100);
    expect(add.element.disabled).toBe(true);
    expect(add.attributes("title")).toBe("Högst 100 svar");
    wrapper.unmount();
  });
});
