/**
 * Seat-style drag preview helpers.
 *
 * This module builds a transient DOM drag image that matches the circular seat
 * token language used on the live seating canvas. The preview stays outside
 * Vue's render cycle because HTML drag images must be available synchronously
 * during `dragstart`.
 */

import { ROOM_SEAT_SIZE } from "./roomSeatPresentation";

const PREVIEW_TEST_ID = "seat-drag-preview";

function createSeatDragPreview(studentName: string): HTMLDivElement {
  const preview = document.createElement("div");
  preview.dataset.test = PREVIEW_TEST_ID;
  preview.className = [
    "flex",
    "items-center",
    "justify-center",
    "rounded-full",
    "border",
    "bg-white",
    "text-center",
    "text-navy",
    "shadow-brutal-sm",
  ].join(" ");
  Object.assign(preview.style, {
    position: "fixed",
    top: "-9999px",
    left: "0",
    width: `${ROOM_SEAT_SIZE}px`,
    height: `${ROOM_SEAT_SIZE}px`,
    pointerEvents: "none",
  });

  const content = document.createElement("div");
  content.className = "flex h-full w-full items-center justify-center px-2";

  const name = document.createElement("span");
  name.className = "line-clamp-2 text-xs font-semibold leading-tight";
  name.textContent = studentName;

  content.appendChild(name);
  preview.appendChild(content);
  return preview;
}

export function setSeatStyledStudentDragPreview(
  event: DragEvent,
  studentName: string,
): void {
  if (!event.dataTransfer || !(event.currentTarget instanceof HTMLElement)) {
    return;
  }

  const preview = createSeatDragPreview(studentName);
  document.body.appendChild(preview);
  event.dataTransfer.setDragImage(preview, ROOM_SEAT_SIZE / 2, ROOM_SEAT_SIZE / 2);

  const cleanup = () => {
    preview.remove();
  };

  event.currentTarget.addEventListener("dragend", cleanup, { once: true });
  window.setTimeout(cleanup, 1_000);
}
