/**
 * Exam workspace gap answer list: synchronous removal focus.
 *
 * Expected behavior:
 *   Removing a row moves focus synchronously, before the row is spliced: to
 *   the previous row's input, else the next row's input, else the add button
 *   (removing the only row). The focused remove button is never detached
 *   while focused, so no focusout with a null relatedTarget reaches the
 *   owning popover and it stays open.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, nextTick } from "vue";

import ExamWorkspaceGapAnswerList from "./ExamWorkspaceGapAnswerList.vue";

const TEST_ID = "exam-workspace-gap-answers";

function mountList(values: string[]) {
  return mount(ExamWorkspaceGapAnswerList, {
    attachTo: document.body,
    props: {
      label: "Godkända svar för lucka 1",
      testId: TEST_ID,
      values,
    },
  });
}

type Wrapper = ReturnType<typeof mountList>;

function rowInputs(wrapper: Wrapper): HTMLInputElement[] {
  return wrapper
    .findAll(`[data-test="${TEST_ID}-input"]`)
    .map((row) => row.element as HTMLInputElement);
}

function removeButtons(wrapper: Wrapper): HTMLButtonElement[] {
  return wrapper
    .findAll(`[data-test="${TEST_ID}-remove"]`)
    .map((row) => row.element as HTMLButtonElement);
}

function addButton(wrapper: Wrapper): HTMLButtonElement {
  return wrapper.get(`[data-test="${TEST_ID}-add"]`).element as HTMLButtonElement;
}

function commits(wrapper: Wrapper): string[][] {
  return (wrapper.emitted<[string[]]>("commit") ?? []).map((event) => event[0]);
}

function releaseFocus(): void {
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur();
  }
  document.body.focus();
}

describe("ExamWorkspaceGapAnswerList removal focus", () => {
  it("focuses the previous row synchronously when a middle row is removed", async () => {
    const wrapper = mountList(["a", "b", "c"]);
    const target = rowInputs(wrapper)[0];
    expect(target.value).toBe("a");
    removeButtons(wrapper)[1].focus();
    removeButtons(wrapper)[1].click();
    expect(document.activeElement).toBe(target);

    await nextTick();
    expect(document.activeElement).toBe(target);
    expect(commits(wrapper)).toEqual([["a", "c"]]);
    expect(rowInputs(wrapper).map((row) => row.value)).toEqual(["a", "c"]);
    wrapper.unmount();
    releaseFocus();
  });

  it("focuses the next row synchronously when the first row is removed", async () => {
    const wrapper = mountList(["a", "b", "c"]);
    const target = rowInputs(wrapper)[1];
    expect(target.value).toBe("b");
    removeButtons(wrapper)[0].focus();
    removeButtons(wrapper)[0].click();
    expect(document.activeElement).toBe(target);

    await nextTick();
    expect(document.activeElement).toBe(target);
    expect(rowInputs(wrapper)[0]).toBe(target);
    expect(commits(wrapper)).toEqual([["b", "c"]]);
    expect(rowInputs(wrapper).map((row) => row.value)).toEqual(["b", "c"]);
    wrapper.unmount();
    releaseFocus();
  });

  it("focuses the add button when the only row is removed", async () => {
    const wrapper = mountList(["solo"]);
    removeButtons(wrapper)[0].focus();
    removeButtons(wrapper)[0].click();
    expect(document.activeElement).toBe(addButton(wrapper));

    await nextTick();
    expect(document.activeElement).toBe(addButton(wrapper));
    expect(commits(wrapper)).toEqual([[]]);
    const rows = rowInputs(wrapper);
    expect(rows).toHaveLength(1);
    expect(rows[0].value).toBe("");
    wrapper.unmount();
    releaseFocus();
  });

  it("fires no focusout with a null relatedTarget during removal", async () => {
    const seen: Array<EventTarget | null> = [];
    const Host = defineComponent({
      setup() {
        return () =>
          h(
            "div",
            {
              onFocusout: (event: FocusEvent) => {
                seen.push(event.relatedTarget);
              },
            },
            [
              h(ExamWorkspaceGapAnswerList, {
                label: "Godkända svar för lucka 1",
                testId: TEST_ID,
                values: ["a", "b", "c"],
              }),
            ],
          );
      },
    });
    const host = mount(Host, { attachTo: document.body });
    const removes = host.findAll(`[data-test="${TEST_ID}-remove"]`);
    (removes[1].element as HTMLButtonElement).focus();
    (removes[1].element as HTMLButtonElement).click();
    await nextTick();
    expect(seen.length).toBeGreaterThan(0);
    expect(seen.every((target) => target !== null)).toBe(true);
    host.unmount();
    releaseFocus();
  });
});
