/**
 * Exam workspace question list, Markera mode.
 *
 * Expected behavior:
 *   The list head is one row: the title "Frågor (N)", then one tool group with
 *   the collapse glyph (when the desktop handle is wanted), Ny uppgift and the
 *   glyph-only Markera toggle (data-test exam-workspace-marking-toggle,
 *   "Markera frågor"). The toggle is pressed while marking and its glyph
 *   switches from an empty to a ticked checkbox. The bar under the head with
 *   "Skapa del av markerade (N)" exists only while marking. Every row keeps
 *   its mark cell. Only standalone questions carry a checkbox (a part and a
 *   question inside a part do not, G11); an ordering question's checkbox is
 *   disabled with its reason (G6). The group action is disabled at N = 0 and
 *   emits the ticks in document order (G10); pressing the toggle again clears
 *   the ticks and leaves the mode; while the workspace is busy every control
 *   is disabled.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceQuestionList from "./ExamWorkspaceQuestionList.vue";
import type {
  ExamWorkspaceItemEntry,
  ExamWorkspaceListEntry,
  ExamWorkspaceParentEntry,
} from "./examWorkspaceListEntries";

function question(
  id: string,
  label: string,
  options: { parentId?: string | null; kind?: "free_text" | "ordering" } = {},
): ExamWorkspaceItemEntry {
  return {
    aiKey: null,
    id,
    itemKind: options.kind ?? "free_text",
    kind: "item",
    label,
    parentId: options.parentId ?? null,
    points: 1,
    problem: null,
    status: "ok",
    text: `Text ${label}`,
    typeLabel: options.kind === "ordering" ? "Ordna" : "Fritext",
  };
}

function part(id: string, label: string, childIds: string[]): ExamWorkspaceParentEntry {
  return { childIds, id, kind: "parent", label, points: 2, text: "Delinstruktion" };
}

const ENTRIES: ExamWorkspaceListEntry[] = [
  question("item_001", "1"),
  part("parent_001", "2", ["item_002"]),
  question("item_002", "2a", { parentId: "parent_001" }),
  question("item_003", "3", { kind: "ordering" }),
  question("item_004", "4"),
  question("item_005", "5"),
];

const BAR = '[data-test="exam-workspace-marking-bar"]';
const GROUP = '[data-test="exam-workspace-group-marked"]';
const TOGGLE = '[data-test="exam-workspace-marking-toggle"]';
const ROW_MARK = ".row__mark";
/** The class that hides a row's mark cell while not marking. */
const IDLE_CELL = "row__mark--idle";

const mounted: Array<VueWrapper> = [];

