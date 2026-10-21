/**
 * Exam workspace transport behavior.
 *
 * Expected behavior:
 *   The thin typed client calls the exam workspace document endpoints with
 *   the exact paths and payload shapes the backend contract defines: multipart
 *   import with the `file` field, head-version listing, lineage readback,
 *   answer-key suggestion request/status, and misspellings.
 */

import { describe, expect, it, vi } from "vitest";

import { buildFreeTextItem } from "../test/examWorkspaceFixtures";
import { apiFetch, apiGet, apiPost } from "./client";
import {
  getExamWorkspaceConversionStatus,
  getExamWorkspaceDocument,
  getExamWorkspaceAnswerKeySuggestions,
  importExamWorkspaceDocument,
  importExamWorkspaceGuestDraft,
  importExamWorkspaceQti,
  listExamWorkspaceDocuments,
  releaseExamWorkspaceEditLease,
  requestExamWorkspaceAnswerKeySuggestions,
  requestExamWorkspaceAnswerMisspellings,
  storeExamWorkspaceUndoStep,
} from "./examWorkspace";
import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "./examWorkspace";

vi.mock("./client", () => ({
  apiFetch: vi.fn(),
  apiFetchBlobResponse: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}));

const apiGetMock = vi.mocked(apiGet);
const apiPostMock = vi.mocked(apiPost);
const apiFetchMock = vi.mocked(apiFetch);

const DOCUMENTS_ROOT = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents";
const QTI_IMPORT_PATH = "/api/v1/apps/documents.conversion_hub/exam-workspace/import-qti";
const ANSWER_MISSPELLINGS_PATH =
  "/api/v1/apps/documents.conversion_hub/exam-workspace/answer-misspellings";

function buildDocument(revision: number): NativeExamDocument {
  return {
    assets: [],
    document_id: "doc-1",
    instructions: [
      { heading_level: null, segments: [{ kind: "text", marks: [], text: "Besvara alla frågor." }] },
    ],
    items: [
      buildFreeTextItem(1, {
        body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Beskriv vattnets kretslopp." }] }],
      }),
    ],
    origin: {
      extractor_version: "docx-extractor-1",
      kind: "docx_import",
      source_filename: "NO_Prov_HT25.docx",
      source_sha256: "abc123",
    },
    parents: [],
    revision,
    header: { tags: [] },
    schema_version: "native_exam_document_v11",
    title: "NO-prov HT25",
  };
}

function buildResponse(revision: number): ExamWorkspaceDocumentResponse {
  return {
    export_blockers: [],
    history_cursor: "00000000-0000-4000-8000-000000000001",
    conversion: null,
    document: buildDocument(revision),
    saved_document: buildDocument(revision),
    notes: [],
    summary: {
      course_key: null,
      lineage_id: "lineage-1",
      name: "NO-prov HT25",
      saved_at: "2026-10-09T08:00:00Z",
      title: "NO-prov HT25",
      vault_file_id: "file-1",
      version: revision,
    },
  };
}

