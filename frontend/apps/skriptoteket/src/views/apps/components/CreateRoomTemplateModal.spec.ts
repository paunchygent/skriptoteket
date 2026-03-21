import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import CreateRoomTemplateModal from "./CreateRoomTemplateModal.vue";

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
  beforeEach(() => {
    clientMocks.apiDelete.mockReset();
    clientMocks.apiPost.mockReset();
    clientMocks.apiPut.mockReset();
  });

  it("shows the backend message when classroom delete is blocked by an active draft", async () => {
    clientMocks.apiDelete.mockRejectedValueOnce(
      new ApiError({
        code: "CONFLICT",
        message: "Du kan inte radera klassrummet eftersom ett aktivt utkast fortfarande använder det.",
        status: 409,
      }),
    );

    const wrapper = mount(CreateRoomTemplateModal, {
      props: {
        template: {
          id: "template-1",
          name: "Sal 101",
          seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
          fixtures: [],
        },
      },
    });

    await wrapper.get("button.btn-ghost.border-burgundy\\/40").trigger("click");
    await Promise.resolve();

    expect(wrapper.text()).toContain(
      "Du kan inte radera klassrummet eftersom ett aktivt utkast fortfarande använder det.",
    );
    expect(wrapper.emitted("deleted")).toBeUndefined();
  });
});
