/**
 * Grouping export flow tests.
 *
 * These tests cover the frontend-only grouping export orchestration so the
 * route shell can stay thin while grouping export creation, polling, and
 * reload recovery remain explicit and safe.
 */

import { reactive } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useGroupingExportFlow } from "./useGroupingExportFlow";
import type { GroupingExportJob } from "./classroomPlannerExportApi";
import type { PlanDraft } from "./classroomPlannerTypes";

const exportApiMocks = vi.hoisted(() => ({
  createGroupingExportJob: vi.fn(),
  getGroupingExportJob: vi.fn(),
  getRecoverableGroupingExportJob: vi.fn(),
  downloadGroupingExportJob: vi.fn(),
}));

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
}));

vi.mock("./classroomPlannerExportApi", () => ({
  createGroupingExportJob: exportApiMocks.createGroupingExportJob,
  getGroupingExportJob: exportApiMocks.getGroupingExportJob,
  getRecoverableGroupingExportJob: exportApiMocks.getRecoverableGroupingExportJob,
  downloadGroupingExportJob: exportApiMocks.downloadGroupingExportJob,
}));

vi.mock("../../composables/useToast", () => ({
  useToast: () => toastMocks,
}));

type PlannerStateMock = {
  draft: PlanDraft | null;
  prepareForExport: () => Promise<{ status: "saved"; message: null } | { status: "blocked"; reason: "conflict" | "error"; message: string }>;
};

function createDraft(): PlanDraft {
  return {
    id: "draft-1",
    roster_id: "roster-1",
    draft_kind: "grouping",
    template_id: "template-1",
    status: "active",
    revision: 4,
    last_opened_at: "2026-03-26T10:00:00Z",
  };
}

function createPlannerState(overrides?: Partial<PlannerStateMock>): PlannerStateMock {
  return {
    draft: createDraft(),
    prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    ...overrides,
  };
}

