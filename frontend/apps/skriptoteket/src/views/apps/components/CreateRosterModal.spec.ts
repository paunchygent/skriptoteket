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

  function createImportFile(name = "sa24d_klasslista.excel.xls"): File {
    return new File(["ignored"], name, {
      type: "application/vnd.ms-excel",
    });
  }

  function buildImportPreview(
    overrides: Partial<{
      file_name: string;
      suggested_class_name: string;
      parsed_students: Array<{ full_name: string; row_number: number }>;
      ambiguous_rows: Array<{ raw_text: string; row_number: number; reason: string }>;
    }> = {},
  ) {
    return {
      file_name: "sa24d_klasslista.excel.xls",
      suggested_class_name: "SA24D",
      parsed_students: [
        { full_name: "Kerstin Aitman", row_number: 1 },
        { full_name: "Edith Winlund Strandler", row_number: 2 },
      ],
      ambiguous_rows: [],
      ...overrides,
    };
  }

  async function flushPromises(): Promise<void> {
    for (let attempt = 0; attempt < 5; attempt += 1) {
      await Promise.resolve();
      await nextTick();
    }
  }

  async function uploadImportFile(wrapper: ReturnType<typeof mount>): Promise<void> {
    const input = wrapper.get("input[type='file']");
    const file = createImportFile();
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [file],
    });
    await input.trigger("change");
    await flushPromises();
  }

  async function dropImportFile(wrapper: ReturnType<typeof mount>, file = createImportFile()): Promise<void> {
    const dropzone = wrapper.get("[data-test='roster-modal-import-dropzone']");
    const dataTransfer = { files: [file], types: ["Files"], dropEffect: "copy" };
    await dropzone.trigger("dragover", { dataTransfer });
    await dropzone.trigger("drop", { dataTransfer });
    await flushPromises();
  }

  it("imports a parsed class list directly into the create modal before save", async () => {
    clientMocks.apiPost
      .mockResolvedValueOnce(
        buildImportPreview({
          ambiguous_rows: [{ raw_text: "Osäker Rad", row_number: 3, reason: "ambiguous" }],
        }),
      )
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

  it("imports a dropped file through the same preview flow", async () => {
    clientMocks.apiPost.mockResolvedValueOnce(buildImportPreview());

    const wrapper = mount(CreateRosterModal);

    await dropImportFile(wrapper);

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/rosters/import-preview",
      expect.any(FormData),
    );
    expect((wrapper.get("input[type='text']").element as HTMLInputElement).value).toBe("SA24D");
    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe(
      "Kerstin Aitman\nEdith Winlund Strandler",
    );
    expect(wrapper.get("[data-test='roster-import-summary']").text()).toContain(
      "sa24d_klasslista.excel.xls",
    );
  });

  it("supports an injected public import-preview path without hardcoding the owner route", async () => {
    clientMocks.apiPost.mockResolvedValueOnce(buildImportPreview());

    const wrapper = mount(CreateRosterModal, {
      props: {
        importPreviewApiPath:
          "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
      },
    });

    await dropImportFile(wrapper);

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
      expect.any(FormData),
    );
  });

  it("shows drag-active styling only while a file is over the drop zone", async () => {
    const wrapper = mount(CreateRosterModal);
    const dropzone = wrapper.get("[data-test='roster-modal-import-dropzone']");

    expect(dropzone.classes()).not.toContain("border-action");

    await dropzone.trigger("dragover", {
      dataTransfer: { files: [], types: ["Files"], dropEffect: "copy" },
    });
    expect(dropzone.classes()).toContain("border-action");

    await dropzone.trigger("dragleave", { relatedTarget: null });
    expect(dropzone.classes()).not.toContain("border-action");
  });

  it("matches edit-mode student ids by name instead of reusing ids by row position", async () => {
    const randomUuidSpy = vi
      .spyOn(globalThis.crypto, "randomUUID")
      .mockReturnValueOnce("11111111-1111-4111-8111-111111111111")
      .mockReturnValueOnce("22222222-2222-4222-8222-222222222222");
    clientMocks.apiPost.mockResolvedValueOnce(
      buildImportPreview({
        parsed_students: [
          { full_name: "Nytt Namn", row_number: 1 },
          { full_name: "Bea Befintlig", row_number: 2 },
          { full_name: "Annat Namn", row_number: 3 },
        ],
      }),
    );
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

    const saveButton = wrapper.findAll("button").find((button) => button.text() === "Spara");
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

    await wrapper.get("button.planner-btn-danger").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain(
      "Kunde inte radera klasslistan just nu.",
    );
    expect(wrapper.emitted("deleted")).toBeUndefined();
  });

  it("uses compact edit-mode action labels", () => {
    const wrapper = mount(CreateRosterModal, {
      props: {
        roster: {
          id: "roster-1",
          name: "SA24D",
          students: [{ id: "s1", display_name: "Ada" }],
        },
      },
    });

    const deleteButton = wrapper.get("button.planner-btn-danger");

    expect(deleteButton.text()).toBe("Radera");
    expect(deleteButton.find("svg").exists()).toBe(true);
    expect(wrapper.findAll("button").some((button) => button.text() === "Spara")).toBe(true);
    expect(wrapper.text()).not.toContain("Spara ändringar");
    expect(wrapper.text()).not.toContain("Radera klasslista");
  });

  it("uses injected save and delete handlers when provided", async () => {
    const saveRoster = vi.fn().mockResolvedValue({
      id: "guest-roster-1",
      name: "SA24D",
      students: [{ id: "student-1", display_name: "Ada" }],
    });
    const deleteRoster = vi.fn().mockResolvedValue(undefined);

    const createWrapper = mount(CreateRosterModal, {
      props: {
        saveRoster,
      },
    });

    await createWrapper.get("input[type='text']").setValue("SA24D");
    await createWrapper.get("textarea").setValue("Ada");
    const saveButton = createWrapper.findAll("button").find((button) => button.text() === "Skapa klasslista");
    if (!saveButton) {
      throw new Error("Expected the create save button to be rendered.");
    }
    await saveButton.trigger("click");
    await flushPromises();

    expect(saveRoster).toHaveBeenCalledWith({
      existingRoster: null,
      name: "SA24D",
      students: [expect.objectContaining({ display_name: "Ada" })],
    });
    expect(clientMocks.apiPost).not.toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/rosters",
      expect.anything(),
    );

    const editWrapper = mount(CreateRosterModal, {
      props: {
        roster: {
          id: "guest-roster-1",
          name: "SA24D",
          students: [{ id: "student-1", display_name: "Ada" }],
        },
        deleteRoster,
      },
    });

    await editWrapper.get("button.planner-btn-danger").trigger("click");
    await flushPromises();

    expect(deleteRoster).toHaveBeenCalledWith("guest-roster-1");
    expect(clientMocks.apiDelete).not.toHaveBeenCalled();
  });
});
