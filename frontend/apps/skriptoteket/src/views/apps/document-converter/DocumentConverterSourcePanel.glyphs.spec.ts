/** File ordering must not turn directional actions into disclosure toggles. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { UiGlyph } from "../../../components/ui/shared";
import DocumentConverterSourcePanel from "./DocumentConverterSourcePanel.vue";

const files = [{ name: "a.pdf" }, { name: "b.pdf" }];

function mountSources(saved: boolean) {
  return mount(DocumentConverterSourcePanel, {
    props: {
      workspaceMode: "single_file",
      projectCssFiles: [],
      projectHtmlFiles: [],
      projectImageFiles: [],
      projectSelectedHtmlFilename: null,
      singleFileModeLabel: saved ? "Mina filer" : "Lokal fil",
      singleFileSavedFiles: saved ? files : [],
      singleFileSourceName: "",
      singleFileUploadFiles: saved ? [] : files,
    },
  });
}

describe("DocumentConverterSourcePanel glyph contract", () => {
  it.each([false, true])("preserves directional intent, accessible names and ordering effects (saved=%s)", async (saved) => {
    const wrapper = mountSources(saved);
    const moveEvent = saved ? "moveSingleFileSavedFile" : "moveSingleFileUpload";
    const removeEvent = saved ? "removeSingleFileSavedFile" : "removeSingleFileUpload";
    const firstUp = wrapper.get('[data-testid="document-converter-source-move-up-0"]');
    const firstDown = wrapper.get('[data-testid="document-converter-source-move-down-0"]');
    const lastUp = wrapper.get('[data-testid="document-converter-source-move-up-1"]');
    const lastDown = wrapper.get('[data-testid="document-converter-source-move-down-1"]');
    const remove = wrapper.get('[data-testid="document-converter-source-remove-1"]');

    for (const [control, meaning, label] of [
      [firstUp, "move-up", "Flytta upp"],
      [lastUp, "move-up", "Flytta upp"],
      [firstDown, "move-down", "Flytta ned"],
      [lastDown, "move-down", "Flytta ned"],
      [remove, "delete", "Ta bort fil"],
    ] as const) {
      expect(control.attributes("aria-label")).toBe(label);
      expect(control.attributes("title")).toBe(label);
      const glyph = control.getComponent(UiGlyph);
      expect(glyph.props("meaning")).toBe(meaning);
      expect(glyph.get("svg").attributes("aria-hidden")).toBe("true");
      expect(glyph.attributes("aria-label")).toBeUndefined();
    }

    await firstUp.trigger("click");
    await lastDown.trigger("click");
    expect(wrapper.emitted(moveEvent)).toBeUndefined();
    await firstDown.trigger("click");
    await lastUp.trigger("click");
    expect(wrapper.emitted(moveEvent)).toEqual([[0, 1], [1, 0]]);
    await remove.trigger("click");
    expect(wrapper.emitted(removeEvent)).toEqual([[1]]);
    expect(wrapper.emitted(saved ? "moveSingleFileUpload" : "moveSingleFileSavedFile")).toBeUndefined();
  });
});
