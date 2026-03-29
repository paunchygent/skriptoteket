import { describe, expect, it } from "vitest";

import { mountWithContext } from "../../test/utils";
import UiDenseStatusPill from "./UiDenseStatusPill.vue";

describe("UiDenseStatusPill", () => {
  it("renders the shared dense status contract for warning states", () => {
    const wrapper = mountWithContext(UiDenseStatusPill, {
      props: {
        label: "Osparat",
        tone: "warning",
      },
    });

    expect(wrapper.text()).toContain("Osparat");
    expect(wrapper.get('[data-ui="dense-status-pill"]').classes()).toContain("h-[28px]");
    expect(wrapper.get('[data-ui="dense-status-pill"]').classes()).toContain("border-warning/50");
  });

  it("renders success states without interactive button behavior", () => {
    const wrapper = mountWithContext(UiDenseStatusPill, {
      props: {
        label: "Låst av dig",
        tone: "success",
      },
    });

    expect(wrapper.get('[data-ui="dense-status-pill"]').classes()).toContain("border-success/45");
    expect(wrapper.get('[data-ui="dense-status-pill"]').classes()).not.toContain("cursor-pointer");
  });
});
