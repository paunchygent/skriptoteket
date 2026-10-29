import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import CreateRoomTemplateModal from "./CreateRoomTemplateModal.vue";

function mockCellRect(element: Element): void {
  Object.defineProperty(element, "getBoundingClientRect", {
    configurable: true,
    value: () => ({
      left: 0,
      top: 0,
      right: 96,
      bottom: 96,
      width: 96,
      height: 96,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    }),
  });
}

class ResizeObserverMock {
  observe(): void {}
  disconnect(): void {}
}

function setHoverCapableViewport(): void {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn().mockReturnValue({
      matches: false,
      media: "(hover: none), (pointer: coarse)",
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

const clientMocks = vi.hoisted(() => ({
  apiDelete: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}));

vi.mock("../../../api/client", async () => {
  const actual = await vi.importActual<typeof import("../../../api/client")>("../../../api/client");
  return {
    ...actual,
    apiDelete: clientMocks.apiDelete,
    apiPost: clientMocks.apiPost,
    apiPut: clientMocks.apiPut,
  };
});

describe("CreateRoomTemplateModal", () => {
  const editTemplate = {
    id: "template-1",
    name: "Sal 101",
    grid_cols: 14,
    grid_rows: 9,
    seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
    fixtures: [],
  };
  const templateDeleteConfirmation = {
    eyebrow: "Ta bort klassrum",
    title: "Är du säker?",
    message:
      "Klassrummet Sal 101 tas bort från översikten. Utkast kopplade till klassrummet tas också bort.",
    confirmLabel: "Ta bort klassrum",
  };

  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    setHoverCapableViewport();
    clientMocks.apiDelete.mockReset();
    clientMocks.apiPost.mockReset();
    clientMocks.apiPut.mockReset();
  });

  function confirmationDialog(wrapper: ReturnType<typeof mount>) {
    return wrapper.get('[aria-labelledby="planner-confirmation-title"]');
  }

  async function clickCancelInConfirmation(wrapper: ReturnType<typeof mount>): Promise<void> {
    const cancelButton = confirmationDialog(wrapper)
      .findAll("button")
      .find((button) => button.text() === "Avbryt");
    if (!cancelButton) {
      throw new Error("Expected the confirmation cancel button to be rendered.");
    }
    await cancelButton.trigger("click");
  }

  async function confirmDeletion(wrapper: ReturnType<typeof mount>): Promise<void> {
    await confirmationDialog(wrapper).get('[data-test="confirm-dialog-confirm"]').trigger("click");
    await flushPromises();
  }

  it("exposes a modal dialog named by its visible title", () => {
    const wrapper = mount(CreateRoomTemplateModal);
    const dialog = wrapper.get('[role="dialog"]');
    expect(dialog.attributes("aria-modal")).toBe("true");
    const titleId = dialog.attributes("aria-labelledby");
    expect(titleId).toBeTruthy();
    const heading = dialog.get("h2");
    expect(heading.attributes("id")).toBe(titleId);
    expect(heading.text()).toBe("Nytt klassrum");
    expect(heading.isVisible()).toBe(true);
    wrapper.unmount();
  });

  it("lets wall objects share the edge with seats without consuming floor space", async () => {
    clientMocks.apiPost.mockResolvedValueOnce({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [{ id: "door-1", type: "door", x: 0, y: 0, width: 96, height: 96, label: null }],
    });

    const wrapper = mount(CreateRoomTemplateModal);

    await wrapper.get('input[type="text"]').setValue("Sal 101");

    const gridButtons = wrapper.findAll('.relative.grid.gap-1 button[type="button"]');
    await gridButtons[0]?.trigger("click");
    await wrapper.get("button").trigger("focus");

    const doorButton = wrapper.findAll("button").find((button) => button.text() === "Dörr");
    expect(doorButton).toBeDefined();
    await doorButton!.trigger("click");
    await gridButtons[0]?.trigger("click");
    await wrapper.get("button.btn-primary").trigger("click");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/templates",
      expect.objectContaining({
        name: "Sal 101",
        grid_cols: 14,
        grid_rows: 9,
        seats: [expect.objectContaining({ x: 0, y: 0 })],
        fixtures: [
          expect.objectContaining({
            type: "door",
            x: 0,
            y: 0,
            width: 96,
            height: 96,
            label: null,
          }),
        ],
      }),
    );
  });

  it("shows a ghost preview before placing a fixture", async () => {
    const wrapper = mount(CreateRoomTemplateModal);

    const whiteboardButton = wrapper.findAll("button").find((button) => button.text() === "Whiteboard");
    expect(whiteboardButton).toBeDefined();
    await whiteboardButton!.trigger("click");

    const gridButtons = wrapper.findAll('.relative.grid.gap-1 button[type="button"]');
    await gridButtons[57]?.trigger("mousemove", {
      clientX: 10,
      clientY: 10,
    });

    expect(wrapper.html()).toContain("border-dashed");
  });

  it("renders seat placements as circular markers in the builder preview", async () => {
    const wrapper = mount(CreateRoomTemplateModal);

    const gridButtons = wrapper.findAll('.relative.grid.gap-1 button[type="button"]');
    await gridButtons[0]?.trigger("click");

    const circularSeat = wrapper.findComponent({ name: "RoomSeatToken" });
    expect(circularSeat.exists()).toBe(true);
    expect(wrapper.html()).toContain("rounded-full");
  });

  it("snaps wall objects to the nearest wall based on the pointer position", async () => {
    clientMocks.apiPost.mockResolvedValueOnce({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [{ id: "seat-1", x: 96, y: 96, zone: null }],
      fixtures: [{ id: "whiteboard-1", type: "whiteboard", x: 0, y: 0, width: 288, height: 96, label: "Whiteboard" }],
    });

    const wrapper = mount(CreateRoomTemplateModal);
    await wrapper.get('input[type="text"]').setValue("Sal 101");

    const gridButtons = wrapper.findAll('.relative.grid.gap-1 button[type="button"]');
    await gridButtons[15]?.trigger("click", { clientX: 26, clientY: 26 });

    const whiteboardButton = wrapper.findAll("button").find((button) => button.text() === "Whiteboard");
    expect(whiteboardButton).toBeDefined();
    await whiteboardButton!.trigger("click");
    const topBandButton = gridButtons[1];
    expect(topBandButton).toBeDefined();
    mockCellRect(topBandButton!.element);
    await topBandButton!.trigger("click", { clientX: 48, clientY: 4 });
    await wrapper.get("button.btn-primary").trigger("click");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/templates",
      expect.objectContaining({
        fixtures: [expect.objectContaining({ type: "whiteboard", y: 0, width: 288, height: 96 })],
      }),
    );
  });

  it("keeps a window on the right wall when the pointer is tied in the top-right corner", async () => {
    clientMocks.apiPost.mockResolvedValueOnce({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [{ id: "window-1", type: "window", x: 1248, y: 0, width: 96, height: 192, label: null }],
    });

    const wrapper = mount(CreateRoomTemplateModal);
    await wrapper.get('input[type="text"]').setValue("Sal 101");

    const gridButtons = wrapper.findAll('.relative.grid.gap-1 button[type="button"]');
    await gridButtons[14]?.trigger("click");

    const windowButton = wrapper.findAll("button").find((button) => button.text() === "Fönster");
    expect(windowButton).toBeDefined();
    await windowButton!.trigger("click");

    const topRightButton = gridButtons[13];
    expect(topRightButton).toBeDefined();
    mockCellRect(topRightButton!.element);

    await topRightButton!.trigger("click", {
      clientX: 84,
      clientY: 12,
    });
    await wrapper.get("button.btn-primary").trigger("click");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/templates",
      expect.objectContaining({
        fixtures: [
          expect.objectContaining({
            type: "window",
            x: 1248,
            y: 0,
            width: 96,
            height: 192,
          }),
        ],
      }),
    );
  });

  it("resizes the classroom and saves the updated grid dimensions", async () => {
    clientMocks.apiPost.mockResolvedValueOnce({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 15,
      grid_rows: 10,
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [],
    });

    const wrapper = mount(CreateRoomTemplateModal);
    await wrapper.get('input[type="text"]').setValue("Sal 101");

    const gridButtons = wrapper.findAll('.relative.grid.gap-1 button[type="button"]');
    await gridButtons[0]?.trigger("click");

    const plusButtons = wrapper.findAll("button").filter((button) => button.text() === "+");
    await plusButtons[0]?.trigger("click");
    await plusButtons[1]?.trigger("click");
    await wrapper.get("button.btn-primary").trigger("click");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/templates",
      expect.objectContaining({
        grid_cols: 15,
        grid_rows: 10,
      }),
    );
  });

  it("uses a sticky left editor rail and removes the redundant modal eyebrow", () => {
    const wrapper = mount(CreateRoomTemplateModal, {
      props: {
        template: {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 14,
          grid_rows: 9,
          seats: [],
          fixtures: [],
        },
      },
    });

    expect(wrapper.get('[data-test="room-template-editor-sidebar"]').classes()).toEqual(
      expect.arrayContaining(["xl:sticky", "xl:top-4", "xl:self-start"]),
    );
    expect(wrapper.find('p.text-\\[11px\\]').exists()).toBe(false);
    expect(wrapper.text()).toContain("Redigera klassrum");
  });

  it("updates an existing classroom through the edit save contract", async () => {
    clientMocks.apiPut.mockResolvedValueOnce({
      id: "template-1",
      name: "Sal 101B",
      grid_cols: 15,
      grid_rows: 10,
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [{ id: "bench-1", type: "bench", x: 96, y: 96, width: 96, height: 96, label: null }],
    });

    const wrapper = mount(CreateRoomTemplateModal, {
      props: {
        template: {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 14,
          grid_rows: 9,
          seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
          fixtures: [{ id: "bench-1", type: "bench", x: 96, y: 96, width: 96, height: 96, label: null }],
        },
      },
    });

    await wrapper.get('input[type="text"]').setValue("Sal 101B");

    const plusButtons = wrapper.findAll("button").filter((button) => button.text() === "+");
    await plusButtons[0]?.trigger("click");
    await plusButtons[1]?.trigger("click");
    await wrapper.get("button.btn-primary").trigger("click");

    expect(clientMocks.apiPut).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/templates/template-1",
      expect.objectContaining({
        name: "Sal 101B",
        grid_cols: 15,
        grid_rows: 10,
        seats: [expect.objectContaining({ x: 0, y: 0 })],
        fixtures: [
          expect.objectContaining({
            id: "bench-1",
            type: "bench",
            x: 96,
            y: 96,
            width: 96,
            height: 96,
            label: null,
          }),
        ],
      }),
    );
    expect(wrapper.emitted("saved")).toEqual([
      [
        expect.objectContaining({
          id: "template-1",
          name: "Sal 101B",
          grid_cols: 15,
          grid_rows: 10,
        }),
      ],
    ]);
  });

  it("uses injected save and delete handlers when provided", async () => {
    const saveTemplate = vi.fn().mockResolvedValue({
      id: "guest-template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [],
      fixtures: [],
    });
    const deleteTemplate = vi.fn().mockResolvedValue(undefined);
    const createWrapper = mount(CreateRoomTemplateModal, {
      props: {
        saveTemplate,
      },
    });

    await createWrapper.get('input[type="text"]').setValue("Sal 101");
    await createWrapper.get("button.btn-primary").trigger("click");

    expect(saveTemplate).toHaveBeenCalledWith(
      expect.objectContaining({
        existingTemplate: null,
        name: "Sal 101",
      }),
    );
    expect(clientMocks.apiPost).not.toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/templates",
      expect.anything(),
    );

    const editWrapper = mount(CreateRoomTemplateModal, {
      props: {
        template: {
          id: "guest-template-1",
          name: "Sal 101",
          grid_cols: 14,
          grid_rows: 9,
          seats: [],
          fixtures: [],
        },
        deleteConfirmation: {
          ...templateDeleteConfirmation,
          message:
            "Klassrummet Sal 101 tas bort från den publika arbetsytan i den här webbläsaren.",
        },
        deleteTemplate,
      },
    });

    await editWrapper.find('[data-test="room-template-delete-button"]').trigger("click");
    await flushPromises();
    await confirmDeletion(editWrapper);

    expect(deleteTemplate).toHaveBeenCalledWith("guest-template-1");
    expect(clientMocks.apiDelete).not.toHaveBeenCalled();
  });

  it("clears seats and fixtures without changing the current grid size", async () => {
    clientMocks.apiPost.mockResolvedValueOnce({
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [],
      fixtures: [],
    });

    const wrapper = mount(CreateRoomTemplateModal);
    await wrapper.get('input[type="text"]').setValue("Sal 101");

    const gridButtons = wrapper.findAll('.relative.grid.gap-1 button[type="button"]');
    await gridButtons[0]?.trigger("click");

    const benchButton = wrapper.findAll("button").find((button) => button.text() === "Bänk");
    expect(benchButton).toBeDefined();
    await benchButton!.trigger("click");
    await gridButtons[15]?.trigger("click");

    const clearButton = wrapper.findAll("button").find((button) => button.text() === "Rensa");
    expect(clearButton).toBeDefined();
    await clearButton!.trigger("click");
    await wrapper.get("button.btn-primary").trigger("click");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/templates",
      expect.objectContaining({
        grid_cols: 14,
        grid_rows: 9,
        seats: [],
        fixtures: [],
      }),
    );
  });

  describe("delete confirmation", () => {
    it("opens the shared confirmation and sends no request before confirm", async () => {
      const wrapper = mount(CreateRoomTemplateModal, {
        props: { template: editTemplate, deleteConfirmation: templateDeleteConfirmation },
      });

      await wrapper.find('[data-test="room-template-delete-button"]').trigger("click");
      await flushPromises();

      const dialog = confirmationDialog(wrapper);
      expect(dialog.text()).toContain("Ta bort klassrum");
      expect(dialog.text()).toContain("Är du säker?");
      expect(dialog.text()).toContain(templateDeleteConfirmation.message);
      expect(dialog.get('[data-test="confirm-dialog-confirm"]').text()).toBe("Ta bort klassrum");
      expect(clientMocks.apiDelete).not.toHaveBeenCalled();
      expect(wrapper.emitted("deleted")).toBeUndefined();
      wrapper.unmount();
    });

    it("deletes the classroom only from the confirm button", async () => {
      clientMocks.apiDelete.mockResolvedValueOnce(undefined);
      const wrapper = mount(CreateRoomTemplateModal, {
        props: { template: editTemplate, deleteConfirmation: templateDeleteConfirmation },
      });

      await wrapper.find('[data-test="room-template-delete-button"]').trigger("click");
      await flushPromises();
      expect(clientMocks.apiDelete).not.toHaveBeenCalled();

      await confirmDeletion(wrapper);

      expect(clientMocks.apiDelete).toHaveBeenCalledWith(
        "/api/v1/apps/classroom.group-seating-studio/templates/template-1",
      );
      expect(wrapper.emitted("deleted")).toEqual([["template-1"]]);
      wrapper.unmount();
    });

    it("cancels without deleting or closing the edit dialog", async () => {
      const wrapper = mount(CreateRoomTemplateModal, {
        props: { template: editTemplate, deleteConfirmation: templateDeleteConfirmation },
      });

      await wrapper.find('[data-test="room-template-delete-button"]').trigger("click");
      await flushPromises();
      await clickCancelInConfirmation(wrapper);
      await flushPromises();

      expect(clientMocks.apiDelete).not.toHaveBeenCalled();
      expect(wrapper.emitted("deleted")).toBeUndefined();
      expect(wrapper.emitted("close")).toBeUndefined();
      expect(wrapper.find('[aria-labelledby="planner-confirmation-title"]').exists()).toBe(false);
      expect(wrapper.find("[data-test='room-template-modal-panel']").exists()).toBe(true);
      expect(wrapper.get("#room-template-modal-title").text()).toBe("Redigera klassrum");
      expect(wrapper.get('input[type="text"]').element).toHaveProperty("value", "Sal 101");
      wrapper.unmount();
    });

    it("shows a failed delete in the confirmation and keeps it open", async () => {
      clientMocks.apiDelete.mockRejectedValueOnce(
        new ApiError({
          code: "INTERNAL_ERROR",
          message: "Kunde inte radera klassrummet just nu.",
          status: 500,
        }),
      );
      const wrapper = mount(CreateRoomTemplateModal, {
        props: { template: editTemplate, deleteConfirmation: templateDeleteConfirmation },
      });

      await wrapper.find('[data-test="room-template-delete-button"]').trigger("click");
      await flushPromises();
      await confirmDeletion(wrapper);

      const dialog = confirmationDialog(wrapper);
      expect(dialog.text()).toContain(
        "Det gick inte att ta bort klassrummet. Försök igen eller avbryt.",
      );
      expect(dialog.text()).not.toContain("Kunde inte radera klassrummet just nu.");
      expect(wrapper.emitted("deleted")).toBeUndefined();
      wrapper.unmount();
    });

    it("keeps the guest delete handler behind the same confirmation", async () => {
      const deleteTemplate = vi.fn().mockResolvedValue(undefined);
      const wrapper = mount(CreateRoomTemplateModal, {
        props: {
          template: editTemplate,
          deleteConfirmation: templateDeleteConfirmation,
          deleteTemplate,
        },
      });

      await wrapper.find('[data-test="room-template-delete-button"]').trigger("click");
      await flushPromises();
      expect(deleteTemplate).not.toHaveBeenCalled();

      await confirmDeletion(wrapper);

      expect(deleteTemplate).toHaveBeenCalledWith("template-1");
      expect(clientMocks.apiDelete).not.toHaveBeenCalled();
      expect(wrapper.emitted("deleted")).toEqual([["template-1"]]);
      wrapper.unmount();
    });
  });

  it("keeps delete, cancel and save in one non-wrapping footer row", () => {
    const wrapper = mount(CreateRoomTemplateModal, {
      props: {
        template: {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 14,
          grid_rows: 9,
          seats: [],
          fixtures: [],
        },
      },
    });

    const footer = wrapper.get(".room-template-modal-footer");
    const actions = footer.get(".room-template-modal-footer-actions");
    for (const container of [footer, actions]) {
      expect(container.classes()).toContain("flex-nowrap");
      expect(container.classes()).not.toContain("flex-wrap");
      expect(container.classes()).not.toContain("flex-col");
    }

    const deleteButton = footer.get("[data-test='room-template-delete-button']");
    expect(deleteButton.text()).toBe("");
    expect(deleteButton.attributes("aria-label")).toBe("Radera klassrum");
    expect(actions.get("[data-test='room-template-cancel-button']").classes()).toContain("whitespace-nowrap");
    expect(actions.get("[data-test='room-template-save-button']").classes()).toContain("whitespace-nowrap");
    wrapper.unmount();
  });
});
