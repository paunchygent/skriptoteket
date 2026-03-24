import { describe, expect, it } from "vitest";

import {
  buildParsedFixtures,
  buildParsedSeats,
  fixtureFits,
  hydrateRoomTemplateEditor,
  seatKey,
} from "./roomTemplateEditorDomain";

describe("roomTemplateEditorDomain", () => {
  it("lets wall fixtures share the room edge with seats without consuming floor space", () => {
    expect(
      fixtureFits(
        [],
        [seatKey(0, 0)],
        "door",
        0,
        0,
        { cols: 14, rows: 9 },
      ),
    ).toBe(true);
  });

  it("hydrates editable room state from a saved room template", () => {
    expect(
      hydrateRoomTemplateEditor({
        id: "template-1",
        name: "Sal 101",
        grid_cols: 14,
        grid_rows: 9,
        seats: [{ id: "seat-1", x: 96, y: 192, zone: null }],
        fixtures: [{ id: "door-1", type: "door", x: 0, y: 0, width: 96, height: 96, label: null }],
      }),
    ).toEqual({
      name: "Sal 101",
      gridCols: 14,
      gridRows: 9,
      seatCells: ["2:1"],
      fixtures: [
        {
          id: "door-1",
          type: "door",
          row: 0,
          col: 0,
          width: 1,
          height: 1,
          label: null,
        },
      ],
    });
  });

  it("serializes editor state into the saved seat and fixture contract", () => {
    expect(buildParsedSeats([seatKey(0, 0), seatKey(1, 2)])).toEqual([
      { id: "seat-1", x: 0, y: 0, zone: null },
      { id: "seat-2", x: 192, y: 96, zone: null },
    ]);

    expect(buildParsedFixtures([
      {
        id: "fixture-1",
        type: "teacher_desk",
        row: 1,
        col: 2,
        width: 2,
        height: 1,
        label: "Kateder",
      },
    ])).toEqual([
      {
        id: "fixture-1",
        type: "teacher_desk",
        x: 192,
        y: 96,
        width: 192,
        height: 96,
        label: "Kateder",
      },
    ]);
  });
});
