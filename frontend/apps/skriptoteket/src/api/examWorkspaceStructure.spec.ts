/**
 * Exam workspace structure transport behavior.
 *
 * Expected behavior:
 *   The thin typed client calls the instruction and deluppgift delete
 *   endpoints with the cursor in the body and the exact paths the backend
 *   contract defines, including the with-children variant.
 */

import { describe, expect, it, vi } from "vitest";

import { apiFetch } from "./client";
import { deleteExamWorkspaceChild, deleteExamWorkspaceParent } from "./examWorkspaceStructure";

vi.mock("./client", () => ({
  apiFetch: vi.fn(),
  apiFetchBlobResponse: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}));

const apiFetchMock = vi.mocked(apiFetch);

const DOCUMENTS_ROOT = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents";

describe("examWorkspaceStructure transport", () => {
  it("deletes an instruction, with or without its questions, and one deluppgift", async () => {
    apiFetchMock.mockResolvedValue({});
    const body = { body: { expected_cursor: "cursor-1" }, method: "DELETE" };

    await deleteExamWorkspaceParent("lineage/1", "parent 1", "keep_questions", "cursor-1");
    await deleteExamWorkspaceParent("lineage/1", "parent 1", "with_questions", "cursor-1");
    await deleteExamWorkspaceChild("lineage/1", "parent 1", "item_002", "cursor-1");

    expect(apiFetchMock.mock.calls).toEqual([
      [`${DOCUMENTS_ROOT}/lineage%2F1/parents/parent%201`, body],
      [`${DOCUMENTS_ROOT}/lineage%2F1/parents/parent%201/with-children`, body],
      [`${DOCUMENTS_ROOT}/lineage%2F1/parents/parent%201/children/item_002`, body],
    ]);
  });
});
