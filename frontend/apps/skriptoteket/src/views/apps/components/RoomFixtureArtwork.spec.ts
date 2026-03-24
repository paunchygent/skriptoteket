import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { RoomFixture } from "../classroomPlannerTypes";
import RoomFixtureArtwork from "./RoomFixtureArtwork.vue";

const grid = { cols: 14, rows: 9 };

describe("RoomFixtureArtwork", () => {
  it("shows canonical labels for wall markers and teacher desk", () => {
    const whiteboard = mount(RoomFixtureArtwork, {
      props: {
        fixture: {
          id: "whiteboard-1",
          type: "whiteboard",
          x: 0,
          y: 0,
          width: 288,
          height: 96,
          label: "Whiteboard",
        },
        fixtures: [],
        grid,
      },
    });
    const door = mount(RoomFixtureArtwork, {
      props: {
        fixture: {
          id: "door-1",
          type: "door",
          x: 0,
          y: 384,
          width: 96,
          height: 96,
          label: null,
          displayLabel: "Dörr",
          labelVisible: true,
          labelOrientation: "vertical",
          wallSide: "left",
          tone: "outline",
        },
        fixtures: [],
        grid,
      },
    });
    const teacherDesk = mount(RoomFixtureArtwork, {
      props: {
        fixture: {
          id: "desk-1",
          type: "teacher_desk",
          x: 96,
          y: 96,
          width: 192,
          height: 96,
          label: null,
          displayLabel: "Kateder",
          labelVisible: true,
          tone: "strong",
        },
        fixtures: [],
        grid,
      },
    });

    expect(whiteboard.text()).toContain("Whiteboard");
    expect(door.text()).toContain("Dörr");
    expect(door.html()).toContain("writing-mode: vertical-rl;");
    expect(teacherDesk.text()).toContain("Kateder");
    expect(teacherDesk.html()).toContain("text-white");
  });

  it("renders round tables as truly round", () => {
    const wrapper = mount(RoomFixtureArtwork, {
      props: {
        fixture: {
          id: "round-table-1",
          type: "round_table",
          x: 96,
          y: 96,
          width: 192,
          height: 192,
          label: null,
        },
        fixtures: [],
        grid,
      },
    });

    expect(wrapper.html()).toContain("rounded-full border-2 border-navy");
  });

  it("extends adjacent benches into one continuous bench in the builder grid", () => {
    const fixtures: RoomFixture[] = [
      { id: "bench-left", type: "bench", x: 96, y: 192, width: 96, height: 96, label: null },
      { id: "bench-middle", type: "bench", x: 192, y: 192, width: 96, height: 96, label: null },
      { id: "bench-right", type: "bench", x: 288, y: 192, width: 96, height: 96, label: null },
    ];

    const wrapper = mount(RoomFixtureArtwork, {
      props: {
        fixture: fixtures[1],
        fixtures,
        grid,
        surface: "builder-grid",
      },
    });

    expect(wrapper.html()).toContain("left: -4px;");
    expect(wrapper.html()).toContain("right: -4px;");
  });
});