function mountList(entries: ExamWorkspaceListEntry[] = ENTRIES, disabled = false, handle = false): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionList, {
    props: {
      handle,
      mismatches: [],
      canAdd: true,
      disabled,
      entries,
      examInstructionsPreview: null,
      overlay: false,
      questionCount: entries.filter((entry) => entry.kind === "item").length,
      selectedId: null,
      total: 5,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

function markBoxes(wrapper: VueWrapper): string[] {
  return wrapper
    .findAll('[data-test^="exam-workspace-mark-"]')
    .map((box) => box.attributes("data-test")!.replace("exam-workspace-mark-", ""));
}

function toggleGlyph(wrapper: VueWrapper): string {
  return wrapper.get(TOGGLE).findComponent(UiGlyph).props("meaning") as string;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceQuestionList Markera mode", () => {
  it("puts the title first, then collapse, Ny uppgift and Markera in one tool group", () => {
    const wrapper = mountList(ENTRIES, false, true);
    const head = wrapper.get(".list__head");

    expect(head.element.firstElementChild?.id).toBe("exam-workspace-list-title");
    expect(head.get("h2").text()).toBe("Frågor (5)");
    const tools = head.get(".xw-tools").findAll("button").map((button) => button.attributes("data-test"));
    expect(tools).toEqual(["exam-workspace-list-collapse", "exam-workspace-new", "exam-workspace-marking-toggle"]);
    expect(head.get('[data-test="exam-workspace-list-collapse"]').classes()).toEqual(["xw-tool"]);
    expect(head.get('[data-test="exam-workspace-new"]').classes()).toEqual(["xw-tool", "xw-tool--word"]);
    expect(head.get('[data-test="exam-workspace-new"]').text()).toBe("Ny uppgift");
  });

  it("leaves the collapse glyph out without the handle and keeps Ny uppgift before Markera", () => {
    const wrapper = mountList();

    const tools = wrapper.get(".list__head .xw-tools").findAll("button").map((button) => button.attributes("data-test"));
    expect(tools).toEqual(["exam-workspace-new", "exam-workspace-marking-toggle"]);
  });

  it("presses the glyph-only Markera toggle, switches its glyph and shows the bar only while marking", async () => {
    const wrapper = mountList();
    const toggle = wrapper.get(TOGGLE);

    expect(toggle.classes()).toEqual(["xw-tool"]);
    expect(toggle.attributes("type")).toBe("button");
    expect(toggle.text()).toBe("");
    expect(toggle.attributes("title")).toBe("Markera frågor");
    expect(toggle.attributes("aria-label")).toBe("Markera frågor");
    expect(toggle.attributes("aria-pressed")).toBe("false");
    expect(toggleGlyph(wrapper)).toBe("checkbox-off");
    expect(wrapper.find(BAR).exists()).toBe(false);
    expect(wrapper.find(GROUP).exists()).toBe(false);
    expect(wrapper.findAll(ROW_MARK)).toHaveLength(ENTRIES.length);
    expect(wrapper.findAll(`.${IDLE_CELL}`)).toHaveLength(ENTRIES.length);

    await toggle.trigger("click");

    expect(wrapper.get(TOGGLE).element).toBe(toggle.element);
    expect(wrapper.get(TOGGLE).attributes("aria-pressed")).toBe("true");
    expect(toggleGlyph(wrapper)).toBe("checkbox-on");
    expect(wrapper.get(BAR).findAll("button").map((button) => button.attributes("data-test"))).toEqual([
      "exam-workspace-group-marked",
    ]);
    expect(wrapper.findAll(ROW_MARK)).toHaveLength(ENTRIES.length);
    expect(wrapper.findAll(`.${IDLE_CELL}`)).toHaveLength(0);

    await wrapper.get(TOGGLE).trigger("click");

    expect(wrapper.get(TOGGLE).attributes("aria-pressed")).toBe("false");
    expect(toggleGlyph(wrapper)).toBe("checkbox-off");
    expect(wrapper.find(BAR).exists()).toBe(false);
    expect(wrapper.findAll(`.${IDLE_CELL}`)).toHaveLength(ENTRIES.length);
  });

  it("shows a checkbox per standalone question only", async () => {
    const wrapper = mountList();

    expect(markBoxes(wrapper)).toEqual(["item_001", "item_003", "item_004", "item_005"]);

    await wrapper.get(TOGGLE).trigger("click");

    expect(markBoxes(wrapper)).toEqual(["item_001", "item_003", "item_004", "item_005"]);
  });

  it("disables an ordering question's checkbox with the reason", async () => {
    const wrapper = mountList();
    await wrapper.get(TOGGLE).trigger("click");

    const ordering = wrapper.get('[data-test="exam-workspace-mark-item_003"]');
    expect(ordering.attributes("disabled")).toBeDefined();
    expect(ordering.attributes("title")).toBe("Ordna-frågor kan inte ligga i en del");

    const freeText = wrapper.get('[data-test="exam-workspace-mark-item_001"]');
    expect(freeText.attributes("disabled")).toBeUndefined();
  });

  it("emits the ticks in document order and disables the action at zero", async () => {
    const wrapper = mountList();
    await wrapper.get(TOGGLE).trigger("click");

    const group = wrapper.get(GROUP);
    expect(group.text()).toBe("Skapa del av markerade (0)");
    expect(group.attributes("disabled")).toBeDefined();

    await wrapper.get('[data-test="exam-workspace-mark-item_005"]').setValue(true);
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);

    expect(wrapper.get(GROUP).text()).toBe("Skapa del av markerade (2)");
    await wrapper.get(GROUP).trigger("click");

    expect(wrapper.emitted("group")).toEqual([[["item_001", "item_005"]]]);
  });

  it("leaves the mode once the ticked questions become a part's children", async () => {
    const wrapper = mountList();
    await wrapper.get(TOGGLE).trigger("click");
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);
    await wrapper.get(GROUP).trigger("click");

    await wrapper.setProps({
      entries: [
        part("parent_002", "1", ["item_002", "item_001"]),
        question("item_002", "1a", { parentId: "parent_002" }),
        question("item_001", "1b", { parentId: "parent_002" }),
      ],
    });

    expect(wrapper.get(TOGGLE).attributes("aria-pressed")).toBe("false");
    expect(wrapper.find(BAR).exists()).toBe(false);
    expect(markBoxes(wrapper)).toEqual([]);
  });

  it("clears the ticks and leaves the mode when the pressed toggle is pressed again", async () => {
    const wrapper = mountList();
    await wrapper.get(TOGGLE).trigger("click");
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);

    await wrapper.get(TOGGLE).trigger("click");

    expect(wrapper.get(TOGGLE).attributes("aria-pressed")).toBe("false");
    expect(wrapper.find(BAR).exists()).toBe(false);

    await wrapper.get(TOGGLE).trigger("click");
    expect(wrapper.get(GROUP).text()).toBe("Skapa del av markerade (0)");
  });

  it("disables the checkboxes and the bar while the workspace is busy", async () => {
    const wrapper = mountList();
    await wrapper.get(TOGGLE).trigger("click");
    await wrapper.get('[data-test="exam-workspace-mark-item_001"]').setValue(true);

    await wrapper.setProps({ disabled: true });

    expect(wrapper.get('[data-test="exam-workspace-mark-item_001"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get(GROUP).attributes("disabled")).toBeDefined();
    expect(wrapper.get(TOGGLE).attributes("disabled")).toBeDefined();
  });
});
