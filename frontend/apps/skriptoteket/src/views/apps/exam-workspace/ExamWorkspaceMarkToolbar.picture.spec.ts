/**
 * Exam workspace mark toolbar: the picture control.
 *
 * Expected behavior (TASK-SKRIPT-39-10-04, unit U6):
 *   The toolbar shows no picture control unless the host takes pictures.
 *   With `showPicture` the control is its own group after the headings, one
 *   `.xw-tool` button: "Lägg till bild", or "Byt bild" while a whole picture
 *   is selected. While `pictureBusy` the glyph spins with the busy meaning
 *   and the button locks. Clicking opens the PNG/JPEG picker; choosing a
 *   file emits it as `addPicture` and resets the picker, so the same file
 *   can be chosen again. The button keeps its slot and size in every state.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";

const TOOL = "[data-test='exam-workspace-picture-tool']";
const INPUT = "[data-test='exam-workspace-picture-input']";

function pictureFile(): File {
  return new File(["png!"], "bild.png", { type: "image/png" });
}

describe("ExamWorkspaceMarkToolbar picture control", () => {
  it("shows no picture control unless the host takes pictures", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showHeadings: true } });

    expect(wrapper.find(TOOL).exists()).toBe(false);
    expect(wrapper.find(INPUT).exists()).toBe(false);
    wrapper.unmount();
  });

  it("puts the picture group after the headings with one tool in it", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, {
      props: { showGap: true, showHeadings: true, showPicture: true },
    });

    const groups = wrapper.findAll(".xw-tools");
    const last = groups.at(-1)!;
    expect(last.findAll("button").map((button) => button.attributes("data-test"))).toEqual([
      "exam-workspace-picture-tool",
    ]);
    const children = Array.from(wrapper.get("[role='toolbar']").element.children).map((child) =>
      child.classList.contains("xw-toolsep") ? "sep" : "group",
    );
    expect(children).toEqual(["group", "sep", "group", "sep", "group", "sep", "group"]);
    wrapper.unmount();
  });

  it("follows the last shown group when the headings are hidden", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showPicture: true } });

    const groups = wrapper.findAll(".xw-tools");
    expect(groups).toHaveLength(2);
    expect(groups.at(-1)!.find(TOOL).exists()).toBe(true);
    wrapper.unmount();
  });

  it("names the button Lägg till bild, or Byt bild with a picture selected", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showPicture: true } });

    const tool = wrapper.get(TOOL);
    expect(tool.attributes("aria-label")).toBe("Lägg till bild");
    expect(tool.attributes("title")).toBe("Lägg till bild");

    await wrapper.setProps({ pictureSelected: true });
    expect(wrapper.get(TOOL).attributes("aria-label")).toBe("Byt bild");
    expect(wrapper.get(TOOL).attributes("title")).toBe("Byt bild");
    wrapper.unmount();
  });

  it("renders the add-picture glyph idle", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showPicture: true } });

    const trailing = wrapper.findAllComponents(UiGlyph).at(-1)!;
    expect(trailing.props("meaning")).toBe("add-picture");
    expect(trailing.props("size")).toBe(16);
    expect(trailing.classes()).not.toContain("xw-spin");
    wrapper.unmount();
  });

  it("spins the busy glyph and locks the button while busy", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, {
      props: { showPicture: true, pictureBusy: true },
    });

    const tool = wrapper.get(TOOL);
    expect(tool.attributes("disabled")).toBeDefined();
    const glyph = wrapper.findAllComponents(UiGlyph).at(-1)!;
    expect(glyph.props("meaning")).toBe("busy");
    expect(glyph.classes()).toContain("xw-spin");
    expect(tool.attributes("aria-label")).toBe("Lägg till bild");

    await wrapper.setProps({ pictureBusy: false });
    expect(wrapper.get(TOOL).attributes("disabled")).toBeUndefined();
    expect(wrapper.findAllComponents(UiGlyph).at(-1)!.props("meaning")).toBe("add-picture");
    wrapper.unmount();
  });

  it("locks the button while disabled", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, {
      props: { showPicture: true, disabled: true },
    });

    expect(wrapper.get(TOOL).attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("opens the PNG/JPEG picker on click", async () => {
    const click = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => {});
    try {
      const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showPicture: true } });

      const input = wrapper.get(INPUT).element as HTMLInputElement;
      expect(input.getAttribute("type")).toBe("file");
      expect(input.getAttribute("accept")).toBe("image/png,image/jpeg");
      expect(input.hasAttribute("hidden")).toBe(true);

      await wrapper.get(TOOL).trigger("click");
      expect(click).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    } finally {
      click.mockRestore();
    }
  });

  it("emits the chosen file and resets the picker", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showPicture: true } });
    const file = pictureFile();
    const input = wrapper.get(INPUT).element as HTMLInputElement;
    Object.defineProperty(input, "files", { value: [file], configurable: true });

    await wrapper.get(INPUT).trigger("change");

    expect(wrapper.emitted("addPicture")).toEqual([[file]]);
    expect(input.value).toBe("");
    expect(input.files?.[0]).toBe(file);
    wrapper.unmount();
  });

  it("emits nothing when the picker closes without a file", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showPicture: true } });
    const input = wrapper.get(INPUT).element as HTMLInputElement;
    Object.defineProperty(input, "files", { value: [], configurable: true });

    await wrapper.get(INPUT).trigger("change");

    expect(wrapper.emitted("addPicture")).toBeUndefined();
    wrapper.unmount();
  });
});
