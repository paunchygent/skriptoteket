/**
 * Exam workspace gap answer list: one row per accepted answer.
 *
 * Expected behavior:
 *   The list edits one list of accepted answers as one text input per
 *   answer with a remove glyph per row and a glyph-only add button
 *   ("Lägg till svar" accessible name and tooltip) under the rows. Typing
 *   never emits; an input's `change`, removing a row and the
 *   exposed `commit()` emit the normalized list (trimmed, empties dropped,
 *   exact duplicates collapsed, commas kept) exactly once per change.
 *   Every row input, add, Enter-add and remove also emits the normalized
 *   list as `draft` so the owner can follow unsaved typing.
 *   Enter in a row inserts an empty row below it and focuses it without
 *   dropping it on commit. Removing the only row leaves one empty row.
 *   The list caps at 100 rows, ignores Enter during IME composition,
 *   follows external `values` only while nothing is pending, and emits
 *   nothing while disabled.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceGapAnswerList from "./ExamWorkspaceGapAnswerList.vue";

const TEST_ID = "exam-workspace-gap-answers";

function mountList(props: {
  values?: string[];
  label?: string;
  disabled?: boolean;
  testId?: string;
} = {}) {
  return mount(ExamWorkspaceGapAnswerList, {
    attachTo: document.body,
    props: {
      label: "Godkända svar för lucka 1",
      testId: TEST_ID,
      values: [],
      ...props,
    },
  });
}

type Wrapper = ReturnType<typeof mountList>;

function inputs(wrapper: Wrapper) {
  return wrapper.findAll<HTMLInputElement>(`[data-test="${TEST_ID}-input"]`);
}

function removes(wrapper: Wrapper) {
  return wrapper.findAll<HTMLButtonElement>(`[data-test="${TEST_ID}-remove"]`);
}

function addButton(wrapper: Wrapper) {
  return wrapper.get<HTMLButtonElement>(`[data-test="${TEST_ID}-add"]`);
}

function commits(wrapper: Wrapper): string[][] {
  return (wrapper.emitted<[string[]]>("commit") ?? []).map((event) => event[0]);
}

function many(count: number): string[] {
  return Array.from({ length: count }, (_, index) => `svar ${index + 1}`);
}

describe("ExamWorkspaceGapAnswerList", () => {
  it("renders one row per value with numbered labels", () => {
    const wrapper = mountList({ values: ["x", "y", "z"] });
    const rows = inputs(wrapper);
    expect(rows).toHaveLength(3);
    expect(rows.map((row) => row.element.value)).toEqual(["x", "y", "z"]);
    expect(rows.map((row) => row.attributes("aria-label"))).toEqual(["Svar 1", "Svar 2", "Svar 3"]);
    expect(wrapper.get(`[data-test="${TEST_ID}"]`).attributes("role")).toBe("group");
    expect(wrapper.get(`[data-test="${TEST_ID}"]`).attributes("aria-label")).toBe(
      "Godkända svar för lucka 1",
    );
    wrapper.unmount();
  });

  it("renders exactly one empty row for empty values", () => {
    const wrapper = mountList({ values: [] });
    const rows = inputs(wrapper);
    expect(rows).toHaveLength(1);
    expect(rows[0].element.value).toBe("");
    expect(addButton(wrapper).text()).not.toContain("Lägg till svar");
    expect(addButton(wrapper).attributes("aria-label")).toBe("Lägg till svar");
    expect(addButton(wrapper).attributes("title")).toBe("Lägg till svar");
    wrapper.unmount();
  });

  it("emits the full normalized list once on change and nothing twice", async () => {
    const wrapper = mountList({ values: ["a"] });
    const row = inputs(wrapper)[0];
    row.element.value = "b";
    await row.trigger("input");
    expect(wrapper.emitted("commit")).toBeUndefined();
    await row.trigger("change");
    expect(commits(wrapper)).toEqual([["b"]]);
    await row.trigger("change");
    expect(commits(wrapper)).toEqual([["b"]]);
    wrapper.unmount();
  });

  it("keeps a value containing a comma as one value", async () => {
    const wrapper = mountList({ values: ["Stockholm"] });
    const row = inputs(wrapper)[0];
    row.element.value = "Stockholm, Sverige";
    await row.trigger("input");
    await row.trigger("change");
    expect(inputs(wrapper)).toHaveLength(1);
    expect(commits(wrapper)).toEqual([["Stockholm, Sverige"]]);
    wrapper.unmount();
  });

  it("drops whitespace-only rows and collapses duplicates after trim", async () => {
    const wrapper = mountList({ values: ["a", " a ", "   ", ""] });
    await inputs(wrapper)[0].trigger("change");
    expect(commits(wrapper)).toEqual([["a"]]);
    wrapper.unmount();
  });

  it("inserts Enter rows directly below the current row, focused, surviving a commit", async () => {
    const wrapper = mountList({ values: ["a", "b", "c"] });
    const first = inputs(wrapper)[0];
    first.element.value = "ax";
    await first.trigger("input");
    await first.trigger("keydown", { key: "Enter" });
    await wrapper.vm.$nextTick();
    const afterEnter = inputs(wrapper);
    expect(afterEnter).toHaveLength(4);
    expect(afterEnter.map((row) => row.element.value)).toEqual(["ax", "", "b", "c"]);
    expect(document.activeElement).toBe(afterEnter[1].element);
    await afterEnter[0].trigger("change");
    expect(commits(wrapper)).toEqual([["ax", "b", "c"]]);
    const afterCommit = inputs(wrapper);
    expect(afterCommit).toHaveLength(4);
    expect(afterCommit[1].element.value).toBe("");
    wrapper.unmount();
  });

  it("removes a row and emits without it; removing the only row leaves one empty row", async () => {
    const wrapper = mountList({ values: ["a", "b"] });
    await removes(wrapper)[0].trigger("click");
    expect(commits(wrapper)).toEqual([["b"]]);
    expect(inputs(wrapper).map((row) => row.element.value)).toEqual(["b"]);
    wrapper.unmount();

    const single = mountList({ values: ["solo"] });
    await removes(single)[0].trigger("click");
    expect(commits(single)).toEqual([[]]);
    const rows = inputs(single);
    expect(rows).toHaveLength(1);
    expect(rows[0].element.value).toBe("");
    single.unmount();
  });

  it("keeps the DOM identity of surviving rows when a middle row is removed", async () => {
    const wrapper = mountList({ values: ["a", "b", "c"] });
    const third = inputs(wrapper)[2].element;
    await removes(wrapper)[1].trigger("click");
    await wrapper.vm.$nextTick();
    const rows = inputs(wrapper);
    expect(rows).toHaveLength(2);
    expect(rows[1].element).toBe(third);
    expect(rows[1].element.value).toBe("c");
    expect(commits(wrapper)).toEqual([["a", "c"]]);
    wrapper.unmount();
  });

  it("disables add at 100 rows with its tooltip and keeps it enabled at 99", async () => {
    const full = mountList({ values: many(100) });
    const capped = addButton(full);
    expect(capped.element.disabled).toBe(true);
    expect(capped.attributes("title")).toBe("Högst 100 svar");
    await inputs(full)[0].trigger("keydown", { key: "Enter" });
    expect(inputs(full)).toHaveLength(100);
    full.unmount();

    const room = mountList({ values: many(99) });
    expect(addButton(room).element.disabled).toBe(false);
    room.unmount();
  });

  it("ignores Enter while an IME composition is active", async () => {
    const wrapper = mountList({ values: ["a"] });
    await inputs(wrapper)[0].trigger("keydown", { key: "Enter", isComposing: true });
    expect(inputs(wrapper)).toHaveLength(1);
    wrapper.unmount();
  });

  it("replaces rows on external values change only while nothing is pending", async () => {
    const clean = mountList({ values: ["a"] });
    await clean.setProps({ values: ["x", "y"] });
    expect(inputs(clean).map((row) => row.element.value)).toEqual(["x", "y"]);
    clean.unmount();

    const typing = mountList({ values: ["a"] });
    const row = inputs(typing)[0];
    row.element.value = "pågående";
    await row.trigger("input");
    await typing.setProps({ values: ["x"] });
    expect(inputs(typing)[0].element.value).toBe("pågående");
    expect(typing.emitted("commit")).toBeUndefined();
    typing.unmount();
  });

  it("disables every control and emits nothing while disabled", async () => {
    const wrapper = mountList({ values: ["a"], disabled: true });
    expect(inputs(wrapper)[0].element.disabled).toBe(true);
    expect(removes(wrapper)[0].element.disabled).toBe(true);
    expect(addButton(wrapper).element.disabled).toBe(true);
    const row = inputs(wrapper)[0];
    row.element.value = "b";
    await row.trigger("input");
    await row.trigger("change");
    await addButton(wrapper).trigger("click");
    await row.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("commit")).toBeUndefined();
    expect(inputs(wrapper)).toHaveLength(1);
    wrapper.unmount();
  });

  it("emits pending typing through the exposed commit without touching rows", async () => {
    const wrapper = mountList({ values: ["a"] });
    const row = inputs(wrapper)[0];
    row.element.value = "b";
    await row.trigger("input");
    wrapper.vm.commit();
    expect(commits(wrapper)).toEqual([["b"]]);
    expect(inputs(wrapper).map((entry) => entry.element.value)).toEqual(["b"]);
    wrapper.unmount();
  });

  it("focuses the first row through the exposed focusFirst", () => {
    const wrapper = mountList({ values: ["a", "b"] });
    wrapper.vm.focusFirst();
    expect(document.activeElement).toBe(inputs(wrapper)[0].element);
    wrapper.unmount();
  });

  it("keeps a focused empty row when external values replace the rows", async () => {
    const wrapper = mountList({ values: ["a"] });
    await inputs(wrapper)[0].trigger("keydown", { key: "Enter" });
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(inputs(wrapper)[1].element);
    await wrapper.setProps({ values: ["a", "b"] });
    const rows = inputs(wrapper);
    expect(rows.map((row) => row.element.value)).toEqual(["a", "b", ""]);
    expect(document.activeElement).toBe(rows[2].element);
    wrapper.unmount();
  });

  it("labels remove buttons for assistive technology", () => {
    const wrapper = mountList({ values: ["a"] });
    const remove = removes(wrapper)[0];
    expect(remove.attributes("aria-label")).toBe("Ta bort svaret");
    expect(remove.attributes("title")).toBe("Ta bort svaret");
    wrapper.unmount();
  });
});

describe("ExamWorkspaceGapAnswerList draft", () => {
  function drafts(wrapper: Wrapper): string[][] {
    return (wrapper.emitted<[string[]]>("draft") ?? []).map((event) => event[0]);
  }

  it("emits the normalized list on every row input without committing", async () => {
    const wrapper = mountList({ values: ["a"] });
    const row = inputs(wrapper)[0];
    row.element.value = "ab";
    await row.trigger("input");
    expect(drafts(wrapper)).toEqual([["ab"]]);
    expect(wrapper.emitted("commit")).toBeUndefined();
    wrapper.unmount();
  });

  it("emits the unchanged list when the add button adds an empty row", async () => {
    const wrapper = mountList({ values: ["a"] });
    await addButton(wrapper).trigger("click");
    expect(drafts(wrapper)).toEqual([["a"]]);
    expect(inputs(wrapper)).toHaveLength(2);
    wrapper.unmount();
  });

  it("emits the unchanged list when Enter adds a row", async () => {
    const wrapper = mountList({ values: ["a"] });
    await inputs(wrapper)[0].trigger("keydown", { key: "Enter" });
    expect(drafts(wrapper)).toEqual([["a"]]);
    expect(inputs(wrapper)).toHaveLength(2);
    wrapper.unmount();
  });

  it("emits the list without the removed row on remove", async () => {
    const wrapper = mountList({ values: ["a", "b"] });
    await removes(wrapper)[0].trigger("click");
    expect(drafts(wrapper)).toEqual([["b"]]);
    expect(commits(wrapper)).toEqual([["b"]]);
    wrapper.unmount();
  });

  it("emits nothing while disabled", async () => {
    const wrapper = mountList({ values: ["a"], disabled: true });
    const row = inputs(wrapper)[0];
    row.element.value = "b";
    await row.trigger("input");
    expect(wrapper.emitted("draft")).toBeUndefined();
    wrapper.unmount();
  });
});
