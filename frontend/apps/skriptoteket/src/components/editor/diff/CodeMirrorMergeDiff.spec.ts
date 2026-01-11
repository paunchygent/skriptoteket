import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { mountWithContext } from "../../../test/utils";
import AiVirtualFileDiffViewer from "./AiVirtualFileDiffViewer.vue";
import CodeMirrorMergeDiff from "./CodeMirrorMergeDiff.vue";
import VirtualFileDiffViewer from "./VirtualFileDiffViewer.vue";

describe("CodeMirror merge diff layout", () => {
  it("makes the merge view scrollable", async () => {
    const wrapper = mountWithContext(CodeMirrorMergeDiff, {
      props: {
        beforeText: "a\n",
        afterText: "b\n",
      },
    });

    await nextTick();

    const mergeView = wrapper.element.querySelector(".cm-mergeView") as HTMLElement | null;
    expect(mergeView).toBeTruthy();
    expect(mergeView?.style.overflow).toBe("auto");
  });

  it("keeps AI diff viewer height-constrained", async () => {
    const wrapper = mountWithContext(AiVirtualFileDiffViewer, {
      props: {
        items: [
          {
            virtualFileId: "tool.py",
            beforeText: "print('hej')\n",
            afterText: "print('klar')\n",
          },
        ],
      },
    });

    await nextTick();

    expect(wrapper.classes()).toContain("h-full");
    expect(wrapper.element.querySelector(".cm-mergeView")).toBeTruthy();
  });

  it("keeps general diff viewer height-constrained", async () => {
    const wrapper = mountWithContext(VirtualFileDiffViewer, {
      props: {
        items: [
          {
            virtualFileId: "tool.py",
            beforeText: "print('hej')\n",
            afterText: "print('klar')\n",
          },
        ],
      },
    });

    await nextTick();

    expect(wrapper.classes()).toContain("h-full");
    expect(wrapper.element.querySelector(".cm-mergeView")).toBeTruthy();
  });
});
