import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import RoomSceneSurface from "./RoomSceneSurface.vue";

describe("RoomSceneSurface", () => {
  it("reuses the shared presentation seam for preview fixtures", () => {
    const wrapper = mount(RoomSceneSurface, {
      props: {
        grid: { cols: 14, rows: 9 },
        seats: [],
        fixtures: [
          { id: "door-1", type: "door", x: 0, y: 192, width: 96, height: 96, label: null },
          { id: "whiteboard-1", type: "whiteboard", x: 288, y: 0, width: 192, height: 96, label: null },
          { id: "whiteboard-2", type: "whiteboard", x: 480, y: 0, width: 96, height: 96, label: null },
        ],
      },
    });

    expect(wrapper.text()).toContain("Dörr");
    expect(wrapper.text().match(/Whiteboard/g)).toHaveLength(1);
    expect(wrapper.html()).toContain("writing-mode: vertical-lr;");
  });

  it("can preserve raw fixture identities for builder editing surfaces while keeping wall annotation semantics", () => {
    const wrapper = mount(RoomSceneSurface, {
      props: {
        grid: { cols: 14, rows: 9 },
        seats: [],
        fixtures: [
          { id: "door-1", type: "door", x: 0, y: 192, width: 96, height: 96, label: null },
          { id: "whiteboard-1", type: "whiteboard", x: 288, y: 0, width: 192, height: 96, label: null },
          { id: "whiteboard-2", type: "whiteboard", x: 480, y: 0, width: 96, height: 96, label: null },
        ],
        normalizePresentation: false,
      },
    });

    expect(wrapper.text().match(/Whiteboard/g)).toHaveLength(2);
    expect(wrapper.text()).toContain("Dörr");
    expect(wrapper.html()).toContain("writing-mode: vertical-lr;");
  });
});
