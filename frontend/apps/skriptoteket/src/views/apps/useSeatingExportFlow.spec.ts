/**
 * Seating export flow tests.
 *
 * These tests cover the frontend-only seating export orchestration so the
 * route shell can stay thin while the happy-path export semantics remain
 * explicit and easy to reason about.
 */

import { reactive } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSeatingExportFlow } from "./useSeatingExportFlow";
import type { SeatingExportJob } from "./classroomPlannerExportApi";
import type { PlanDraft } from "./classroomPlannerTypes";

const exportApiMocks = vi.hoisted(() => ({
  createSeatingExportJob: vi.fn(),
  getRecoverableSeatingExportJob: vi.fn(),
  getSeatingExportJob: vi.fn(),
  downloadSeatingExportJob: vi.fn(),
}));

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
}));

vi.mock("./classroomPlannerExportApi", () => ({
  createSeatingExportJob: exportApiMocks.createSeatingExportJob,
  getRecoverableSeatingExportJob: exportApiMocks.getRecoverableSeatingExportJob,
  getSeatingExportJob: exportApiMocks.getSeatingExportJob,
  downloadSeatingExportJob: exportApiMocks.downloadSeatingExportJob,
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
    draft_kind: "seating",
    template_id: "template-1",
    status: "active",
    revision: 4,
    last_opened_at: "2026-03-24T10:00:00Z",
  };
}

function createPlannerState(overrides?: Partial<PlannerStateMock>): PlannerStateMock {
  return {
    draft: createDraft(),
    prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    ...overrides,
  };
}

function createJob(
  overrides?: Partial<SeatingExportJob>,
): SeatingExportJob {
  return {
    job_id: "job-1",
    draft_id: "draft-1",
    export_kind: "pdf",
    layout_id: "pretty_brutalist_poster",
    paper_size: "a3_landscape",
    status: "submitted",
    created_at: "2026-03-24T10:00:00Z",
    download_url: "/api/v1/apps/classroom.group-seating-studio/exports/jobs/job-1/download",
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

describe("useSeatingExportFlow", () => {
  beforeEach(() => {
    exportApiMocks.createSeatingExportJob.mockReset();
    exportApiMocks.getRecoverableSeatingExportJob.mockReset();
    exportApiMocks.getSeatingExportJob.mockReset();
    exportApiMocks.downloadSeatingExportJob.mockReset();
    toastMocks.success.mockReset();
    window.sessionStorage.clear();
    exportApiMocks.getRecoverableSeatingExportJob.mockResolvedValue(null);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:export");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  it("flushes pending save, exports the default A3 poster, and auto-downloads on success", async () => {
    const plannerState = createPlannerState();
    exportApiMocks.createSeatingExportJob.mockResolvedValue(createJob());
    exportApiMocks.getSeatingExportJob
      .mockResolvedValueOnce(createJob({ status: "processing" }))
      .mockResolvedValueOnce(
        createJob({
          status: "succeeded",
          vault_artifact: {
            file_id: "file-1",
            name: "klassrumskarta-a3.pdf",
            bytes: 1234,
            created_at: "2026-03-24T10:00:05Z",
          },
        }),
      );
    exportApiMocks.downloadSeatingExportJob.mockResolvedValue(new Blob(["pdf"]));

    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 3,
    });

    await flow.startDefaultExport();

    expect(plannerState.prepareForExport).toHaveBeenCalledTimes(1);
    expect(exportApiMocks.createSeatingExportJob).toHaveBeenCalledWith("draft-1", "a3_landscape");
    expect(exportApiMocks.downloadSeatingExportJob).toHaveBeenCalledWith("job-1");
    expect(flow.statusLabel.value).toBeNull();
    expect(flow.errorMessage.value).toBeNull();
    expect(toastMocks.success).toHaveBeenCalledWith(
      "PDF hämtad och sparad i Mina filer. Hämta den där igen vid behov.",
    );
  });

  it("uses the requested paper size for alternate export options", async () => {
    const plannerState = createPlannerState();
    exportApiMocks.createSeatingExportJob.mockResolvedValue(
      createJob({
        paper_size: "a4_landscape",
      }),
    );
    exportApiMocks.getSeatingExportJob.mockResolvedValue(
      createJob({
        paper_size: "a4_landscape",
        status: "succeeded",
        vault_artifact: {
          file_id: "file-2",
          name: "klassrumskarta-a4.pdf",
          bytes: 1234,
          created_at: "2026-03-24T10:00:05Z",
        },
      }),
    );
    exportApiMocks.downloadSeatingExportJob.mockResolvedValue(new Blob(["pdf"]));

    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await flow.startExportOption("a4_landscape");

    expect(exportApiMocks.createSeatingExportJob).toHaveBeenCalledWith("draft-1", "a4_landscape");
  });

  it("exports xlsx with the dedicated status and download messages", async () => {
    const plannerState = createPlannerState();
    exportApiMocks.createSeatingExportJob.mockResolvedValue(
      createJob({
        export_kind: "xlsx",
        layout_id: null,
        paper_size: null,
      }),
    );
    exportApiMocks.getSeatingExportJob.mockResolvedValue(
      createJob({
        export_kind: "xlsx",
        layout_id: null,
        paper_size: null,
        status: "succeeded",
        vault_artifact: {
          file_id: "file-xlsx",
          name: "klass-7a-sittplacering.xlsx",
          bytes: 1234,
          created_at: "2026-03-24T10:00:05Z",
        },
      }),
    );
    exportApiMocks.downloadSeatingExportJob.mockResolvedValue(new Blob(["xlsx"]));

    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await flow.startExportOption("xlsx");

    expect(exportApiMocks.createSeatingExportJob).toHaveBeenCalledWith("draft-1", "xlsx");
    expect(exportApiMocks.downloadSeatingExportJob).toHaveBeenCalledWith("job-1");
    expect(flow.statusLabel.value).toBeNull();
    expect(toastMocks.success).toHaveBeenCalledWith(
      "Excel-filen hämtad och sparad i Mina filer. Hämta den där igen vid behov.",
    );
  });

  it("blocks export when the pending save ends in a conflict", async () => {
    const plannerState = createPlannerState({
      prepareForExport: vi.fn().mockResolvedValue({
        status: "blocked",
        reason: "conflict",
        message: "Lös sparkonflikten innan du exporterar.",
      }),
    });
    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await flow.startDefaultExport();

    expect(exportApiMocks.createSeatingExportJob).not.toHaveBeenCalled();
    expect(flow.errorMessage.value).toBe("Lös sparkonflikten innan du exporterar.");
  });

  it("blocks duplicate export starts while the create-job request is still pending", async () => {
    const flushDeferred = createDeferred<{ status: "saved"; message: null }>();
    const plannerState = createPlannerState({
      prepareForExport: vi.fn().mockReturnValue(flushDeferred.promise),
    });
    const createJobDeferred = createDeferred<SeatingExportJob>();
    exportApiMocks.createSeatingExportJob.mockReturnValue(createJobDeferred.promise);
    exportApiMocks.getSeatingExportJob.mockResolvedValue(
      createJob({
        status: "succeeded",
        vault_artifact: {
          file_id: "file-3",
          name: "klassrumskarta-a3.pdf",
          bytes: 1234,
          created_at: "2026-03-24T10:00:05Z",
        },
      }),
    );
    exportApiMocks.downloadSeatingExportJob.mockResolvedValue(new Blob(["pdf"]));

    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    const firstExportPromise = flow.startDefaultExport();
    const secondExportPromise = flow.startDefaultExport();

    expect(flow.isBusy.value).toBe(true);
    expect(exportApiMocks.createSeatingExportJob).not.toHaveBeenCalled();

    flushDeferred.resolve({ status: "saved", message: null });
    await vi.waitFor(() => {
      expect(exportApiMocks.createSeatingExportJob).toHaveBeenCalledTimes(1);
    });

    createJobDeferred.resolve(createJob());
    await Promise.all([firstExportPromise, secondExportPromise]);
  });

  it("keeps the active job recoverable when the first polling window times out", async () => {
    const plannerState = createPlannerState();
    const deferredCompletion = createDeferred<SeatingExportJob>();
    exportApiMocks.createSeatingExportJob.mockResolvedValue(createJob());
    exportApiMocks.getSeatingExportJob
      .mockResolvedValueOnce(createJob({ status: "processing" }))
      .mockReturnValueOnce(deferredCompletion.promise);
    exportApiMocks.downloadSeatingExportJob.mockResolvedValue(new Blob(["pdf"]));

    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await flow.startDefaultExport();

    expect(flow.isBusy.value).toBe(true);
    expect(flow.statusLabel.value).toBe("Exporten tar längre tid än väntat. Vi fortsätter att kontrollera den.");
    expect(flow.errorMessage.value).toBeNull();
    expect(exportApiMocks.downloadSeatingExportJob).not.toHaveBeenCalled();

    deferredCompletion.resolve(
      createJob({
        status: "succeeded",
        vault_artifact: {
          file_id: "file-4",
          name: "klassrumskarta-a3.pdf",
          bytes: 1234,
          created_at: "2026-03-24T10:00:05Z",
        },
      }),
    );

    await vi.waitFor(() => {
      expect(exportApiMocks.downloadSeatingExportJob).toHaveBeenCalledWith("job-1");
    });
    expect(flow.isBusy.value).toBe(false);
    expect(flow.statusLabel.value).toBeNull();
    expect(toastMocks.success).toHaveBeenCalledWith(
      "PDF hämtad och sparad i Mina filer. Hämta den där igen vid behov.",
    );
  });

  it("rehydrates an in-flight export after reload and announces completion in Mina filer", async () => {
    const plannerState = createPlannerState();
    exportApiMocks.getRecoverableSeatingExportJob.mockResolvedValueOnce(
      createJob({ status: "processing" }),
    );
    exportApiMocks.getSeatingExportJob
      .mockResolvedValueOnce(createJob({ status: "processing" }))
      .mockResolvedValueOnce(
        createJob({
          status: "succeeded",
          vault_artifact: {
            file_id: "file-5",
            name: "klassrumskarta-a3.pdf",
            bytes: 1234,
            created_at: "2026-03-24T10:00:05Z",
          },
        }),
      );

    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await vi.waitFor(() => {
      expect(toastMocks.success).toHaveBeenCalledWith(
        "PDF klar och sparad i Mina filer. Hämta den där igen vid behov.",
      );
    });

    expect(flow.isBusy.value).toBe(false);
    expect(flow.statusLabel.value).toBeNull();
    expect(exportApiMocks.downloadSeatingExportJob).not.toHaveBeenCalled();
  });

  it("rehydrates the latest successful export for the active draft without auto-downloading", async () => {
    const plannerState = createPlannerState();
    exportApiMocks.getRecoverableSeatingExportJob.mockResolvedValueOnce(
      createJob({
        status: "succeeded",
        vault_artifact: {
          file_id: "file-6",
          name: "klassrumskarta-a3.pdf",
          bytes: 1234,
          created_at: "2026-03-24T10:00:05Z",
        },
      }),
    );

    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await Promise.resolve();
    await Promise.resolve();

    expect(flow.isBusy.value).toBe(false);
    expect(flow.statusLabel.value).toBeNull();
    expect(toastMocks.success).not.toHaveBeenCalled();
    expect(exportApiMocks.downloadSeatingExportJob).not.toHaveBeenCalled();
  });

  it("does not leak a recovered export into a different seating draft", async () => {
    const plannerState = reactive(createPlannerState()) as PlannerStateMock;
    const deferredRecoveredCompletion = createDeferred<SeatingExportJob>();
    exportApiMocks.getRecoverableSeatingExportJob
      .mockResolvedValueOnce(createJob({ status: "processing" }))
      .mockResolvedValueOnce(null);
    exportApiMocks.getSeatingExportJob.mockReturnValueOnce(deferredRecoveredCompletion.promise);

    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await vi.waitFor(() => {
      expect(flow.statusLabel.value).toBe("Exporten tar längre tid än väntat. Vi fortsätter att kontrollera den.");
    });

    plannerState.draft = {
      ...createDraft(),
      id: "draft-2",
    };

    await vi.waitFor(() => {
      expect(flow.statusLabel.value).toBeNull();
    });

    deferredRecoveredCompletion.resolve(
      createJob({
        status: "succeeded",
        vault_artifact: {
          file_id: "file-7",
          name: "klassrumskarta-a3.pdf",
          bytes: 1234,
          created_at: "2026-03-24T10:00:05Z",
        },
      }),
    );

    await Promise.resolve();
    await Promise.resolve();

    expect(flow.statusLabel.value).toBeNull();
    expect(exportApiMocks.downloadSeatingExportJob).not.toHaveBeenCalled();
  });

  it("does not re-announce the same recovered export when returning to the same seating draft", async () => {
    const plannerState = reactive(createPlannerState()) as PlannerStateMock;
    const recoveredJob = createJob({
      job_id: "job-8",
      status: "succeeded",
      vault_artifact: {
        file_id: "file-8",
        name: "klassrumskarta-a3.pdf",
        bytes: 1234,
        created_at: "2026-03-24T10:00:05Z",
      },
    });
    exportApiMocks.getRecoverableSeatingExportJob
      .mockResolvedValueOnce(recoveredJob)
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce(recoveredJob);

    const flow = useSeatingExportFlow({
      plannerState,
      pollDelayMs: 0,
      maxPollAttempts: 1,
    });

    await vi.waitFor(() => {
      expect(exportApiMocks.getRecoverableSeatingExportJob).toHaveBeenCalledWith("draft-1");
    });

    plannerState.draft = {
      ...createDraft(),
      id: "draft-2",
    };

    await vi.waitFor(() => {
      expect(exportApiMocks.getRecoverableSeatingExportJob).toHaveBeenCalledWith("draft-2");
    });

    plannerState.draft = createDraft();

    await vi.waitFor(() => {
      expect(exportApiMocks.getRecoverableSeatingExportJob).toHaveBeenNthCalledWith(3, "draft-1");
    });

    expect(flow.statusLabel.value).toBeNull();
    expect(toastMocks.success).not.toHaveBeenCalled();
    expect(exportApiMocks.downloadSeatingExportJob).not.toHaveBeenCalled();
  });
});