function createJob(overrides?: Partial<GroupingExportJob>): GroupingExportJob {
  return {
    job_id: "job-1",
    draft_id: "draft-1",
    export_kind: "xlsx",
    paper_size: null,
    status: "submitted",
    created_at: "2026-03-26T10:00:00Z",
    download_url: null,
    vault_artifact: null,
    error: null,
    ...overrides,
  };
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("useGroupingExportFlow", () => {
  beforeEach(() => {
    exportApiMocks.createGroupingExportJob.mockReset();
    exportApiMocks.getGroupingExportJob.mockReset();
    exportApiMocks.getRecoverableGroupingExportJob.mockReset();
    exportApiMocks.downloadGroupingExportJob.mockReset();
    toastMocks.success.mockReset();
    exportApiMocks.getRecoverableGroupingExportJob.mockResolvedValue(null);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:export");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  it("flushes pending save and starts the default grouping xlsx export", async () => {
    const plannerState = createPlannerState();
    exportApiMocks.createGroupingExportJob.mockResolvedValue(createJob());
    exportApiMocks.getGroupingExportJob
      .mockResolvedValueOnce(createJob({ status: "processing" }))
      .mockResolvedValueOnce(
        createJob({
          status: "succeeded",
          vault_artifact: {
            file_id: "file-1",
            name: "klass-7a-gruppindelning.xlsx",
            bytes: 1234,
            created_at: "2026-03-26T10:00:05Z",
          },
          download_url: "/api/v1/apps/classroom.group-seating-studio/grouping/exports/jobs/job-1/download",
        }),
      );
    exportApiMocks.downloadGroupingExportJob.mockResolvedValue(new Blob(["xlsx"]));

    const flow = useGroupingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 3,
    });

    await flow.startDefaultExport();

    expect(plannerState.prepareForExport).toHaveBeenCalledTimes(1);
    expect(exportApiMocks.createGroupingExportJob).toHaveBeenCalledWith("draft-1", "xlsx");
    expect(exportApiMocks.downloadGroupingExportJob).toHaveBeenCalledWith("job-1");
    expect(flow.statusLabel.value).toBe("Excel-filen hämtad och sparad i Mina filer.");
    expect(flow.errorMessage.value).toBeNull();
    expect(flow.canDownloadLatest.value).toBe(true);
  });

  it("starts the requested pdf option with the locked a4 portrait contract", async () => {
    const plannerState = createPlannerState();
    exportApiMocks.createGroupingExportJob.mockResolvedValue(
      createJob({
        export_kind: "pdf",
        paper_size: "a4_portrait",
      }),
    );
    exportApiMocks.getGroupingExportJob.mockResolvedValue(
      createJob({
        export_kind: "pdf",
        paper_size: "a4_portrait",
        status: "succeeded",
        vault_artifact: {
          file_id: "file-2",
          name: "klass-7a-gruppindelning.pdf",
          bytes: 1234,
          created_at: "2026-03-26T10:00:05Z",
        },
        download_url: "/api/v1/apps/classroom.group-seating-studio/grouping/exports/jobs/job-1/download",
      }),
    );
    exportApiMocks.downloadGroupingExportJob.mockResolvedValue(new Blob(["pdf"]));

    const flow = useGroupingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await flow.startExportOption("pdf_a4_portrait");

    expect(exportApiMocks.createGroupingExportJob).toHaveBeenCalledWith("draft-1", "pdf_a4_portrait");
  });

  it("recovers an in-flight grouping export after draft reload", async () => {
    const plannerState = reactive(createPlannerState());
    exportApiMocks.getRecoverableGroupingExportJob.mockResolvedValue(
      createJob({
        job_id: "job-recover",
        export_kind: "pdf",
        paper_size: "a4_portrait",
        status: "processing",
      }),
    );

    useGroupingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await Promise.resolve();

    expect(exportApiMocks.getRecoverableGroupingExportJob).toHaveBeenCalledWith("draft-1");
  });

  it("blocks duplicate export starts while the create-job request is pending", async () => {
    const flushDeferred = createDeferred<{ status: "saved"; message: null }>();
    const plannerState = createPlannerState({
      prepareForExport: vi.fn().mockReturnValue(flushDeferred.promise),
    });
    const createJobDeferred = createDeferred<GroupingExportJob>();
    exportApiMocks.createGroupingExportJob.mockReturnValue(createJobDeferred.promise);
    exportApiMocks.getGroupingExportJob.mockResolvedValue(
      createJob({
        status: "succeeded",
        vault_artifact: {
          file_id: "file-3",
          name: "klass-7a-gruppindelning.xlsx",
          bytes: 1234,
          created_at: "2026-03-26T10:00:05Z",
        },
      }),
    );
    exportApiMocks.downloadGroupingExportJob.mockResolvedValue(new Blob(["xlsx"]));

    const flow = useGroupingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    const firstExportPromise = flow.startDefaultExport();
    const secondExportPromise = flow.startDefaultExport();

    expect(flow.isBusy.value).toBe(true);
    expect(exportApiMocks.createGroupingExportJob).not.toHaveBeenCalled();

    flushDeferred.resolve({ status: "saved", message: null });
    await Promise.resolve();
    createJobDeferred.resolve(createJob());

    await Promise.all([firstExportPromise, secondExportPromise]);

    expect(exportApiMocks.createGroupingExportJob).toHaveBeenCalledTimes(1);
  });

  it("blocks export when the pending save ends in a conflict", async () => {
    const plannerState = createPlannerState({
      prepareForExport: vi.fn().mockResolvedValue({
        status: "blocked",
        reason: "conflict",
        message: "Lös sparkonflikten innan du exporterar.",
      }),
    });
    const flow = useGroupingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await flow.startDefaultExport();

    expect(exportApiMocks.createGroupingExportJob).not.toHaveBeenCalled();
    expect(flow.errorMessage.value).toBe("Lös sparkonflikten innan du exporterar.");
  });
});
