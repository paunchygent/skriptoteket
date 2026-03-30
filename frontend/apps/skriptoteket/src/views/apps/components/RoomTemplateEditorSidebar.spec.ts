/**
 * Room-template editor sidebar tests.
 *
 * These tests lock the active-tool feedback pattern so the classroom editor
 * palette stays aligned with the stronger rules-rail selection language.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import RoomTemplateEditorSidebar from "./RoomTemplateEditorSidebar.vue";

function mountSidebar(selectedTool: "seat" | "whiteboard" | "erase" = "seat") {
  return mount(RoomTemplateEditorSidebar, {
    props: {
      name: "Sal 101",
      selectedTool,
      seatCount: 31,
      roomGrid: { cols: 13, rows: 9 },
      canShrinkCols: true,
      canShrinkRows: true,
      roomFixturePalette: [
        {
          type: "whiteboard",
          label: "Whiteboard",
          width: 3,
          height: 1,
          placementKind: "wall",
          defaultLabel: "Whiteboard",
        },
      ],
    },
  });
}

describe("RoomTemplateEditorSidebar", () => {
  it("shows explicit active-tool feedback for the selected room-editor tool", async () => {
    const wrapper = mountSidebar("seat");

    expect(wrapper.get('[data-test="room-template-selected-tool-meta"]').text()).toContain(
      "Aktivt verktyg",
    );
    expect(wrapper.get('[data-test="room-template-selected-tool-meta"]').text()).toContain(
      "Placera plats",
    );
    expect(wrapper.get('[data-test="room-template-tool-seat"]').classes()).toContain(
      "planner-choice-button-active",
    );

    await wrapper.get('[data-test="room-template-tool-whiteboard"]').trigger("click");
    expect(wrapper.emitted("update:selectedTool")).toEqual([["whiteboard"]]);

    await wrapper.setProps({ selectedTool: "whiteboard" });
    expect(wrapper.get('[data-test="room-template-selected-tool-meta"]').text()).toContain(
      "Whiteboard",
    );
    expect(wrapper.get('[data-test="room-template-selected-tool-help"]').text()).toContain("vägg");
    expect(wrapper.get('[data-test="room-template-tool-whiteboard"]').classes()).toContain(
      "planner-choice-button-active",
    );
  });

  it("keeps clear-room as a separate action below the tool feedback", async () => {
    const wrapper = mountSidebar("erase");

    expect(wrapper.get('[data-test="room-template-selected-tool-meta"]').text()).toContain("Sudda");

    await wrapper.get('[data-test="builder-clear-room"]').trigger("click");

    expect(wrapper.emitted("clear-room")).toEqual([[]]);
  });
});
