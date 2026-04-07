/**
 * Public seating export flow tests.
 *
 * These tests cover the guest direct-download seating export seam so the
 * public planner can flush the snapshot, download the artifact, and record a
 * deduped export checkpoint in browser storage.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { createClassroomPlannerGuestSnapshotFromSeed } from "./classroomPlannerGuestSnapshotMapping";
import { usePublicSeatingExportFlow } from "./usePublicSeatingExportFlow";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { PlanDraft } from "./classroomPlannerTypes";

const exportApiMocks = vi.hoisted(() => ({
  exportPublicSeatingSnapshot: vi.fn(),
}));

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
  warning: vi.fn(),
}));

vi.mock("./classroomPlannerPublicExportApi", () => ({
  exportPublicSeatingSnapshot: exportApiMocks.exportPublicSeatingSnapshot,
}));

vi.mock("../../composables/useToast", () => ({
  useToast: () => toastMocks,
}));

function createDraft(): PlanDraft {
  return {
    id: "seating-draft-1",
    roster_id: "roster-1",
    draft_kind: "seating",
    template_id: "template-1",
    status: "active",
    revision: 2,
    last_opened_at: "2026-04-07T10:00:00Z",
  };
}

function createSnapshot(input?: {
  draftId?: string;
  seatAssignments?: Array<{ student_id: string; seat_id: string }>;
}): ClassroomPlannerGuestSnapshot {
  return createClassroomPlannerGuestSnapshotFromSeed({
    snapshot_id: "guest-snapshot-1",
    created_at: "2026-04-07T09:00:00Z",
    updated_at: "2026-04-07T10:00:00Z",
    expires_at: "2026-04-21T10:00:00Z",
    rosters: [
      {
        id: "roster-1",
        name: "SA24D",
        students: [
          { id: "ada", display_name: "Ada" },
          { id: "alan", display_name: "Alan" },
        ],
      },
    ],
    templates: [
      {
        id: "template-1",
        name: "Sal 101",
        grid_cols: 4,
        grid_rows: 4,
        seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
        fixtures: [],
      },
    ],
    smart_rule_sets: [],
    grouping_draft: null,
    seating_draft: {
      draft: {
        ...createDraft(),
        id: input?.draftId ?? createDraft().id,
      },
      roster: {
        id: "roster-1",
        name: "SA24D",
        students: [
          { id: "ada", display_name: "Ada" },
          { id: "alan", display_name: "Alan" },
        ],
      },
      template: {
        id: "template-1",
        name: "Sal 101",
        grid_cols: 4,
        grid_rows: 4,
        seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
        fixtures: [],
      },
      groups: [],
      group_assignments: [],
      seat_assignments: input?.seatAssignments ?? [{ student_id: "alan", seat_id: "seat-1" }],
      history_status: { can_undo: false, can_redo: false },
    },
    checkpoint_descriptors: [],
    ui_state: {
      selected_roster_id: "roster-1",
      selected_template_id: "template-1",
      current_screen: "planner",
      planner_initial_view: "seats",
      dismissed_grouping_draft_id: null,
      dismissed_seating_draft_id: null,
    },
  });
}

function createDeferredExportResult() {
  let resolve: ((value: {
    blob: Blob;
    filename: string;
    mediaType: string;
  }) => void) | null = null;
  const promise = new Promise<{
    blob: Blob;
    filename: string;
    mediaType: string;
  }>((nextResolve) => {
    resolve = nextResolve;
  });
  return {
    promise,
    resolve(value: {
      blob: Blob;
      filename: string;
      mediaType: string;
    }) {
      resolve?.(value);
    },
  };
}

describe("usePublicSeatingExportFlow", () => {
  beforeEach(() => {
    exportApiMocks.exportPublicSeatingSnapshot.mockReset();
    toastMocks.success.mockReset();
    toastMocks.warning.mockReset();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:public-seating-export");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  it("exports the current guest seating draft and records one checkpoint", async () => {
    let snapshot = createSnapshot();
    const initialSnapshot = snapshot;
    const plannerState = {
      draft: createDraft(),
      prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    };
    exportApiMocks.exportPublicSeatingSnapshot.mockResolvedValue({
      blob: new Blob(["pdf"]),
      filename: "klassrumskarta-a3-landscape.pdf",
      mediaType: "application/pdf",
    });

    const flow = usePublicSeatingExportFlow({
      plannerState,
      getSnapshot: vi.fn(async () => snapshot),
      persistSnapshotMutation: vi.fn(async ({ mutate }) => {
        const result = mutate(snapshot, "2026-04-07T10:05:00Z");
        snapshot = result.nextSnapshot;
        return result.result;
      }),
    });

    await flow.startDefaultExport();

    expect(plannerState.prepareForExport).toHaveBeenCalledTimes(1);
    expect(exportApiMocks.exportPublicSeatingSnapshot).toHaveBeenCalledWith(
      initialSnapshot,
      2,
      "a3_landscape",
    );
    expect(snapshot.checkpoint_descriptors).toHaveLength(1);
    expect(snapshot.checkpoint_descriptors[0]?.draft_kind).toBe("seating");
    expect(snapshot.checkpoint_descriptors[0]?.source).toBe("export");
    expect(toastMocks.success).toHaveBeenCalledWith(
      "PDF-filen hämtades och exportcheckpointen sparades i den här webbläsaren.",
    );
    expect(flow.errorMessage.value).toBeNull();
  });

  it("dedupes repeated exports of the same seating snapshot fingerprint", async () => {
    let snapshot = createSnapshot();
    const plannerState = {
      draft: createDraft(),
      prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    };
    exportApiMocks.exportPublicSeatingSnapshot.mockResolvedValue({
      blob: new Blob(["pdf"]),
      filename: "klassrumskarta-a3-landscape.pdf",
      mediaType: "application/pdf",
    });

    const flow = usePublicSeatingExportFlow({
      plannerState,
      getSnapshot: vi.fn(async () => snapshot),
      persistSnapshotMutation: vi.fn(async ({ mutate }) => {
        const result = mutate(snapshot, "2026-04-07T10:05:00Z");
        snapshot = result.nextSnapshot;
        return result.result;
      }),
    });

    await flow.startDefaultExport();
    await flow.startDefaultExport();

    expect(snapshot.checkpoint_descriptors).toHaveLength(1);
  });

  it("persists the checkpoint from the exported snapshot even if the seating draft mutates in flight", async () => {
    let snapshot = createSnapshot();
    const plannerState = {
      draft: createDraft(),
      prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    };
    const deferred = createDeferredExportResult();
    exportApiMocks.exportPublicSeatingSnapshot.mockReturnValue(deferred.promise);

    const flow = usePublicSeatingExportFlow({
      plannerState,
      getSnapshot: vi.fn(async () => snapshot),
      persistSnapshotMutation: vi.fn(async ({ mutate }) => {
        const result = mutate(snapshot, "2026-04-07T10:05:00Z");
        snapshot = result.nextSnapshot;
        return result.result;
      }),
    });

    const exportPromise = flow.startDefaultExport();
    await vi.waitFor(() => {
      expect(exportApiMocks.exportPublicSeatingSnapshot).toHaveBeenCalledTimes(1);
    });

    snapshot = createSnapshot({
      seatAssignments: [{ student_id: "ada", seat_id: "seat-1" }],
    });

    deferred.resolve({
      blob: new Blob(["pdf"]),
      filename: "klassrumskarta-a3-landscape.pdf",
      mediaType: "application/pdf",
    });
    await exportPromise;

    expect(snapshot.checkpoint_descriptors).toHaveLength(1);
    expect(snapshot.checkpoint_descriptors[0]?.seat_assignments).toEqual([
      { student_id: "alan", seat_id: "seat-1" },
    ]);
  });

  it("keeps writing the exported checkpoint if the active seating draft changes before export resolves", async () => {
    let snapshot = createSnapshot();
    const plannerState = {
      draft: createDraft(),
      prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    };
    const deferred = createDeferredExportResult();
    exportApiMocks.exportPublicSeatingSnapshot.mockReturnValue(deferred.promise);

    const flow = usePublicSeatingExportFlow({
      plannerState,
      getSnapshot: vi.fn(async () => snapshot),
      persistSnapshotMutation: vi.fn(async ({ mutate }) => {
        const result = mutate(snapshot, "2026-04-07T10:05:00Z");
        snapshot = result.nextSnapshot;
        return result.result;
      }),
    });

    const exportPromise = flow.startDefaultExport();
    await vi.waitFor(() => {
      expect(exportApiMocks.exportPublicSeatingSnapshot).toHaveBeenCalledTimes(1);
    });

    plannerState.draft = {
      ...createDraft(),
      id: "seating-draft-2",
    };
    snapshot = createSnapshot({
      draftId: "seating-draft-2",
      seatAssignments: [{ student_id: "ada", seat_id: "seat-1" }],
    });

    deferred.resolve({
      blob: new Blob(["pdf"]),
      filename: "klassrumskarta-a3-landscape.pdf",
      mediaType: "application/pdf",
    });
    await exportPromise;

    expect(snapshot.checkpoint_descriptors).toHaveLength(1);
    expect(snapshot.checkpoint_descriptors[0]?.seat_assignments).toEqual([
      { student_id: "alan", seat_id: "seat-1" },
    ]);
  });
});