describe("examWorkspace transport", () => {
  it("imports a .docx as multipart form data with the `file` field", async () => {
    const response = { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null };
    apiPostMock.mockResolvedValueOnce(response);
    const file = new File(["prov"], "NO_Prov_HT25.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    const result = await importExamWorkspaceDocument(file);

    expect(apiPostMock).toHaveBeenCalledTimes(1);
    const [path, body] = apiPostMock.mock.calls[0];
    expect(path).toBe(DOCUMENTS_ROOT);
    expect(body).toBeInstanceOf(FormData);
    const sentFile = (body as FormData).get("file");
    expect(sentFile).toBeInstanceOf(File);
    expect((sentFile as File).name).toBe("NO_Prov_HT25.docx");
    expect(result).toBe(response);
  });

  it("imports a QTI package to the import-qti path with the `file` and `course_key` multipart fields", async () => {
    const summary = {
      course_key: "gy11:SVESVE01",
      lineage_id: "lineage-1",
      name: "NO-prov HT25.zip",
      saved_at: "2026-10-18T09:00:00Z",
      title: "NO-prov HT25",
      vault_file_id: "file-1",
      version: 1,
    };
    apiPostMock.mockResolvedValueOnce(summary);
    const file = new File(["qti"], "NO_Prov_HT25.zip", { type: "application/zip" });

    const result = await importExamWorkspaceQti(file, "gy11:SVESVE01");

    expect(apiPostMock).toHaveBeenCalledTimes(1);
    const [path, body] = apiPostMock.mock.calls[0];
    expect(path).toBe(QTI_IMPORT_PATH);
    expect(body).toBeInstanceOf(FormData);
    const form = body as FormData;
    const sentFile = form.get("file");
    expect(sentFile).toBeInstanceOf(File);
    expect((sentFile as File).name).toBe("NO_Prov_HT25.zip");
    expect(form.get("course_key")).toBe("gy11:SVESVE01");
    expect(result).toBe(summary);
  });

  it("omits the course_key field from a QTI package import without a course", async () => {
    apiPostMock.mockResolvedValueOnce({});
    const file = new File(["qti"], "NO_Prov_HT25.zip", { type: "application/zip" });

    await importExamWorkspaceQti(file, null);

    const form = apiPostMock.mock.calls[0][1] as FormData;
    expect(form.get("course_key")).toBeNull();
  });

  it("reads conversion status using an encoded job id", async () => {
    const status = { job_id: "job/1", lineage_id: "lineage-1", state: "running", error_message: null };
    apiGetMock.mockResolvedValueOnce(status);
    expect(await getExamWorkspaceConversionStatus("job/1")).toBe(status);
    expect(apiGetMock).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/exam-workspace/conversion-jobs/job%2F1",
    );
  });

  it("reads a document lineage by id", async () => {
    const response = buildResponse(3);
    apiGetMock.mockResolvedValueOnce(response);

    const result = await getExamWorkspaceDocument("lineage-1");

    expect(apiGetMock).toHaveBeenCalledWith(`${DOCUMENTS_ROOT}/lineage-1`);
    expect(result).toBe(response);
  });

  it("encodes the lineage id in the document path", async () => {
    apiGetMock.mockResolvedValueOnce(buildResponse(1));

    await getExamWorkspaceDocument("lineage/1");

    expect(apiGetMock).toHaveBeenCalledWith(`${DOCUMENTS_ROOT}/lineage%2F1`);
  });

  it("lists saved documents from the collection path", async () => {
    apiGetMock.mockResolvedValueOnce({ documents: [] });

    const result = await listExamWorkspaceDocuments();

    expect(apiGetMock).toHaveBeenCalledWith(DOCUMENTS_ROOT);
    expect(result).toEqual({ documents: [] });
  });

  it("requests suggestions with the editor document and reads status per job", async () => {
    const status = {
      job_id: "job-1",
      lineage_id: "lineage-1",
      state: "queued" as const,
      suggestions: [],
    };
    apiPostMock.mockResolvedValueOnce(status);
    apiGetMock.mockResolvedValueOnce(status);
    const document = buildDocument(2);

    await requestExamWorkspaceAnswerKeySuggestions("lineage-1", document);
    await requestExamWorkspaceAnswerKeySuggestions("lineage-1", document, "item_001");
    await getExamWorkspaceAnswerKeySuggestions("lineage-1", "job-1");

    expect(apiPostMock).toHaveBeenNthCalledWith(
      1,
      `${DOCUMENTS_ROOT}/lineage-1/answer-key-suggestions`,
      { document, item_id: null },
    );
    expect(apiPostMock).toHaveBeenNthCalledWith(
      2,
      `${DOCUMENTS_ROOT}/lineage-1/answer-key-suggestions`,
      { document, item_id: "item_001" },
    );
    expect(apiGetMock).toHaveBeenCalledWith(
      `${DOCUMENTS_ROOT}/lineage-1/answer-key-suggestions/job-1`,
    );
  });

  it("requests misspellings for the newly added answers with the item's gold answers", async () => {
    const response = { automatic_values: ["Götebprg"] };
    apiPostMock.mockResolvedValueOnce(response);
    const request = {
      accepted_values: ["Göteborg"],
      other_gold_answers: ["Stockholm", "Göteborg"],
      document_text: "Hon heter Stockholm och Oslo.",
    };

    const result = await requestExamWorkspaceAnswerMisspellings(request);

    expect(apiPostMock).toHaveBeenCalledTimes(1);
    expect(apiPostMock).toHaveBeenCalledWith(ANSWER_MISSPELLINGS_PATH, request);
    expect(result).toBe(response);
  });

  it("imports the guest draft as multipart bound to the owner session", async () => {
    const response = buildResponse(1);
    apiFetchMock.mockResolvedValueOnce(response);
    const document = {
      ...buildDocument(1),
      assets: [
        {
          asset_id: "asset-a",
          byte_length: 1,
          height: 1,
          media_type: "image/png" as const,
          sha256: "a".repeat(64),
          width: 1,
        },
        {
          asset_id: "asset-b",
          byte_length: 1,
          height: 1,
          media_type: "image/png" as const,
          sha256: "b".repeat(64),
          width: 1,
        },
      ],
    };
    const blobA = new Blob(["aa"]);
    const blobB = new Blob(["b"]);

    const session = Symbol("guest handoff owner");
    const onSupersededSuccess = vi.fn();
    const signal = new AbortController().signal;
    const result = await importExamWorkspaceGuestDraft("draft-1", document, {
      "asset-a": blobA,
      "asset-b": blobB,
      "asset-extra": new Blob(["extra"]),
    }, ["Fråga 3 hoppades över."], { onSupersededSuccess, session, signal });

    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    const [path, options] = apiFetchMock.mock.calls[0];
    expect(path).toBe("/api/v1/apps/documents.conversion_hub/exam-workspace/guest-drafts");
    expect(options).toMatchObject({ method: "POST", session, onSupersededSuccess, signal });
    expect(options?.body).toBeInstanceOf(FormData);
    const form = options?.body as FormData;
    expect(form.get("draft_id")).toBe("draft-1");
    expect(JSON.parse(form.get("document") as string)).toEqual(document);
    expect(JSON.parse(form.get("notes") as string)).toEqual(["Fråga 3 hoppades över."]);
    expect(form.get("asset:asset-a")).toBeInstanceOf(Blob);
    expect((form.get("asset:asset-a") as Blob).size).toBe(2);
    expect(form.get("asset:asset-b")).toBeInstanceOf(Blob);
    expect((form.get("asset:asset-b") as Blob).size).toBe(1);
    expect(form.get("asset:asset-extra")).toBeNull();
    expect(result).toBe(response);
  });

  it("releases the edit lease with a plain POST by default", async () => {
    const response = { holder_tab_id: null, renewed_at: null, takeover_requested: false, takeover_requested_by: null };
    apiPostMock.mockResolvedValueOnce(response);

    const result = await releaseExamWorkspaceEditLease("lineage-1", "tab-a");

    expect(apiPostMock).toHaveBeenCalledWith(`${DOCUMENTS_ROOT}/lineage-1/edit-lease/release`, {
      tab_id: "tab-a",
    });
    expect(apiFetchMock).not.toHaveBeenCalled();
    expect(result).toBe(response);
  });

  it("releases the edit lease with keepalive so a pagehide release survives the unload", async () => {
    const response = { holder_tab_id: null, renewed_at: null, takeover_requested: false, takeover_requested_by: null };
    apiFetchMock.mockResolvedValueOnce(response);

    const result = await releaseExamWorkspaceEditLease("lineage-1", "tab-a", { keepalive: true });

    expect(apiFetchMock).toHaveBeenCalledWith(`${DOCUMENTS_ROOT}/lineage-1/edit-lease/release`, {
      body: { tab_id: "tab-a" },
      keepalive: true,
      method: "POST",
    });
    expect(result).toBe(response);
  });

  it("posts new picture bytes as standard base64 new_assets_by_id", async () => {
    apiPostMock.mockResolvedValueOnce({ document: buildDocument(1), history: {} });
    const bytes = new Uint8Array([0, 1, 2, 250, 251, 252, 253, 254, 255, 72, 101, 106]);
    const blob = new Blob([bytes]);
    // jsdom's Blob has no arrayBuffer; equip this blob with the production Web API.
    Object.defineProperty(blob, "arrayBuffer", {
      value: async () => Uint8Array.from(bytes).buffer as ArrayBuffer,
    });
    const empty = new Blob([]);
    Object.defineProperty(empty, "arrayBuffer", { value: async () => new ArrayBuffer(0) });

    await storeExamWorkspaceUndoStep("lineage-1", {
      afterStepId: null,
      document: buildDocument(1),
      expectedCursor: "00000000-0000-4000-8000-000000000001",
      newPictures: { asset_001: blob, asset_002: empty },
      tabId: "00000000-0000-4000-8000-000000000002",
    });

    expect(apiPostMock).toHaveBeenCalledTimes(1);
    const [path, body] = apiPostMock.mock.calls[0] as [
      string,
      { after_step_id?: unknown; new_assets_by_id?: unknown; tab_id?: unknown },
    ];
    expect(path).toBe(`${DOCUMENTS_ROOT}/lineage-1/autosaves`);
    // The standard-base64 encoding of [0, 1, 2, 250, 251, 252, 253, 254, 255, 72, 101, 106].
    expect(body["new_assets_by_id"]).toEqual({ asset_001: "AAEC+vv8/f7/SGVq", asset_002: "" });
    expect(String((body["new_assets_by_id"] as Record<string, string>)["asset_001"])).toMatch(
      /^[A-Za-z0-9+/=]+$/,
    );
    expect(body["after_step_id"]).toBeNull();
    expect(body["tab_id"]).toBe("00000000-0000-4000-8000-000000000002");
  });

  it("posts an empty new_assets_by_id when the store carries no new pictures", async () => {
    apiPostMock.mockResolvedValueOnce({ document: buildDocument(1), history: {} });

    await storeExamWorkspaceUndoStep("lineage-1", {
      afterStepId: "step-1",
      document: buildDocument(1),
      expectedCursor: "00000000-0000-4000-8000-000000000001",
      newPictures: {},
      tabId: "00000000-0000-4000-8000-000000000002",
    });

    const [, body] = apiPostMock.mock.calls[0] as [string, { new_assets_by_id?: unknown }];
    expect(body["new_assets_by_id"]).toEqual({});
  });
});
