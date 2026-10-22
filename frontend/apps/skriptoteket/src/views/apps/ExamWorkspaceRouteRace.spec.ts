/**
 * Exam workspace route race: the last route asked for wins, with its own generation.
 *
 * Fail-first for TASK-SKRIPT-40-04-14 W1 (Mac walk step 5, defect 1): tab B is
 * editable on exam X while exam Y's lease is contended; B pushes
 * `?document=Y`, then pushes `?document=X` back. B must end on X, open and
 * editable, without ever claiming Y or releasing X. The same holds when Y's
 * document GET resolves (Y installs read-only) before the push back to X: X
 * reopens editable and a stale Y grant is released, never installed.
 *
 * Slice purpose:
 *   Pin the real-router, real-address, real-document behaviour around two
 *   route pushes with Y's document GET deferred and Y's lease contended.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceEditLeaseResponse,
} from "../../api/examWorkspace";
import { buildSavedExamSummary } from "./exam-workspace/useExamWorkspaceDocument.specSupport";
import {
  buildResponse,
  mountExamWorkspace,
  resetSliceApiMocks,
  unmountExamWorkspace,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  claimExamWorkspaceEditLease: vi.fn(),
  renewExamWorkspaceEditLease: vi.fn(),
  releaseExamWorkspaceEditLease: vi.fn(),
  requestExamWorkspaceEditLeaseTakeover: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const X_LINEAGE = "lineage-1";
const Y_LINEAGE = "lineage-2";
const X_TITLE = "Provet X";
const Y_TITLE = "Matteprov v48";

function xResponse(): ExamWorkspaceDocumentResponse {
  return buildResponse({ title: X_TITLE, version: 1 });
}

function yResponse(): ExamWorkspaceDocumentResponse {
  const base = buildResponse({ title: Y_TITLE, version: 3 });
  const document = { ...base.document, document_id: Y_LINEAGE };
  return {
    ...base,
    document,
    saved_document: { ...document },
    summary: buildSavedExamSummary({
      lineage_id: Y_LINEAGE,
      name: "Matteprov_v48.provdokument.zip",
      saved_at: "2026-10-08T07:30:00Z",
      title: Y_TITLE,
      vault_file_id: "file-9",
      version: 3,
    }),
  };
}

function heldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 });
}

function leaseResponse(holder: string): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: holder,
    renewed_at: "2026-10-19T12:00:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
} {
  let resolveFn: ((value: T) => void) | null = null;
  const promise = new Promise<T>((resolve) => {
    resolveFn = resolve;
  });
  return {
    promise,
    resolve: (value: T) => {
      if (resolveFn !== null) {
        resolveFn(value);
      }
    },
  };
}

/** Flush the gate's document read, step-list read and lease claim continuations. */
async function settle(): Promise<void> {
  for (let index = 0; index < 8; index += 1) {
    await flushPromises();
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  for (const mock of Object.values(exportApiMocks)) {
    mock.mockReset();
  }
  resetSliceApiMocks(apiMocks);
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue({
    job_id: "job-1",
    lineage_id: X_LINEAGE,
    state: "succeeded",
    error_message: null,
    summary: null,
    document_revision: 1,
    phase: null,
    phase_started_at: null,
    questions_total: 0,
    questions_done: 0,
    questions_received: 0,
    units: [],
  });
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.renewExamWorkspaceEditLease.mockImplementation(async () => leaseResponse("tab-a"));
  apiMocks.releaseExamWorkspaceEditLease.mockImplementation(async () => leaseResponse("tab-a"));
  apiMocks.requestExamWorkspaceEditLeaseTakeover.mockImplementation(async () => leaseResponse("tab-a"));
});

afterEach(() => {
  unmountExamWorkspace();
  vi.useRealTimers();
});

