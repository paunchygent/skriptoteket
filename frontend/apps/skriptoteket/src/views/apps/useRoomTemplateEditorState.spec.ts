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
});
