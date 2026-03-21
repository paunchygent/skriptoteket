import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import CreateRosterModal from "./CreateRosterModal.vue";

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

describe("CreateRosterModal", () => {
  beforeEach(() => {
    clientMocks.apiDelete.mockReset();
    clientMocks.apiPost.mockReset();
    clientMocks.apiPut.mockReset();
  });

  it("shows the backend message when roster delete is blocked by an active draft", async () => {
    clientMocks.apiDelete.mockRejectedValueOnce(
      new ApiError({
        code: "CONFLICT",
        message: "Du kan inte radera klasslistan eftersom ett aktivt utkast fortfarande använder den.",
        status: 409,
      }),
    );

    const wrapper = mount(CreateRosterModal, {
      props: {
        roster: {
          id: "roster-1",
          name: "SA24D",
          students: [{ id: "s1", display_name: "Ada" }],
        },
      },
    });

    await wrapper.get("button.btn-ghost.border-burgundy\\/40").trigger("click");
    await Promise.resolve();

    expect(wrapper.text()).toContain(
      "Du kan inte radera klasslistan eftersom ett aktivt utkast fortfarande använder den.",
    );
    expect(wrapper.emitted("deleted")).toBeUndefined();
  });
});
