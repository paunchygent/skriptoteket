import { nextTick } from "vue";
import { describe, expect, it } from "vitest";

import type { EditorWorkingCopyFields } from "../../composables/editor/editorPersistence";
import { mountWithContext } from "../../test/utils";
import EditorComparePanel from "./EditorComparePanel.vue";
import VirtualFileDiffViewer from "./diff/VirtualFileDiffViewer.vue";

const baseFiles = {
  "tool.py": "print('base')\n",
  "entrypoint.txt": "main.py",
  "settings_schema.json": "{}",
  "input_schema.json": "{}",
  "usage_instructions.md": "",
};

const workingCopyFields: EditorWorkingCopyFields = {
  entrypoint: "main.py",
  sourceCode: "print('working')\n",
  settingsSchemaText: "{}",
  inputSchemaText: "{}",
  usageInstructions: "",
  bundleFiles: { "target-only.py": "print('target')\n" },
};

async function flushAsyncWork(): Promise<void> {
  for (let index = 0; index < 4; index += 1) {
    await Promise.resolve();
    await nextTick();
  }
}

describe("EditorComparePanel bundle files", () => {
  it("lists bundle files from both sides with an empty side when the file exists only once", async () => {
    const wrapper = mountWithContext(EditorComparePanel, {
      props: {
        versions: [],
        baseVersion: null,
        baseFiles,
        baseBundleFiles: { "base-only.py": "print('base only')\n" },
        compareTarget: { kind: "working" },
        activeFileId: null,
        baseIsDirty: false,
        canCompareWorkingCopy: true,
        workingCopyProvider: async () => workingCopyFields,
      },
    });

    await flushAsyncWork();

    const items = wrapper.findComponent(VirtualFileDiffViewer).props("items");
    const targetOnly = items.find((item) => item.virtualFileId === "bundle/target-only.py");
    const baseOnly = items.find((item) => item.virtualFileId === "bundle/base-only.py");

    expect(targetOnly).toEqual({
      virtualFileId: "bundle/target-only.py",
      beforeText: "print('target')\n",
      afterText: "",
    });
    expect(baseOnly).toEqual({
      virtualFileId: "bundle/base-only.py",
      beforeText: "",
      afterText: "print('base only')\n",
    });

    const optionValues = wrapper
      .findAll("#editor-diff-file option")
      .map((option) => option.attributes("value"));
    expect(optionValues).toContain("bundle/target-only.py");
    expect(optionValues).toContain("bundle/base-only.py");
  });
});
