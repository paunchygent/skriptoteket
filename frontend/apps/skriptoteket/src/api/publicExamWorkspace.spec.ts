/**
 * Public exam workspace transport for guests.
 *
 * Expected behavior:
 *   Every stateless guest route is called under the public Exam Converter
 *   namespace with the exact paths and payload shapes the backend contract
 *   defines: the whole document in JSON commands, multipart exports with the
 *   `document` field and one `asset:<id>` part per declared picture, and the
 *   checklist on the same multipart shape.
 */

import { describe, expect, it, vi } from "vitest";

import { buildParentDocument } from "../views/apps/exam-workspace/examWorkspaceParentDocument.specSupport";
import { buildFreeTextItem } from "../test/examWorkspaceFixtures";
import { publicApiFetchBlobResponse, publicApiGet, publicApiPost } from "./client";
import type { NativeExamDocument } from "./examWorkspace";
import {
  addPublicExamWorkspaceChild,
  changePublicExamWorkspaceItemType,
  createEmptyPublicExamWorkspacePart,
  createPublicExamWorkspaceBlank,
  createPublicExamWorkspaceParent,
  deletePublicExamWorkspaceChild,
  deletePublicExamWorkspaceParent,
  downloadPublicExamWorkspaceExport,
  getPublicExamCourseCatalog,
  getPublicExamWorkspaceExportChecklist,
  groupPublicExamWorkspaceItems,
  importPublicExamWorkspaceQti,
  movePublicExamWorkspaceItem,
  reorderPublicExamWorkspaceChildren,
  requestPublicExamWorkspaceAnswerMisspellings,
} from "./publicExamWorkspace";

vi.mock("./client", () => ({
  publicApiFetchBlobResponse: vi.fn(),
  publicApiGet: vi.fn(),
  publicApiPost: vi.fn(),
}));

const publicApiPostMock = vi.mocked(publicApiPost);
const publicApiGetMock = vi.mocked(publicApiGet);
const publicApiFetchBlobResponseMock = vi.mocked(publicApiFetchBlobResponse);

const WORKSPACE_ROOT =
  "/api/v1/public/apps/documents.conversion_hub/exam-converter/workspace";

/** Any current-schema document; the transport treats it as opaque payload. */
function document(): NativeExamDocument {
  return buildParentDocument();
}

function pictureDocument(): NativeExamDocument {
  return {
    ...document(),
    assets: [
      {
        asset_id: "asset_001",
        byte_length: 8,
        height: 1,
        media_type: "image/png",
        sha256: "a".repeat(64),
        width: 1,
      },
    ],
    instructions: [{ heading_level: null, segments: [{ asset_id: "asset_001", kind: "asset" }] }],
  };
}

const OK_COMMAND = { document: document(), export_blockers: [] };

