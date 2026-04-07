/**
 * Public grouping export flow tests.
 *
 * These tests cover the guest direct-download grouping export seam so the
 * public planner can flush the snapshot, download the artifact, and record a
 * deduped export checkpoint in browser storage.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { createClassroomPlannerGuestSnapshotFromSeed } from "./classroomPlannerGuestSnapshotMapping";
import { usePublicGroupingExportFlow } from "./usePublicGroupingExportFlow";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { PlanDraft } from "./classroomPlannerTypes";

const exportApiMocks = vi.hoisted(() => ({
  exportPublicGroupingSnapshot: vi.fn(),
}));

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
  warning: vi.fn(),
}));

vi.mock("./classroomPlannerPublicExportApi", () => ({
  exportPublicGroupingSnapshot: exportApiMocks.exportPublicGroupingSnapshot,
}));

vi.mock("../../composables/useToast", () => ({
  useToast: () => toastMocks,
}));

function createDraft(): PlanDraft {
  return {
    id: "grouping-draft-1",
    roster_id: "roster-1",
    draft_kind: "grouping",
    template_id: "template-1",
    status: "active",
    revision: 4,
    last_opened_at: "2026-04-07T10:00:00Z",
  };
}

function createSnapshot(input?: {
  draftId?: string;
  groupAssignments?: Array<{ student_id: string; group_id: string }>;
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
    grouping_draft: {
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
      groups: [{ id: "group-a", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
      group_assignments: input?.groupAssignments ?? [{ student_id: "ada", group_id: "group-a" }],
      seat_assignments: [],
      history_status: { can_undo: false, can_redo: false },
    },
    seating_draft: null,
    checkpoint_descriptors: [],
    ui_state: {
      selected_roster_id: "roster-1",
      selected_template_id: "template-1",
      current_screen: "planner",
      planner_initial_view: "groups",
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

describe("usePublicGroupingExportFlow", () => {
  beforeEach(() => {
    exportApiMocks.exportPublicGroupingSnapshot.mockReset();
    toastMocks.success.mockReset();
    toastMocks.warning.mockReset();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:public-export");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  it("exports the current guest grouping draft and records one checkpoint", async () => {
    let snapshot = createSnapshot();
    const initialSnapshot = snapshot;
    const plannerState = {
      draft: createDraft(),
      prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    };
    exportApiMocks.exportPublicGroupingSnapshot.mockResolvedValue({
      blob: new Blob(["xlsx"]),
      filename: "gruppindelning.xlsx",
      mediaType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    const flow = usePublicGroupingExportFlow({
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
    expect(exportApiMocks.exportPublicGroupingSnapshot).toHaveBeenCalledWith(
      initialSnapshot,
      4,
      "xlsx",
    );
    expect(snapshot.checkpoint_descriptors).toHaveLength(1);
    expect(snapshot.checkpoint_descriptors[0]?.source).toBe("export");
    expect(toastMocks.success).toHaveBeenCalledWith(
      "Excel-filen hämtades och exportcheckpointen sparades i den här webbläsaren.",
    );
    expect(flow.errorMessage.value).toBeNull();
  });

  it("dedupes repeated exports of the same grouping snapshot fingerprint", async () => {
    let snapshot = createSnapshot();
    const plannerState = {
      draft: createDraft(),
      prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    };
    exportApiMocks.exportPublicGroupingSnapshot.mockResolvedValue({
      blob: new Blob(["xlsx"]),
      filename: "gruppindelning.xlsx",
      mediaType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    const flow = usePublicGroupingExportFlow({
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

  it("persists the checkpoint from the exported snapshot even if the draft mutates in flight", async () => {
    let snapshot = createSnapshot();
    const plannerState = {
      draft: createDraft(),
      prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    };
    const deferred = createDeferredExportResult();
    exportApiMocks.exportPublicGroupingSnapshot.mockReturnValue(deferred.promise);

    const flow = usePublicGroupingExportFlow({
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
      expect(exportApiMocks.exportPublicGroupingSnapshot).toHaveBeenCalledTimes(1);
    });

    snapshot = createSnapshot({
      groupAssignments: [{ student_id: "alan", group_id: "group-a" }],
    });

    deferred.resolve({
      blob: new Blob(["xlsx"]),
      filename: "gruppindelning.xlsx",
      mediaType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    await exportPromise;

    expect(snapshot.checkpoint_descriptors).toHaveLength(1);
    expect(snapshot.checkpoint_descriptors[0]?.group_assignments).toEqual([
      { student_id: "ada", group_id: "group-a" },
    ]);
  });

  it("keeps writing the exported checkpoint if the active draft changes before export resolves", async () => {
    let snapshot = createSnapshot();
    const plannerState = {
      draft: createDraft(),
      prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    };
    const deferred = createDeferredExportResult();
    exportApiMocks.exportPublicGroupingSnapshot.mockReturnValue(deferred.promise);

    const flow = usePublicGroupingExportFlow({
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
      expect(exportApiMocks.exportPublicGroupingSnapshot).toHaveBeenCalledTimes(1);
    });

    plannerState.draft = {
      ...createDraft(),
      id: "grouping-draft-2",
    };
    snapshot = createSnapshot({
      draftId: "grouping-draft-2",
      groupAssignments: [{ student_id: "alan", group_id: "group-a" }],
    });

    deferred.resolve({
      blob: new Blob(["xlsx"]),
      filename: "gruppindelning.xlsx",
      mediaType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    await exportPromise;

    expect(snapshot.checkpoint_descriptors).toHaveLength(1);
    expect(snapshot.checkpoint_descriptors[0]?.group_assignments).toEqual([
      { student_id: "ada", group_id: "group-a" },
    ]);
  });
});
