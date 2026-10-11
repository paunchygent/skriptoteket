import { defineComponent } from "vue";
import { describe, expect, it } from "vitest";

import { mountWithContext } from "../../test/utils";
import groupingPy from "../../../../../../src/skriptoteket/script_bank/scripts/gruppgenerator/grouping.py?raw";
import rosterPy from "../../../../../../src/skriptoteket/script_bank/scripts/gruppgenerator/roster.py?raw";
import EditorSourceCodePanel from "./EditorSourceCodePanel.vue";

const CodeMirrorEditorStub = defineComponent({
  name: "CodeMirrorEditor",
  props: {
    modelValue: { type: String, default: "" },
    extensions: { type: Array, default: () => [] },
    readOnly: { type: Boolean, default: false },
    language: { type: [Object, Array], default: null },
  },
  emits: ["update:modelValue", "viewReady"],
  template: '<div data-test="codemirror-stub" :data-value="modelValue" />',
});

function mountPanel(bundleFiles: Record<string, string> = {}) {
  return mountWithContext(EditorSourceCodePanel, {
    props: {
      entrypoint: "tool.py",
      sourceCode: "print('entrypoint')\n",
      isReadOnly: false,
      bundleFiles,
    },
    global: {
      stubs: { CodeMirrorEditor: CodeMirrorEditorStub },
    },
  });
}

describe("EditorSourceCodePanel bundle file tabs", () => {
  it("renders no file tab strip for a single-file tool", () => {
    const wrapper = mountPanel({});

    expect(wrapper.find('[role="tablist"]').exists()).toBe(false);
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(0);
    expect(wrapper.findAllComponents(CodeMirrorEditorStub)).toHaveLength(1);
  });

  it("shows tool.py first, then bundle files sorted, and edits the selected file only", async () => {
    const wrapper = mountPanel({ "roster.py": rosterPy, "grouping.py": groupingPy });

    const tabs = wrapper.findAll('[role="tab"]');
    expect(tabs.map((tab) => tab.text())).toEqual(["tool.py", "grouping.py", "roster.py"]);
    expect(tabs[0]!.attributes("aria-selected")).toBe("true");

    await tabs[2]!.trigger("click");

    expect(wrapper.findAll('[role="tab"]')[2]!.attributes("aria-selected")).toBe("true");

    const editors = wrapper.findAllComponents(CodeMirrorEditorStub);
    expect(editors).toHaveLength(2);
    expect(editors[1]!.props("modelValue")).toBe(rosterPy);

    editors[1]!.vm.$emit("update:modelValue", "print('edited roster')\n");
    await wrapper.vm.$nextTick();

    const bundleUpdates = wrapper.emitted("update:bundleFiles");
    expect(bundleUpdates).toHaveLength(1);
    expect(bundleUpdates![0]![0]).toEqual({
      "roster.py": "print('edited roster')\n",
      "grouping.py": groupingPy,
    });
    expect(wrapper.emitted("update:sourceCode")).toBeUndefined();
  });

  it("falls back to the entrypoint when the active bundle file disappears", async () => {
    const wrapper = mountPanel({ "roster.py": rosterPy });

    await wrapper.findAll('[role="tab"]')[1]!.trigger("click");
    expect(wrapper.findAllComponents(CodeMirrorEditorStub)).toHaveLength(2);

    await wrapper.setProps({ bundleFiles: {} });

    expect(wrapper.find('[role="tablist"]').exists()).toBe(false);
    expect(wrapper.findAllComponents(CodeMirrorEditorStub)).toHaveLength(1);
  });
});
