/**
 * Exam workspace shared rich-text toolbar wiring.
 *
 * Expected behavior:
 *   The toolbar reads the registry's active rich target: its pressed marks
 *   and heading level, dispatching mark and heading toggles to that target.
 *   With no active target the toolbar reads empty marks and no heading, and
 *   both toggles do nothing. Deactivating the target returns the toolbar to
 *   the empty state.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";

import type { BodyMark } from "./examWorkspaceBodyMarks";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextHeadingLevel, RichTextTarget, RichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import { useExamWorkspaceRichTextToolbar } from "./useExamWorkspaceRichTextToolbar";

function fakeTarget(marks: BodyMark[], heading: RichTextHeadingLevel | null): RichTextTarget {
  return {
    marks: ref<BodyMark[]>(marks),
    acceptsPictures: false,
    selectedPictureId: ref(null),
    headingLevel: () => heading,
    toggleMark: vi.fn(),
    toggleHeading: vi.fn(),
    makeGap: vi.fn(),
    placePicture: vi.fn(),
    isLive: () => true,
    release: vi.fn(),
  };
}

// eslint-disable-next-line vue/one-component-per-file
const Child = defineComponent({
  setup() {
    return { ...useExamWorkspaceRichTextToolbar() };
  },
  render() {
    return h("div");
  },
});

/** The provider sits above the consumer, like ExamWorkspaceQuestionEditor above its fields. */
// eslint-disable-next-line vue/one-component-per-file
const Host = defineComponent({
  setup() {
    const registry = provideRichTextTargetRegistry();
    return { registry };
  },
  render() {
    return h(Child, { ref: "toolbar" });
  },
});

type HostWrapper = VueWrapper<InstanceType<typeof Host>>;

function toolbarOf(wrapper: HostWrapper) {
  return wrapper.findComponent(Child).vm;
}

function registryOf(wrapper: HostWrapper): RichTextTargetRegistry {
  return wrapper.vm.registry;
}

describe("useExamWorkspaceRichTextToolbar", () => {
  it("reads empty marks and no heading with no active target, and the toggles do nothing", () => {
    const wrapper = mount(Host);
    const toolbar = toolbarOf(wrapper);

    expect(toolbar.activeMarks).toEqual([]);
    expect(toolbar.activeHeading).toBeNull();
    expect(() => {
      toolbar.toggleMark("bold");
      toolbar.toggleHeading(2);
    }).not.toThrow();

    wrapper.unmount();
  });

  it("mirrors the active target and dispatches both toggles to it", () => {
    const wrapper = mount(Host);
    const toolbar = toolbarOf(wrapper);
    const target = fakeTarget(["bold", "italic"], 2);
    registryOf(wrapper).activate(target);

    expect(toolbar.activeMarks).toEqual(["bold", "italic"]);
    expect(toolbar.activeHeading).toBe(2);

    toolbar.toggleMark("underline");
    toolbar.toggleHeading(3);
    expect(target.toggleMark).toHaveBeenCalledWith("underline");
    expect(target.toggleHeading).toHaveBeenCalledWith(3);

    wrapper.unmount();
  });

  it("returns to empty marks and no heading after the target deactivates", () => {
    const wrapper = mount(Host);
    const toolbar = toolbarOf(wrapper);
    const target = fakeTarget(["bold"], 1);
    registryOf(wrapper).activate(target);
    expect(toolbar.activeMarks).toEqual(["bold"]);

    registryOf(wrapper).deactivate(target);

    expect(toolbar.activeMarks).toEqual([]);
    expect(toolbar.activeHeading).toBeNull();
    expect(() => {
      toolbar.toggleMark("bold");
    }).not.toThrow();

    wrapper.unmount();
  });
});
