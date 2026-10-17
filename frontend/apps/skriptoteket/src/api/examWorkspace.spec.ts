/**
 * Exam workspace transport behavior.
 *
 * Expected behavior:
 *   The thin typed client calls the exam workspace document endpoints with
 *   the exact paths and payload shapes the backend contract defines: multipart
 *   import with the `file` field, head-version listing, lineage readback, blob
 *   export downloads per target, and answer-key suggestion request/status.
 */

import { describe, expect, it, vi } from "vitest";

import { apiFetchBlobResponse, apiGet, apiPost } from "./client";
import {
  downloadExamWorkspaceExport,
  getExamWorkspaceConversionStatus,
  getExamWorkspaceDocument,
  getExamWorkspaceExportChecklist,
  getExamWorkspaceAnswerKeySuggestions,
  importExamWorkspaceDocument,
  listExamWorkspaceDocuments,
  requestExamWorkspaceAnswerKeySuggestions,
  requestExamWorkspaceAnswerMisspellings,
} from "./examWorkspace";
import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "./examWorkspace";

vi.mock("./client", () => ({
  apiFetchBlobResponse: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}));

const apiGetMock = vi.mocked(apiGet);
const apiPostMock = vi.mocked(apiPost);
const apiFetchBlobResponseMock = vi.mocked(apiFetchBlobResponse);

const DOCUMENTS_ROOT = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents";
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
      {
        ai_suggestion: null,
        facit_text: null,
        criteria: [],
        printed_label: null,
        retry_source: null,
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
        body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Beskriv vattnets kretslopp." }] }],
        choices: [],
        gaps: [],
        match_left: [],
        match_right: [],
        item_id: "item_001",
        kind: "free_text",
        points: 2,
        points_estimated: false,
        review: {
          confidence: 0.9,
          parse_origin: "deterministic",
          reasons: [],
          state: "review_complete",
        },
        sequence: 1,
        source_anchor: null,
        tick_points: null,
      },
    ],
    origin: {
      extractor_version: "docx-extractor-1",
      kind: "docx_import",
      source_filename: "NO_Prov_HT25.docx",
      source_sha256: "abc123",
    },
    parents: [],
    revision,
    header: {},
    schema_version: "native_exam_document_v4",
    title: "NO-prov HT25",
  };
}

function buildResponse(revision: number): ExamWorkspaceDocumentResponse {
  return {
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

  it("downloads each export target as a blob from the export path", async () => {
    const blobResponse = {
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: "prov-qti.zip",
    };
    apiFetchBlobResponseMock.mockResolvedValueOnce(blobResponse);

    const result = await downloadExamWorkspaceExport("lineage-1", "qti", 2);

    expect(apiFetchBlobResponseMock).toHaveBeenCalledWith(
      `${DOCUMENTS_ROOT}/lineage-1/exports/qti?expected_revision=2`,
    );
    expect(result).toBe(blobResponse);
  });

  it("requests only the checklist for the exported revision", async () => {
    const response = { entries: [] };
    apiGetMock.mockResolvedValueOnce(response);

    const result = await getExamWorkspaceExportChecklist("lineage-1", 2);

    expect(apiGetMock).toHaveBeenCalledWith(
      `${DOCUMENTS_ROOT}/lineage-1/export-checklist?expected_revision=2`,
    );
    expect(result).toBe(response);
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
});
