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
  const editRoster = {
    id: "roster-1",
    name: "SA24D",
    students: [{ id: "s1", display_name: "Ada" }],
  };
  const rosterDeleteConfirmation = {
    eyebrow: "Ta bort klasslista",
    title: "Är du säker?",
    message:
      "Klasslistan SA24D tas bort från översikten. Utkast kopplade till klassen tas också bort.",
    confirmLabel: "Ta bort klasslista",
  };

  beforeEach(() => {
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

  it.each([
    { roster: null, title: "Ny klasslista" },
    { roster: { id: "roster-1", name: "SA24D", students: [] }, title: "Redigera klasslista" },
  ])("labels the modal with its visible title: $title", ({ roster, title }) => {
    const wrapper = mount(CreateRosterModal, { props: { roster } });
    const dialog = wrapper.get('[role="dialog"]');

    expect(dialog.attributes("aria-modal")).toBe("true");
    const titleId = dialog.attributes("aria-labelledby");
    expect(titleId).toBeTruthy();
    const heading = dialog.get("h2");
    expect(heading.attributes("id")).toBe(titleId);
    expect(heading.text()).toBe(title);
    expect(heading.isVisible()).toBe(true);
    wrapper.unmount();
  });

  it("closes from the named header icon without submitting or deleting", async () => {
    const wrapper = mount(CreateRosterModal);
    const closeButton = wrapper.get('[role="dialog"] button[aria-label="Stäng"]');
    expect(closeButton.attributes("type")).toBe("button");
    await closeButton.trigger("click");
    expect(wrapper.emitted("close")).toEqual([[]]);
    expect(clientMocks.apiPost).not.toHaveBeenCalled();
    expect(clientMocks.apiDelete).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("returns focus to import after dismissing its failed-upload announcement", async () => {
    clientMocks.apiPost.mockRejectedValueOnce(new Error("Upload failed"));
    const wrapper = mount(CreateRosterModal, { attachTo: document.body });
    try {
      await uploadImportFile(wrapper);
      const alert = wrapper.get('[role="alert"]');
      const dismissButton = alert.get('button[aria-label="Stäng"]');
      (dismissButton.element as HTMLButtonElement).focus();
      expect(document.activeElement).toBe(dismissButton.element);
      await dismissButton.trigger("click");
      await nextTick();
      expect(wrapper.find('[role="alert"]').exists()).toBe(false);
      expect(document.activeElement).toBe(wrapper.get('[data-test="roster-modal-import-trigger"]').element);
      expect(wrapper.emitted("close")).toBeUndefined();
    } finally {
      wrapper.unmount();
    }
  });

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

  describe("delete confirmation", () => {
    it("opens the shared confirmation and sends no request before confirm", async () => {
      const wrapper = mount(CreateRosterModal, {
        props: { roster: editRoster, deleteConfirmation: rosterDeleteConfirmation },
      });

      await wrapper.get("[data-test='roster-modal-delete']").trigger("click");
      await flushPromises();

      const dialog = confirmationDialog(wrapper);
      expect(dialog.text()).toContain("Ta bort klasslista");
      expect(dialog.text()).toContain("Är du säker?");
      expect(dialog.text()).toContain(rosterDeleteConfirmation.message);
      expect(dialog.get('[data-test="confirm-dialog-confirm"]').text()).toBe("Ta bort klasslista");
      expect(clientMocks.apiDelete).not.toHaveBeenCalled();
      expect(wrapper.emitted("deleted")).toBeUndefined();
      wrapper.unmount();
    });

    it("deletes the class list only from the confirm button", async () => {
      clientMocks.apiDelete.mockResolvedValueOnce(undefined);
      const wrapper = mount(CreateRosterModal, {
        props: { roster: editRoster, deleteConfirmation: rosterDeleteConfirmation },
      });

      await wrapper.get("[data-test='roster-modal-delete']").trigger("click");
      await flushPromises();
      expect(clientMocks.apiDelete).not.toHaveBeenCalled();

      await confirmDeletion(wrapper);

      expect(clientMocks.apiDelete).toHaveBeenCalledWith(
        "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1",
      );
      expect(wrapper.emitted("deleted")).toEqual([["roster-1"]]);
      wrapper.unmount();
    });

    it("cancels without deleting or closing the edit dialog", async () => {
      const wrapper = mount(CreateRosterModal, {
        props: { roster: editRoster, deleteConfirmation: rosterDeleteConfirmation },
      });

      await wrapper.get("[data-test='roster-modal-delete']").trigger("click");
      await flushPromises();
      await clickCancelInConfirmation(wrapper);
      await flushPromises();

      expect(clientMocks.apiDelete).not.toHaveBeenCalled();
      expect(wrapper.emitted("deleted")).toBeUndefined();
      expect(wrapper.emitted("close")).toBeUndefined();
      expect(wrapper.find('[aria-labelledby="planner-confirmation-title"]').exists()).toBe(false);
      expect(wrapper.find("[data-test='roster-modal-shell']").exists()).toBe(true);
      expect(wrapper.get("#roster-modal-title").text()).toBe("Redigera klasslista");
      expect(wrapper.get("#roster-name").element).toHaveProperty("value", "SA24D");
      wrapper.unmount();
    });

    it("shows a failed delete in the confirmation and keeps it open", async () => {
      clientMocks.apiDelete.mockRejectedValueOnce(
        new ApiError({
          code: "INTERNAL_ERROR",
          message: "Kunde inte radera klasslistan just nu.",
          status: 500,
        }),
      );
      const wrapper = mount(CreateRosterModal, {
        props: { roster: editRoster, deleteConfirmation: rosterDeleteConfirmation },
      });

      await wrapper.get("[data-test='roster-modal-delete']").trigger("click");
      await flushPromises();
      await confirmDeletion(wrapper);

      const dialog = confirmationDialog(wrapper);
      expect(dialog.text()).toContain(
        "Det gick inte att ta bort klasslistan. Försök igen eller avbryt.",
      );
      expect(dialog.text()).not.toContain("Kunde inte radera klasslistan just nu.");
      expect(wrapper.emitted("deleted")).toBeUndefined();
      wrapper.unmount();
    });

    it("keeps the guest delete handler behind the same confirmation", async () => {
      const deleteRoster = vi.fn().mockResolvedValue(undefined);
      const wrapper = mount(CreateRosterModal, {
        props: {
          roster: editRoster,
          deleteConfirmation: rosterDeleteConfirmation,
          deleteRoster,
        },
      });

      await wrapper.get("[data-test='roster-modal-delete']").trigger("click");
      await flushPromises();
      expect(deleteRoster).not.toHaveBeenCalled();

      await confirmDeletion(wrapper);

      expect(deleteRoster).toHaveBeenCalledWith("roster-1");
      expect(clientMocks.apiDelete).not.toHaveBeenCalled();
      expect(wrapper.emitted("deleted")).toEqual([["roster-1"]]);
      wrapper.unmount();
    });
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

    const deleteButton = wrapper.get("[data-test='roster-modal-delete']");

    expect(deleteButton.text()).toBe("");
    expect(deleteButton.attributes("aria-label")).toBe("Radera klasslista");
    expect(deleteButton.attributes("title")).toBe("Radera klasslista");
    expect(deleteButton.find("svg").exists()).toBe(true);
    expect(wrapper.findAll("button").some((button) => button.text() === "Spara")).toBe(true);
    expect(wrapper.text()).not.toContain("Spara ändringar");
    expect(wrapper.text()).not.toContain("Radera");
  });

  describe("footer geometry", () => {
    it.each([
      { mode: "create", roster: null, buttonCount: 2 },
      { mode: "edit", roster: editRoster, buttonCount: 3 },
    ])("keeps every $mode action in one non-wrapping row", ({ roster, buttonCount }) => {
      const wrapper = mount(CreateRosterModal, { props: { roster } });
      const footer = wrapper.get("[data-test='roster-modal-footer']");
      const actions = footer.get("[data-test='roster-modal-footer-actions']");

      for (const container of [footer, actions]) {
        const classes = container.classes();
        expect(classes).toContain("flex-nowrap");
        expect(classes).not.toContain("flex-wrap");
        expect(classes).not.toContain("flex-col");
        expect(classes.some((name) => name.startsWith("sm:flex") || name.startsWith("md:flex"))).toBe(false);
      }

      const cancel = actions.findAll("button").find((button) => button.text() === "Avbryt");
      const submit = actions.findAll("button").find((button) => button.text() !== "Avbryt");
      expect(cancel).toBeDefined();
      expect(submit).toBeDefined();
      expect(cancel!.classes()).toContain("whitespace-nowrap");
      expect(submit!.classes()).toContain("whitespace-nowrap");
      expect(footer.findAll("button")).toHaveLength(buttonCount);
      wrapper.unmount();
    });

    it("labels the create action on one row and offers no delete control", () => {
      const wrapper = mount(CreateRosterModal);
      const footer = wrapper.get("[data-test='roster-modal-footer']");

      expect(footer.text()).toContain("Skapa klasslista");
      expect(footer.find("[data-test='roster-modal-delete']").exists()).toBe(false);
      wrapper.unmount();
    });

    it("renders delete as a frameless 44px danger glyph beside the other actions", () => {
      const wrapper = mount(CreateRosterModal, { props: { roster: editRoster } });
      const footer = wrapper.get("[data-test='roster-modal-footer']");
      const deleteButton = footer.get("[data-test='roster-modal-delete']");

      expect(deleteButton.element.closest("[data-test='roster-modal-footer-actions']")).toBeNull();
      expect(deleteButton.classes()).toContain("w-[44px]");
      expect(deleteButton.classes()).toContain("h-[44px]");
      expect(deleteButton.text()).toBe("");
      expect(deleteButton.attributes("aria-label")).toBe("Radera klasslista");
      wrapper.unmount();
    });

    it("disables the delete glyph and confirm button while a delete is running", async () => {
      let resolveDelete: () => void = () => undefined;
      const deleteRoster = vi.fn(
        () => new Promise<void>((resolve) => {
          resolveDelete = resolve;
        }),
      );
      const wrapper = mount(CreateRosterModal, {
        props: {
          roster: editRoster,
          deleteConfirmation: rosterDeleteConfirmation,
          deleteRoster,
        },
      });
      const deleteButton = wrapper.get("[data-test='roster-modal-delete']");

      await deleteButton.trigger("click");
      await flushPromises();
      await confirmationDialog(wrapper).get('[data-test="confirm-dialog-confirm"]').trigger("click");
      await flushPromises();

      expect(confirmationDialog(wrapper).get('[data-test="confirm-dialog-confirm"]').attributes("disabled")).toBeDefined();
      expect(deleteButton.attributes("disabled")).toBeDefined();

      resolveDelete();
      await flushPromises();
      wrapper.unmount();
    });
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
        deleteConfirmation: {
          ...rosterDeleteConfirmation,
          message:
            "Klasslistan SA24D tas bort från den publika arbetsytan i den här webbläsaren.",
        },
        deleteRoster,
      },
    });

    await editWrapper.get("[data-test='roster-modal-delete']").trigger("click");
    await flushPromises();
    await confirmDeletion(editWrapper);

    expect(deleteRoster).toHaveBeenCalledWith("guest-roster-1");
    expect(clientMocks.apiDelete).not.toHaveBeenCalled();
  });
});
