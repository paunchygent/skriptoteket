/**
 * Phone classroom seat map interaction tests.
 *
 * These tests lock the phone seating map's touch contract: short press removes
 * a seated student, while long press plus release moves or swaps students.
 */

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import PlannerPhoneClassroomSeatMap from "./PlannerPhoneClassroomSeatMap.vue";

const template = {
  id: "template-1",
  name: "G20",
  grid_cols: 4,
  grid_rows: 2,
  fixtures: [],
  seats: [
    { id: "seat-1", x: 0, y: 0, zone: null },
    { id: "seat-2", x: 96, y: 0, zone: null },
    { id: "seat-3", x: 192, y: 0, zone: null },
  ],
};

const studentsById = {
  "student-1": { id: "student-1", display_name: "Ada Lovelace" },
  "student-2": { id: "student-2", display_name: "Bo Berg" },
};
const originalElementFromPoint = document.elementFromPoint;

function mountEditableMap(seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }]) {
  return mount(PlannerPhoneClassroomSeatMap, {
    props: {
      template,
      studentsById,
      seatAssignments,
      editableAssignments: true,
    },
  });
}

function mockSeatFromPoint(element: Element): void {
  Object.defineProperty(document, "elementFromPoint", {
    configurable: true,
    value: vi.fn(() => element),
  });
}

async function dispatchPointerEvent(
  element: Element,
  type: string,
  init: { clientX: number; clientY: number; pointerId?: number; pointerType?: string },
): Promise<void> {
  const event = new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    clientX: init.clientX,
    clientY: init.clientY,
  });
  Object.defineProperty(event, "pointerId", { value: init.pointerId ?? 1 });
  Object.defineProperty(event, "pointerType", { value: init.pointerType ?? "touch" });
  element.dispatchEvent(event);
  await nextTick();
}

async function dispatchTouchEvent(
  element: Element,
  type: string,
  distance: number,
  touches = 2,
): Promise<void> {
  const event = new Event(type, { bubbles: true, cancelable: true });
  Object.defineProperty(event, "touches", {
    value: {
      length: touches,
      item: (index: number) => {
        if (index >= touches) {
          return null;
        }
        return {
          clientX: index === 0 ? 0 : distance,
          clientY: 0,
        };
      },
    },
  });
  element.dispatchEvent(event);
  await nextTick();
}

describe("PlannerPhoneClassroomSeatMap", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    if (originalElementFromPoint) {
      Object.defineProperty(document, "elementFromPoint", {
        configurable: true,
        value: originalElementFromPoint,
      });
    } else {
      Reflect.deleteProperty(document, "elementFromPoint");
    }
    vi.useRealTimers();
  });

  it("removes a seated student on short press", async () => {
    const wrapper = mountEditableMap();

    await wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]').trigger("click");

    expect(wrapper.emitted("student-removed")).toEqual([["student-1"]]);
  });

  it("moves a seated student to an empty seat on long press release", async () => {
    vi.useFakeTimers();
    const wrapper = mountEditableMap();
    const sourceSeat = wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]');
    const targetSeat = wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-2"]');
    mockSeatFromPoint(targetSeat.element);

    await dispatchPointerEvent(sourceSeat.element, "pointerdown", {
      pointerType: "touch",
      pointerId: 1,
      clientX: 8,
      clientY: 8,
    });
    vi.advanceTimersByTime(451);
    await dispatchPointerEvent(sourceSeat.element, "pointerup", {
      pointerType: "touch",
      pointerId: 1,
      clientX: 56,
      clientY: 8,
    });
    await sourceSeat.trigger("click");

    expect(wrapper.emitted("student-dropped")).toEqual([["student-1", "seat-2"]]);
    expect(wrapper.emitted("student-removed")).toBeUndefined();
  });

  it("swaps two seated students on long press release over an occupied seat", async () => {
    vi.useFakeTimers();
    const wrapper = mountEditableMap([
      { student_id: "student-1", seat_id: "seat-1" },
      { student_id: "student-2", seat_id: "seat-2" },
    ]);
    const sourceSeat = wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]');
    const targetSeat = wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-2"]');
    mockSeatFromPoint(targetSeat.element);

    await dispatchPointerEvent(sourceSeat.element, "pointerdown", {
      pointerType: "touch",
      pointerId: 1,
      clientX: 8,
      clientY: 8,
    });
    vi.advanceTimersByTime(451);
    await dispatchPointerEvent(sourceSeat.element, "pointerup", {
      pointerType: "touch",
      pointerId: 1,
      clientX: 56,
      clientY: 8,
    });
    await sourceSeat.trigger("click");

    expect(wrapper.emitted("swap-requested")).toEqual([["student-1", "student-2"]]);
    expect(wrapper.emitted("student-removed")).toBeUndefined();
  });

  it("zooms on pinch without firing the follow-up short-press removal", async () => {
    const wrapper = mountEditableMap();
    const map = wrapper.get('[data-test="phone-classroom-seat-map"]');
    const sourceSeat = wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]');

    await dispatchTouchEvent(map.element, "touchstart", 100);
    await dispatchTouchEvent(map.element, "touchmove", 125);
    await dispatchTouchEvent(map.element, "touchend", 125, 1);
    await sourceSeat.trigger("click");

    expect(wrapper.get('[data-test="phone-fixed-seat-map-zoom-percent"]').text()).toBe("125%");
    expect(wrapper.emitted("student-removed")).toBeUndefined();
  });

  it("zooms on pinch without selecting a fixed-seat target", async () => {
    const wrapper = mount(PlannerPhoneClassroomSeatMap, {
      props: {
        template,
        studentsById,
        seatAssignments: [],
      },
    });
    const map = wrapper.get('[data-test="phone-classroom-seat-map"]');
    const targetSeat = wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]');

    await dispatchTouchEvent(map.element, "touchstart", 100);
    await dispatchTouchEvent(map.element, "touchmove", 125);
    await dispatchTouchEvent(map.element, "touchend", 125, 1);
    await targetSeat.trigger("click");

    expect(wrapper.get('[data-test="phone-fixed-seat-map-zoom-percent"]').text()).toBe("125%");
    expect(wrapper.emitted("seat-selected")).toBeUndefined();
  });
});