describe("publicExamWorkspace transport", () => {
  it("starts a blank exam on the public blank route", async () => {
    publicApiPostMock.mockResolvedValueOnce(OK_COMMAND);

    const result = await createPublicExamWorkspaceBlank();

    expect(publicApiPostMock).toHaveBeenCalledWith(`${WORKSPACE_ROOT}/blank`);
    expect(result).toBe(OK_COMMAND);
  });

  it("sends every command body with the whole document under the workspace root", async () => {
    publicApiPostMock.mockResolvedValue({ ...OK_COMMAND, removed_parent_id: null, dropped_content: [] });
    const exam = document();
    const child = buildFreeTextItem(2);
    const instruction = [
      { heading_level: null, segments: [{ kind: "text" as const, marks: [], text: "Läs texten." }] },
    ];

    await createPublicExamWorkspaceParent({
      child,
      document: exam,
      instruction,
      position: 0,
    });
    await addPublicExamWorkspaceChild("parent 1", { child, document: exam, position: 1 });
    await deletePublicExamWorkspaceChild("parent 1", "item/2", { document: exam });
    await reorderPublicExamWorkspaceChildren("parent 1", {
      document: exam,
      item_ids: ["item/2", "item_001"],
    });
    await deletePublicExamWorkspaceParent("parent 1", { document: exam, mode: "with_questions" });
    await changePublicExamWorkspaceItemType({
      document: exam,
      item_id: "item/2",
      target_kind: "single_choice",
    });
    await requestPublicExamWorkspaceAnswerMisspellings({
      accepted_values: ["Göteborg"],
      document_text: "Hon heter Göteborg.",
      other_gold_answers: ["Stockholm"],
    });

    expect(publicApiPostMock.mock.calls).toEqual([
      [`${WORKSPACE_ROOT}/parents`, { child, document: exam, instruction, position: 0 }],
      [
        `${WORKSPACE_ROOT}/parents/parent%201/children`,
        { child, document: exam, position: 1 },
      ],
      [
        `${WORKSPACE_ROOT}/parents/parent%201/children/item%2F2/delete`,
        { document: exam },
      ],
      [
        `${WORKSPACE_ROOT}/parents/parent%201/children/order`,
        { document: exam, item_ids: ["item/2", "item_001"] },
      ],
      [
        `${WORKSPACE_ROOT}/parents/parent%201/delete`,
        { document: exam, mode: "with_questions" },
      ],
      [
        `${WORKSPACE_ROOT}/change-type`,
        { document: exam, item_id: "item/2", target_kind: "single_choice" },
      ],
      [
        `${WORKSPACE_ROOT}/answer-misspellings`,
        {
          accepted_values: ["Göteborg"],
          document_text: "Hon heter Göteborg.",
          other_gold_answers: ["Stockholm"],
        },
      ],
    ]);
  });

  it("groups items, inserts an empty part and moves an item on the public part routes", async () => {
    publicApiPostMock
      .mockResolvedValueOnce({ ...OK_COMMAND, created_parent_id: "parent_002" })
      .mockResolvedValueOnce({ ...OK_COMMAND, created_parent_id: "parent_003" })
      .mockResolvedValueOnce(OK_COMMAND)
      .mockResolvedValueOnce(OK_COMMAND);
    const exam = document();

    const grouped = await groupPublicExamWorkspaceItems(exam, ["item_001", "item_002"]);
    const emptied = await createEmptyPublicExamWorkspacePart(exam, 2);
    const moved = await movePublicExamWorkspaceItem(exam, "item_004", "parent_001");
    const movedOut = await movePublicExamWorkspaceItem(exam, "item_004", null);

    expect(publicApiPostMock.mock.calls).toEqual([
      [`${WORKSPACE_ROOT}/parents/group`, { document: exam, item_ids: ["item_001", "item_002"] }],
      [`${WORKSPACE_ROOT}/parents/empty`, { document: exam, position: 2 }],
      [
        `${WORKSPACE_ROOT}/parents/move`,
        { document: exam, item_id: "item_004", target_parent_id: "parent_001" },
      ],
      [
        `${WORKSPACE_ROOT}/parents/move`,
        { document: exam, item_id: "item_004", target_parent_id: null },
      ],
    ]);
    expect(grouped).toEqual({ ...OK_COMMAND, created_parent_id: "parent_002" });
    expect(emptied).toEqual({ ...OK_COMMAND, created_parent_id: "parent_003" });
    expect(moved).toEqual(OK_COMMAND);
    expect(movedOut).toEqual(OK_COMMAND);
  });

  it("reads the guest course catalog from the workspace route", async () => {
    const catalog = { courses: [], registered_course_keys: [] };
    publicApiGetMock.mockResolvedValueOnce(catalog);

    const result = await getPublicExamCourseCatalog();

    expect(publicApiGetMock).toHaveBeenCalledWith(`${WORKSPACE_ROOT}/courses`);
    expect(result).toBe(catalog);
  });

  it("downloads an export from the document JSON and one asset part per declared picture", async () => {
    const exam = pictureDocument();
    const png = new Blob(["png-bytes"], { type: "image/png" });
    publicApiFetchBlobResponseMock.mockResolvedValueOnce({
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: "prov-qti.zip",
    });

    const result = await downloadPublicExamWorkspaceExport("qti", {
      assets: { asset_001: png },
      document: exam,
    });

    expect(publicApiFetchBlobResponseMock).toHaveBeenCalledTimes(1);
    const [path, options] = publicApiFetchBlobResponseMock.mock.calls[0]!;
    expect(path).toBe(`${WORKSPACE_ROOT}/exports/qti`);
    expect(options?.method).toBe("POST");
    const form = options?.body as FormData;
    expect(form).toBeInstanceOf(FormData);
    expect(form.get("document")).toBe(JSON.stringify(exam));
    const asset = form.get("asset:asset_001");
    expect(asset).toBeInstanceOf(Blob);
    expect((asset as Blob).type).toBe("image/png");
    expect((asset as Blob).size).toBe(png.size);
    expect(form.get("asset_001")).toBeNull();
    expect(result).toEqual({
      blob: expect.any(Blob),
      contentType: "application/zip",
      filename: "prov-qti.zip",
    });
  });

  it("treats an export response without a Content-Disposition file name as a fault", async () => {
    publicApiFetchBlobResponseMock.mockResolvedValueOnce({
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: null,
    });

    await expect(
      downloadPublicExamWorkspaceExport("pdf", { assets: {}, document: document() }),
    ).rejects.toThrow("Content-Disposition");
  });

  it("asks for the checklist on the same multipart body", async () => {
    const exam = pictureDocument();
    const png = new Blob(["png-bytes"], { type: "image/png" });
    const checklist = { entries: [] };
    publicApiPostMock.mockResolvedValueOnce(checklist);

    const result = await getPublicExamWorkspaceExportChecklist({
      assets: { asset_001: png },
      document: exam,
    });

    expect(publicApiPostMock).toHaveBeenCalledTimes(1);
    const [path, body] = publicApiPostMock.mock.calls[0]!;
    expect(path).toBe(`${WORKSPACE_ROOT}/export-checklist`);
    const form = body as FormData;
    expect(form.get("document")).toBe(JSON.stringify(exam));
    const asset = form.get("asset:asset_001");
    expect(asset).toBeInstanceOf(Blob);
    expect((asset as Blob).type).toBe("image/png");
    expect((asset as Blob).size).toBe(png.size);
    expect(result).toBe(checklist);
  });

  it("refuses to build an export body while a declared picture has no stored bytes", async () => {
    await expect(
      downloadPublicExamWorkspaceExport("qti", { assets: {}, document: pictureDocument() }),
    ).rejects.toThrow("asset_001");
    expect(publicApiFetchBlobResponseMock).not.toHaveBeenCalled();
  });

  it("parses a guest QTI .zip into the document and decodes each base64 picture to its blob", async () => {
    const exam = pictureDocument();
    const pngBytes = new Uint8Array([137, 80, 78, 71, 1, 2, 3, 4]);
    const binary = Array.from(pngBytes, (byte) => String.fromCharCode(byte)).join("");
    publicApiPostMock.mockResolvedValueOnce({
      assets_by_id: { asset_001: btoa(binary) },
      document: exam,
      notes: [],
    });
    const file = new File(["qti"], "Prov_HT25.zip", { type: "application/zip" });

    const result = await importPublicExamWorkspaceQti(file, "SVESVE02");

    expect(publicApiPostMock).toHaveBeenCalledTimes(1);
    const [path, body] = publicApiPostMock.mock.calls[0]!;
    expect(path).toBe(`${WORKSPACE_ROOT}/imports/qti`);
    expect(body).toBeInstanceOf(FormData);
    if (!(body instanceof FormData)) {
      throw new Error("expected the QTI import to send a multipart body");
    }
    const uploaded = body.get("file");
    expect(uploaded).toBeInstanceOf(File);
    if (!(uploaded instanceof File)) {
      throw new Error("expected the QTI import to upload the package as a file");
    }
    expect(uploaded.name).toBe("Prov_HT25.zip");
    expect(body.get("course_key")).toBe("SVESVE02");
    expect(result.document).toEqual(exam);
    const blob = result.assets["asset_001"];
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe("image/png");
    expect(blob.size).toBe(pngBytes.length);
  });

  it("omits the course key for a guest QTI .zip without a course", async () => {
    const exam = document();
    publicApiPostMock.mockResolvedValueOnce({ assets_by_id: {}, document: exam, notes: [] });

    await importPublicExamWorkspaceQti(
      new File(["qti"], "Prov_HT25.zip", { type: "application/zip" }),
      null,
    );

    const [, body] = publicApiPostMock.mock.calls[0]!;
    expect(body).toBeInstanceOf(FormData);
    if (!(body instanceof FormData)) {
      throw new Error("expected the QTI import to send a multipart body");
    }
    expect(body.get("course_key")).toBeNull();
  });
});
