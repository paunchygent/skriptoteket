/**
 * Phone room-template modal behavior tests.
 *
 * Relationships:
 * - covers the PR-0311 phone footer, required-name recovery, and touch no-hover contract
 * - complements the broader create/edit persistence tests for the modal shell
 */

import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CreateRoomTemplateModal from "./CreateRoomTemplateModal.vue";

class ResizeObserverMock {
  observe(): void {}
  disconnect(): void {}
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

function mountModal(): VueWrapper {
  const host = document.createElement("div");
  document.body.appendChild(host);
  return mount(CreateRoomTemplateModal, { attachTo: host });
}

describe("CreateRoomTemplateModal phone behavior", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    HTMLElement.prototype.scrollIntoView = vi.fn();
    clientMocks.apiDelete.mockReset();
    clientMocks.apiPost.mockReset();
    clientMocks.apiPut.mockReset();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.unstubAllGlobals();
  });

  it("renders compact edit footer actions on first render", () => {
    const wrapper = mount(CreateRoomTemplateModal, {
      props: {
        template: {
          id: "template-1",
          name: "G20",
          grid_cols: 14,
          grid_rows: 9,
          seats: [],
          fixtures: [],
        },
      },
    });

    const deleteButton = wrapper.get('[data-test="room-template-delete-button"]');
    const cancelButton = wrapper.get('[data-test="room-template-cancel-button"]');
    const saveButton = wrapper.get('[data-test="room-template-save-button"]');

    expect(deleteButton.text()).toBe("Radera");
    expect(cancelButton.text()).toBe("Avbryt");
    expect(saveButton.text()).toBe("Spara");
    expect(wrapper.text()).not.toContain("Radera klassrum");
    expect(wrapper.text()).not.toContain("Spara klassrum");
    expect(deleteButton.html()).toContain("lucide-trash-2");
    expect(cancelButton.html()).toContain("lucide-x");
    expect(saveButton.html()).toContain("lucide-save");
  });

  it("focuses the classroom name field when save is attempted without a name", async () => {
    const wrapper = mountModal();

    const saveButton = wrapper.get('[data-test="room-template-save-button"]');
    expect(saveButton.attributes("disabled")).toBeUndefined();

    await saveButton.trigger("click");

    expect(wrapper.text()).toContain("Ge klassrummet ett namn innan du sparar.");
    expect(wrapper.find(".system-message").exists()).toBe(false);
    expect(wrapper.get('[data-test="room-template-name-input"]').attributes("aria-invalid")).toBe("true");
    expect(document.activeElement).toBe(wrapper.get('[data-test="room-template-name-input"]').element);
    expect(clientMocks.apiPost).not.toHaveBeenCalled();
  });

  it("creates and removes a real seat from touch taps without leaving a ghost preview", async () => {
    const wrapper = mountModal();
    const firstCell = wrapper.find(".planner-grid-node-button");
    const builderViewport = wrapper.get('[data-test="room-builder-viewport"]');

    expect(builderViewport.findAll('[data-test="room-seat-token"]')).toHaveLength(0);

    await firstCell.trigger("pointerdown", { pointerType: "touch" });
    await firstCell.trigger("click", { clientX: 8, clientY: 8 });

    const placedSeats = builderViewport.findAll('[data-test="room-seat-token"]');
    expect(placedSeats).toHaveLength(1);
    expect(placedSeats[0]!.text()).toContain("plats-1");
    expect(wrapper.find('[data-test="room-builder-ghost-overlay"]').exists()).toBe(false);

    await firstCell.trigger("pointerdown", { pointerType: "touch" });
    await firstCell.trigger("click", { clientX: 8, clientY: 8 });

    expect(builderViewport.findAll('[data-test="room-seat-token"]')).toHaveLength(0);
    expect(wrapper.find('[data-test="room-builder-ghost-overlay"]').exists()).toBe(false);
  });
});
