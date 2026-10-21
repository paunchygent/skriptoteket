/** Consumer proof for the shared toggle's opt-in label measurement contract. */
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { UiSegmentedToggle } from "../../components/ui";

class LabelResizeObserver implements ResizeObserver {
  static instances: LabelResizeObserver[] = [];
  readonly elements = new Set<Element>();
  readonly disconnect = vi.fn(() => this.elements.clear());

  constructor(private readonly callback: ResizeObserverCallback) {
    LabelResizeObserver.instances.push(this);
  }

  observe(element: Element): void {
    this.elements.add(element);
  }

  unobserve(element: Element): void {
    this.elements.delete(element);
  }

  resize(): void {
    this.callback([], this);
  }
}

const options = [
  { value: "short", label: "Kort" },
  { value: "long", label: "Längre alternativ" },
];

describe("shared segmented toggle consumer", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    LabelResizeObserver.instances = [];
  });

  it("leaves natural labels unmeasured unless equal widths are requested", async () => {
    vi.stubGlobal("ResizeObserver", LabelResizeObserver);
    const measure = vi.spyOn(Element.prototype, "getBoundingClientRect");
    const wrapper = mount(UiSegmentedToggle, {
      props: { modelValue: "short", options, width: "auto" },
    });

    expect(LabelResizeObserver.instances).toHaveLength(0);
    expect(measure).not.toHaveBeenCalled();
    expect(wrapper.get('[role="radio"]').text()).toBe("Kort");
    const target = wrapper.findAll('[role="radio"]')
      .find((button) => button.text() === "Längre alternativ");
    if (!target) throw new Error('Missing radio with label "Längre alternativ"');
    await target.trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([["long"]]);
    wrapper.unmount();
  });

  it("uses the widest measured label, follows resize, and stops when opted out", async () => {
    vi.stubGlobal("ResizeObserver", LabelResizeObserver);
    let longWidth = 122.4;
    vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      return new DOMRect(0, 0, this.textContent === "Kort" ? 36 : longWidth, 16);
    });
    const wrapper = mount(UiSegmentedToggle, {
      props: { modelValue: "short", options, width: "auto", equalizeOptionWidth: true },
    });
    const observer = LabelResizeObserver.instances[0]!;
    expect(observer.elements.size).toBe(2);
    observer.resize();
    await nextTick();

    function minimumLabelWidths(): string[] {
      return options.map((option) => {
        const button = wrapper.findAll('[role="radio"]')
          .find((candidate) => candidate.text() === option.label);
        if (!button) throw new Error(`Missing radio with label "${option.label}"`);
        const label = button.find("span");
        if (!label.exists()) throw new Error(`Missing label element for "${option.label}"`);
        const element = label.element;
        if (!(element instanceof HTMLElement)) {
          throw new Error(`Label element for "${option.label}" is not measurable`);
        }
        return element.style.minWidth;
      });
    }
    // Geometry is supplied by the host observer double: jsdom does not lay out text.
    expect(minimumLabelWidths()).toEqual(["123px", "123px"]);
    longWidth = 90.1;
    observer.resize();
    await nextTick();
    expect(minimumLabelWidths()).toEqual(["91px", "91px"]);

    await wrapper.setProps({ equalizeOptionWidth: false });
    expect(observer.disconnect).toHaveBeenCalledOnce();
    expect(observer.elements.size).toBe(0);
    expect(wrapper.findAll('[role="radio"] span')).toHaveLength(0);
    expect(wrapper.findAll('[role="radio"]').map((button) => button.text()))
      .toEqual(options.map((option) => option.label));
    wrapper.unmount();
  });
});