describe("ExamWorkspaceView route race", () => {
  it("a. a push back to X before Y resolves keeps X open and editable", async () => {
    const claims: string[] = [];
    const releases: string[] = [];
    let yFree = false;
    apiMocks.claimExamWorkspaceEditLease.mockImplementation(async (lineageId: string) => {
      claims.push(lineageId);
      if (lineageId === Y_LINEAGE && !yFree) {
        throw heldError();
      }
      return leaseResponse("tab-a");
    });
    apiMocks.releaseExamWorkspaceEditLease.mockImplementation(async (lineageId: string) => {
      releases.push(lineageId);
      return leaseResponse("tab-a");
    });
    const yGet = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
      if (lineageId === Y_LINEAGE) {
        return yGet.promise;
      }
      return Promise.resolve(xResponse());
    });

    const { router, wrapper } = await mountExamWorkspace({ document: X_LINEAGE });
    await settle();
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(X_TITLE);

    await router.push({ query: { document: Y_LINEAGE } });
    await settle();
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith(Y_LINEAGE);

    await router.push({ query: { document: X_LINEAGE } });
    await settle();

    yGet.resolve(yResponse());
    await settle();
    yFree = true;
    await vi.advanceTimersByTimeAsync(6000);
    await vi.advanceTimersByTimeAsync(6000);
    await settle();

    expect(router.currentRoute.value.query.document).toBe(X_LINEAGE);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(X_TITLE);
    expect(wrapper.find('[data-test="exam-workspace-edit-lease"]').exists()).toBe(false);
    expect(claims).not.toContain(Y_LINEAGE);
    expect(releases).not.toContain(X_LINEAGE);
  });

  it("b. a push back to X after Y installs readonly reopens X and drops a stale Y grant", async () => {
    const claims: string[] = [];
    const releases: string[] = [];
    let yRetryGate: { promise: Promise<ExamWorkspaceEditLeaseResponse>; resolve: (value: ExamWorkspaceEditLeaseResponse) => void } | null = null;
    let yClaims = 0;
    apiMocks.claimExamWorkspaceEditLease.mockImplementation(async (lineageId: string) => {
      claims.push(lineageId);
      if (lineageId === Y_LINEAGE) {
        yClaims += 1;
        if (yClaims > 1 && yRetryGate !== null) {
          return yRetryGate.promise;
        }
        throw heldError();
      }
      return leaseResponse("tab-a");
    });
    apiMocks.releaseExamWorkspaceEditLease.mockImplementation(async (lineageId: string) => {
      releases.push(lineageId);
      return leaseResponse("tab-a");
    });
    apiMocks.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
      if (lineageId === Y_LINEAGE) {
        return Promise.resolve(yResponse());
      }
      return Promise.resolve(xResponse());
    });

    const { router, wrapper } = await mountExamWorkspace({ document: X_LINEAGE });
    await settle();

    await router.push({ query: { document: Y_LINEAGE } });
    await settle();
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(Y_TITLE);
    expect(wrapper.find('[data-test="exam-workspace-edit-lease"]').exists()).toBe(true);

    yRetryGate = deferred<ExamWorkspaceEditLeaseResponse>();
    await vi.advanceTimersByTimeAsync(5000);
    await flushPromises();
    expect(claims.filter((lineageId) => lineageId === Y_LINEAGE).length).toBeGreaterThan(1);

    await router.push({ query: { document: X_LINEAGE } });
    await settle();
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(X_TITLE);

    if (yRetryGate !== null) {
      yRetryGate.resolve(leaseResponse("tab-a"));
    }
    await settle();
    await vi.advanceTimersByTimeAsync(6000);
    await settle();

    expect(router.currentRoute.value.query.document).toBe(X_LINEAGE);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(X_TITLE);
    expect(wrapper.find('[data-test="exam-workspace-edit-lease"]').exists()).toBe(false);
    expect(releases).toContain(Y_LINEAGE);
  });

  it("c. a single push to Y with no race still opens Y", async () => {
    apiMocks.claimExamWorkspaceEditLease.mockImplementation(async () => leaseResponse("tab-a"));
    apiMocks.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
      if (lineageId === Y_LINEAGE) {
        return Promise.resolve(yResponse());
      }
      return Promise.resolve(xResponse());
    });

    const { router, wrapper } = await mountExamWorkspace({ document: X_LINEAGE });
    await settle();

    await router.push({ query: { document: Y_LINEAGE } });
    await settle();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith(Y_LINEAGE);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(Y_TITLE);
    expect(router.currentRoute.value.query.document).toBe(Y_LINEAGE);
    expect(wrapper.find('[data-test="exam-workspace-edit-lease"]').exists()).toBe(false);
  });
});
