/**
 * Exam workspace transport behavior.
 *
 * Expected behavior:
 *   The thin typed client calls the exam workspace document endpoints with
 *   the exact paths and payload shapes the backend contract defines: multipart
 *   import with the `file` field, lineage readback, and versioned PUT saves
 *   with `expected_revision` plus the full native document.
 */

import { describe, expect, it, vi } from "vitest";

import { apiGet, apiPost, apiPut } from "./client";
import {
  getExamWorkspaceDocument,
  importExamWorkspaceDocument,
  saveExamWorkspaceDocument,
} from "./examWorkspace";
import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "./examWorkspace";

vi.mock("./client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}));

const apiGetMock = vi.mocked(apiGet);
const apiPostMock = vi.mocked(apiPost);
const apiPutMock = vi.mocked(apiPut);

const DOCUMENTS_ROOT = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents";

function buildDocument(revision: number): NativeExamDocument {
  return {
    assets: [],
    document_id: "doc-1",
    instructions: ["Besvara alla frågor."],
    items: [
      {
        answer_key: { correct_choice_ids: [], origin: "not_applicable" },
        body: [{ segments: [{ kind: "text", text: "Beskriv vattnets kretslopp." }] }],
        choices: [],
        gaps: [],
        item_id: "item_001",
        kind: "free_text",
        points: 2,
        review: {
          confidence: 0.9,
          parse_origin: "deterministic",
          reasons: [],
          state: "review_complete",
        },
        sequence: 1,
        source_anchor: null,
        title: "Kretsloppet",
      },
    ],
    origin: {
      extractor_version: "docx-extractor-1",
      kind: "docx_import",
      source_filename: "NO_Prov_HT25.docx",
      source_sha256: "abc123",
    },
    revision,
    schema_version: "native_exam_document_v1",
    title: "NO-prov HT25",
  };
}

function buildResponse(revision: number): ExamWorkspaceDocumentResponse {
  return {
    document: buildDocument(revision),
    notes: [],
    summary: {
      lineage_id: "lineage-1",
      name: "NO-prov HT25",
      saved_at: "2026-10-09T08:00:00Z",
      vault_file_id: "file-1",
      version: revision,
    },
  };
}

describe("examWorkspace transport", () => {
  it("imports a .docx as multipart form data with the `file` field", async () => {
    const response = buildResponse(1);
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

  it("saves with expected_revision and the full document as the PUT body", async () => {
    const response = buildResponse(5);
    apiPutMock.mockResolvedValueOnce(response);
    const document = buildDocument(5);

    const result = await saveExamWorkspaceDocument("lineage-1", {
      document,
      expectedRevision: 4,
    });

    expect(apiPutMock).toHaveBeenCalledWith(`${DOCUMENTS_ROOT}/lineage-1`, {
      document,
      expected_revision: 4,
    });
    expect(result).toBe(response);
  });
});
