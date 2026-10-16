/**
 * Document-state fixtures for `useExamWorkspaceDocument` specs.
 *
 * Purpose:
 *   Open the real matching question through the document state with a
 *   mocked transport, read the open item back, build a save or reload
 *   response around a given item, read the open exam opening that arrivals
 *   are delivered for, and hold a response pending so a spec can act while a
 *   save is in flight.
 */

import { flushPromises } from "@vue/test-utils";
import { effectScope } from "vue";
import type { Mock } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";

export type DocumentState = ReturnType<typeof useExamWorkspaceDocument>;

export function buildResponse(
  item: NativeExamItem = buildMatchingItem(),
): ExamWorkspaceDocumentResponse {
  return {
    conversion: null,
    document: {
      assets: [],
      document_id: "doc-1",
      instructions: [],
      items: [item],
      origin: {
        extractor_version: "docx-extractor-1",
        kind: "docx_import",
        source_filename: "english-1.docx",
        source_sha256: "abc123",
      },
      parents: [],
      revision: 1,
      header: {},
      schema_version: "native_exam_document_v3",
      title: "English 1",
    },
    notes: [],
    summary: {
      lineage_id: "lineage-1",
      name: "english-1.provdokument.zip",
      saved_at: "2026-10-11T08:00:00Z",
      vault_file_id: "file-1",
      version: 1,
    },
  };
}

/** The response a save returns: the given document as the next version. */
export function savedResponse(document: NativeExamDocument): ExamWorkspaceDocumentResponse {
  return { ...buildResponse(), document, summary: { ...buildResponse().summary, version: 2 } };
}

export async function openMatchingDocument(
  getDocument: Mock,
  item?: NativeExamItem,
): Promise<DocumentState> {
  getDocument.mockResolvedValue(buildResponse(item));
  const state = effectScope().run(() => useExamWorkspaceDocument());
  if (!state) {
    throw new Error("expected the document state to be created");
  }
  await state.openDocument("lineage-1");
  await flushPromises();
  return state;
}

export function currentItem(state: DocumentState): NativeExamItem {
  const item = state.workspaceDocument.value?.items[0];
  if (!item) {
    throw new Error("expected a loaded matching item");
  }
  return item;
}

export function currentDocument(state: DocumentState): NativeExamDocument {
  const document = state.workspaceDocument.value;
  if (!document) {
    throw new Error("expected an open document");
  }
  return document;
}

/** The exam opening in front of the teacher, which an arrival is delivered for. */
export function openingOf(state: DocumentState): ExamWorkspaceOpening {
  const opening = state.openExam.value;
  if (!opening) {
    throw new Error("expected an open exam");
  }
  return opening;
}

export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((pendingResolve, pendingReject) => {
    resolve = pendingResolve;
    reject = pendingReject;
  });
  return { promise, reject, resolve };
}
