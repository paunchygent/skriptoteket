import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
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

  async function flushPromises(): Promise<void> {
    for (let attempt = 0; attempt < 5; attempt += 1) {
      await Promise.resolve();
      await nextTick();
    }
  }

  async function uploadImportFile(wrapper: ReturnType<typeof mount>): Promise<void> {
    const input = wrapper.get("input[type='file']");
    const file = new File(["ignored"], "sa24d_klasslista.excel.xls", {
      type: "application/vnd.ms-excel",
    });
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [file],
    });
    await input.trigger("change");
    await flushPromises();
  }

  it("imports a parsed class list directly into the create modal before save", async () => {
    clientMocks.apiPost
      .mockResolvedValueOnce({
        file_name: "sa24d_klasslista.excel.xls",
        suggested_class_name: "SA24D",
        parsed_students: [
          { full_name: "Kerstin Aitman", row_number: 1 },
          { full_name: "Edith Winlund Strandler", row_number: 2 },
        ],
        ambiguous_rows: [{ raw_text: "Osäker Rad", row_number: 3, reason: "ambiguous" }],
      })
      .mockResolvedValueOnce({
        id: "roster-1",
        name: "SA24D",
        students: [
          { id: "student-1", display_name: "Kerstin Aitman" },
          { id: "student-2", display_name: "Edith Winlund Strandler" },
          { id: "student-3", display_name: "Osäker Rad" },
        ],
      });

    const wrapper = mount(CreateRosterModal);

    expect(wrapper.text()).toContain("Importera från fil");
    expect(wrapper.text()).toContain("Skola24");

    await uploadImportFile(wrapper);

    const inputs = wrapper.findAll("input[type='text']");
    expect((inputs[0]?.element as HTMLInputElement | undefined)?.value).toBe("SA24D");
    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe(
      "Kerstin Aitman\nEdith Winlund Strandler",
    );
    expect(wrapper.get("[data-test='roster-import-summary']").text()).toContain(
      "sa24d_klasslista.excel.xls",
    );

    await wrapper.get("[data-test='roster-import-ambiguous'] button").trigger("click");
    await flushPromises();
    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe(
      "Kerstin Aitman\nEdith Winlund Strandler\nOsäker Rad",
    );

    const saveButton = wrapper.findAll("button").find((button) => button.text() === "Skapa klasslista");
    if (!saveButton) {
      throw new Error("Expected the save button to be rendered.");
    }

    await saveButton.trigger("click");
    await flushPromises();

    expect(clientMocks.apiPost).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/classroom.group-seating-studio/rosters",
      {
        name: "SA24D",
        students: [
          expect.objectContaining({ display_name: "Kerstin Aitman" }),
          expect.objectContaining({ display_name: "Edith Winlund Strandler" }),
          expect.objectContaining({ display_name: "Osäker Rad" }),
        ],
      },
    );
    expect(wrapper.emitted("saved")).toHaveLength(1);
  });

  it("matches edit-mode student ids by name instead of reusing ids by row position", async () => {
    const randomUuidSpy = vi
      .spyOn(globalThis.crypto, "randomUUID")
      .mockReturnValueOnce("11111111-1111-4111-8111-111111111111")
      .mockReturnValueOnce("22222222-2222-4222-8222-222222222222");
    clientMocks.apiPost.mockResolvedValueOnce({
      file_name: "sa24d_klasslista.excel.xls",
      suggested_class_name: "SA24D",
      parsed_students: [
        { full_name: "Nytt Namn", row_number: 1 },
        { full_name: "Bea Befintlig", row_number: 2 },
        { full_name: "Annat Namn", row_number: 3 },
      ],
      ambiguous_rows: [],
    });
    clientMocks.apiPut.mockResolvedValueOnce({
      id: "roster-1",
      name: "SA24D",
      students: [],
    });

    const wrapper = mount(CreateRosterModal, {
      props: {
        roster: {
          id: "roster-1",
          name: "Klass 1",
          students: [
            { id: "student-a", display_name: "Ada Befintlig" },
            { id: "student-b", display_name: "Bea Befintlig" },
            { id: "student-c", display_name: "Cia Befintlig" },
          ],
        },
      },
    });

    await uploadImportFile(wrapper);

    const saveButton = wrapper.findAll("button").find((button) => button.text() === "Spara ändringar");
    if (!saveButton) {
      throw new Error("Expected the edit save button to be rendered.");
    }

    await saveButton.trigger("click");
    await flushPromises();

    expect(clientMocks.apiPut).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1",
      {
        name: "SA24D",
        students: [
          { id: "11111111-1111-4111-8111-111111111111", display_name: "Nytt Namn" },
          { id: "student-b", display_name: "Bea Befintlig" },
          { id: "22222222-2222-4222-8222-222222222222", display_name: "Annat Namn" },
        ],
      },
    );

    randomUuidSpy.mockRestore();
  });

  it("shows the backend message when roster delete fails", async () => {
    clientMocks.apiDelete.mockRejectedValueOnce(
      new ApiError({
        code: "INTERNAL_ERROR",
        message: "Kunde inte radera klasslistan just nu.",
        status: 500,
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
    await flushPromises();

    expect(wrapper.text()).toContain(
      "Kunde inte radera klasslistan just nu.",
    );
    expect(wrapper.emitted("deleted")).toBeUndefined();
  });
});
