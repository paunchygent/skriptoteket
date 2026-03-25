import { ref } from "vue";
import { describe, expect, it } from "vitest";

import { useRoomTemplateEditorState } from "./useRoomTemplateEditorState";

function createMouseEvent(): MouseEvent {
  const target = {
    getBoundingClientRect: () => ({
      left: 0,
      top: 0,
      width: 96,
      height: 96,
      right: 96,
      bottom: 96,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    }),
  } as unknown as EventTarget;

  return {
    clientX: 12,
    clientY: 12,
    currentTarget: target,
  } as MouseEvent;
}

describe("useRoomTemplateEditorState", () => {
  it("hydrates editor state from the current template and clears hover/tool transient state", () => {
    const template = ref({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [{ id: "door-1", type: "door" as const, x: 0, y: 0, width: 96, height: 96, label: null }],
    });

    const editor = useRoomTemplateEditorState(template);

    expect(editor.name.value).toBe("Sal 101");
    expect(editor.roomGrid.value).toEqual({ cols: 14, rows: 9 });
    expect(editor.parsedSeats.value).toHaveLength(1);
    expect(editor.parsedFixtures.value).toHaveLength(1);
    expect(editor.selectedTool.value).toBe("seat");
    expect(editor.error.value).toBeNull();
  });

  it("clears seats and fixtures without changing the current grid size", () => {
    const template = ref({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [{ id: "bench-1", type: "bench" as const, x: 96, y: 96, width: 96, height: 96, label: null }],
    });

    const editor = useRoomTemplateEditorState(template);
    editor.selectedTool.value = "bench";
    editor.clearRoomContents();

    expect(editor.roomGrid.value).toEqual({ cols: 14, rows: 9 });
    expect(editor.parsedSeats.value).toEqual([]);
    expect(editor.parsedFixtures.value).toEqual([]);
    expect(editor.selectedTool.value).toBe("seat");
  });

  it("updates ghost placement and parsed payload state from builder interactions", () => {
    const editor = useRoomTemplateEditorState(ref(null));
    editor.name.value = "Sal 101";
    editor.setBuilderViewportSize({ width: 800, height: 600 });

    editor.toggleGridCell(0, 0, createMouseEvent());
    expect(editor.parsedSeats.value).toHaveLength(1);

    editor.selectedTool.value = "whiteboard";
    editor.updateHoverState(createMouseEvent(), 0, 1);

    expect(editor.ghostPlacement.value).toMatchObject({
      row: 0,
      type: "whiteboard",
    });
    expect(editor.builderScalePercent.value).toBeGreaterThan(0);
    expect(editor.isValid.value).toBe(true);
  });

  it("keeps true wall fixtures attached when the room grows", () => {
    const template = ref({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [],
      fixtures: [{ id: "window-1", type: "window" as const, x: 1248, y: 192, width: 96, height: 192, label: null }],
    });

    const editor = useRoomTemplateEditorState(template);
    editor.resizeRoom("cols", 1);
    editor.resizeRoom("rows", 1);

    expect(editor.roomGrid.value).toEqual({ cols: 15, rows: 10 });
    expect(editor.parsedFixtures.value[0]).toMatchObject({
      x: 1344,
      y: 192,
      width: 96,
      height: 192,
    });
  });

  it("blocks seat placement on a reserved wall-fixture boundary cell", () => {
    const template = ref({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [],
      fixtures: [{ id: "door-1", type: "door" as const, x: 0, y: 0, width: 96, height: 96, label: null }],
    });

    const editor = useRoomTemplateEditorState(template);
    editor.toggleGridCell(0, 0, createMouseEvent());

    expect(editor.parsedSeats.value).toEqual([]);
    expect(editor.error.value).toContain("väggobjektet");
  });

  it("removes a floor fixture when the same selected tool is clicked again", () => {
    const template = ref({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [],
      fixtures: [{ id: "bench-1", type: "bench" as const, x: 96, y: 96, width: 96, height: 96, label: null }],
    });

    const editor = useRoomTemplateEditorState(template);
    editor.selectedTool.value = "bench";
    editor.updateHoverState(createMouseEvent(), 1, 1);

    expect(editor.ghostPlacement.value?.canPlace).toBe(true);

    editor.toggleGridCell(1, 1, createMouseEvent());

    expect(editor.parsedFixtures.value).toEqual([]);
    expect(editor.error.value).toBeNull();
  });

  it("removes a wall fixture when the same selected tool is clicked again", () => {
    const template = ref({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [],
      fixtures: [
        { id: "whiteboard-1", type: "whiteboard" as const, x: 0, y: 0, width: 288, height: 96, label: "Whiteboard" },
      ],
    });

    const editor = useRoomTemplateEditorState(template);
    editor.selectedTool.value = "whiteboard";
    editor.updateHoverState(createMouseEvent(), 0, 1);

    expect(editor.ghostPlacement.value?.canPlace).toBe(true);

    editor.toggleGridCell(0, 1, createMouseEvent());

    expect(editor.parsedFixtures.value).toEqual([]);
    expect(editor.error.value).toBeNull();
  });

  it("keeps the existing object when a different selected tool conflicts with it", () => {
    const template = ref({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [],
      fixtures: [{ id: "bench-1", type: "bench" as const, x: 96, y: 96, width: 96, height: 96, label: null }],
    });

    const editor = useRoomTemplateEditorState(template);
    editor.selectedTool.value = "square_table";
    editor.toggleGridCell(1, 1, createMouseEvent());

    expect(editor.parsedFixtures.value).toEqual([
      {
        id: "bench-1",
        type: "bench",
        x: 96,
        y: 96,
        width: 96,
        height: 96,
        label: null,
      },
    ]);
    expect(editor.error.value).toContain("krockar");
  });
});
