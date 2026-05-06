/**
 * Public guest share-link flow tests.
 *
 * These tests lock the browser-held metadata contract for PR-0273 so guest
 * share links can supersede across snapshot edits and retry transport failures
 * with the same client operation.
 */

import { nextTick, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { createClassroomPlannerGuestSnapshotFromSeed } from "./classroomPlannerGuestSnapshotMapping";
import { createClassroomPlannerPublicShareFlow } from "./classroomPlannerPublicShareFlow";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { PlanDraft } from "./classroomPlannerTypes";

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
  warning: vi.fn(),
  failure: vi.fn(),
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

function createSnapshot(snapshotContentHash: string): ClassroomPlannerGuestSnapshot {
  const snapshot = createClassroomPlannerGuestSnapshotFromSeed({
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
      draft: createDraft(),
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
      group_assignments: [{ student_id: "ada", group_id: "group-a" }],
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
  return {
    ...snapshot,
    snapshot_content_hash: snapshotContentHash,
  };
}

function createdShare(publicPath: string, revokeSecret: string) {
  return {
    artifact: {
      id: "share-1",
      title: "Klass 7A",
      draft_kind: "grouping",
      source: "public_guest",
      source_revision: 4,
      slug: "klass-7a",
      public_path: publicPath,
      public_url: `https://skriptoteket.hule.education${publicPath}`,
      preview_description: "Frozen grouping plan",
      renderer_version: "klassrumskartan-share-renderer-v1",
      presentation_schema_version: "grouping-share-v1",
      content_hash: "sha256:content",
      presentation_hash: "sha256:presentation",
      created_at: "2026-04-30T10:00:00Z",
      updated_at: "2026-04-30T10:00:00Z",
      revoked_at: null,
      expires_at: "2026-06-29T10:00:00Z",
    },
    public_path: publicPath,
    public_url: `https://skriptoteket.hule.education${publicPath}`,
    public_revoke_secret: revokeSecret,
    superseded_previous: false,
    reused_client_operation: false,
  };
}

describe("createClassroomPlannerPublicShareFlow", () => {
  beforeEach(() => {
    localStorage.clear();
    toastMocks.success.mockReset();
    toastMocks.warning.mockReset();
    toastMocks.failure.mockReset();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("sends previous guest share metadata after snapshot content changes", async () => {
    let snapshot = createSnapshot("sha256:first");
    const createShare = vi
      .fn()
      .mockResolvedValueOnce(createdShare("/share/classroom/first/klass-7a", "first-secret"))
      .mockResolvedValueOnce(createdShare("/share/classroom/second/klass-7a", "second-secret"));
    const flow = createClassroomPlannerPublicShareFlow({
      plannerState: {
        draft: createDraft(),
        prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      },
      getSnapshot: vi.fn(async () => snapshot),
      draftKind: "grouping",
      createShare,
      revokeShare: vi.fn(),
      messages: {
        missingDraftMessage: "missing",
        initialStatusLabel: "sharing",
        copiedMessage: "copied",
        revokedMessage: "revoked",
        fallbackMessage: "failed",
        revokeFallbackMessage: "revoke failed",
      },
    });

    await flow.startShare();
    snapshot = createSnapshot("sha256:edited");
    await flow.startShare();

    expect(createShare).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        previousPublicPath: "/share/classroom/first/klass-7a",
        previousRevokeSecret: "first-secret",
      }),
    );
  });

  it("reuses a pending client operation after a transport failure", async () => {
    const createShare = vi
      .fn()
      .mockRejectedValueOnce(
        new ApiError({
          code: "HTTP_ERROR",
          message: "network failed",
          status: 503,
        }),
      )
      .mockResolvedValueOnce(createdShare("/share/classroom/retry/klass-7a", "retry-secret"));
    const flow = createClassroomPlannerPublicShareFlow({
      plannerState: {
        draft: createDraft(),
        prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      },
      getSnapshot: vi.fn(async () => createSnapshot("sha256:first")),
      draftKind: "grouping",
      createShare,
      revokeShare: vi.fn(),
      messages: {
        missingDraftMessage: "missing",
        initialStatusLabel: "sharing",
        copiedMessage: "copied",
        revokedMessage: "revoked",
        fallbackMessage: "failed",
        revokeFallbackMessage: "revoke failed",
      },
    });

    await flow.startShare();
    await flow.startShare();

    const firstCall = createShare.mock.calls[0]?.[0];
    const secondCall = createShare.mock.calls[1]?.[0];
    expect(secondCall?.clientOperationId).toBe(firstCall?.clientOperationId);
    expect(secondCall?.revokeSecret).toBe(firstCall?.revokeSecret);
    expect(Object.keys(localStorage).some((key) => key.includes(":pending:"))).toBe(false);
  });

  it("shows a created share and revokes it with browser-held metadata", async () => {
    const createShare = vi
      .fn()
      .mockResolvedValue(createdShare("/share/classroom/current/klass-7a", "current-secret"));
    const revokeShare = vi.fn().mockResolvedValue({
      artifact: {
        ...createdShare("/share/classroom/current/klass-7a", "current-secret").artifact,
        revoked_at: "2026-04-30T11:00:00Z",
      },
      public_path: "/share/classroom/current/klass-7a",
      public_url: "https://skriptoteket.hule.education/share/classroom/current/klass-7a",
    });
    const flow = createClassroomPlannerPublicShareFlow({
      plannerState: {
        draft: createDraft(),
        prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      },
      getSnapshot: vi.fn(async () => createSnapshot("sha256:first")),
      draftKind: "grouping",
      createShare,
      revokeShare,
      messages: {
        missingDraftMessage: "missing",
        initialStatusLabel: "sharing",
        copiedMessage: "copied",
        revokedMessage: "revoked",
        fallbackMessage: "failed",
        revokeFallbackMessage: "revoke failed",
      },
    });

    await flow.startShare();
    expect(flow.shares.value).toHaveLength(1);
    const currentShare = flow.shares.value[0];
    expect(currentShare).toBeDefined();

    await flow.revokePublicShare(currentShare!);

    expect(revokeShare).toHaveBeenCalledWith({
      publicPath: "/share/classroom/current/klass-7a",
      revokeSecret: "current-secret",
    });
    expect(flow.shares.value).toEqual([]);
    expect(toastMocks.success).toHaveBeenLastCalledWith("revoked");
  });

  it("hydrates and revokes the browser-owned share after a reload", async () => {
    const createShare = vi
      .fn()
      .mockResolvedValue(createdShare("/share/classroom/current/klass-7a", "current-secret"));
    const snapshot = createSnapshot("sha256:first");
    const firstFlow = createClassroomPlannerPublicShareFlow({
      plannerState: {
        draft: createDraft(),
        prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      },
      getSnapshot: vi.fn(async () => snapshot),
      draftKind: "grouping",
      createShare,
      revokeShare: vi.fn(),
      messages: {
        missingDraftMessage: "missing",
        initialStatusLabel: "sharing",
        copiedMessage: "copied",
        revokedMessage: "revoked",
        fallbackMessage: "failed",
        revokeFallbackMessage: "revoke failed",
      },
    });
    await firstFlow.startShare();

    const revokeShare = vi.fn().mockResolvedValue({
      artifact: {
        ...createdShare("/share/classroom/current/klass-7a", "current-secret").artifact,
        revoked_at: "2026-04-30T11:00:00Z",
      },
      public_path: "/share/classroom/current/klass-7a",
      public_url: "https://skriptoteket.hule.education/share/classroom/current/klass-7a",
    });
    const reloadedFlow = createClassroomPlannerPublicShareFlow({
      plannerState: {
        draft: createDraft(),
        prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      },
      getSnapshot: vi.fn(async () => snapshot),
      draftKind: "grouping",
      createShare: vi.fn(),
      revokeShare,
      messages: {
        missingDraftMessage: "missing",
        initialStatusLabel: "sharing",
        copiedMessage: "copied",
        revokedMessage: "revoked",
        fallbackMessage: "failed",
        revokeFallbackMessage: "revoke failed",
      },
    });

    await vi.waitFor(() => {
      expect(reloadedFlow.shares.value).toHaveLength(1);
    });

    await reloadedFlow.revokePublicShare(reloadedFlow.shares.value[0]!);

    expect(revokeShare).toHaveBeenCalledWith({
      publicPath: "/share/classroom/current/klass-7a",
      revokeSecret: "current-secret",
    });
    expect(reloadedFlow.shares.value).toEqual([]);
    expect(Object.keys(localStorage).some((key) => key.includes("public-share"))).toBe(false);
  });

  it("hydrates browser-owned share metadata when the draft appears after overview preparation", async () => {
    const snapshot = createSnapshot("sha256:first");
    const createShare = vi
      .fn()
      .mockResolvedValue(createdShare("/share/classroom/current/klass-7a", "current-secret"));
    const firstFlow = createClassroomPlannerPublicShareFlow({
      plannerState: {
        draft: createDraft(),
        prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      },
      getSnapshot: vi.fn(async () => snapshot),
      draftKind: "grouping",
      createShare,
      revokeShare: vi.fn(),
      messages: {
        missingDraftMessage: "missing",
        initialStatusLabel: "sharing",
        copiedMessage: "copied",
        revokedMessage: "revoked",
        fallbackMessage: "failed",
        revokeFallbackMessage: "revoke failed",
      },
    });
    await firstFlow.startShare();

    const lateDraft = ref<PlanDraft | null>(null);
    const reloadedFlow = createClassroomPlannerPublicShareFlow({
      plannerState: {
        draft: lateDraft,
        prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      },
      getSnapshot: vi.fn(async () => snapshot),
      draftKind: "grouping",
      createShare: vi.fn(),
      revokeShare: vi.fn(),
      messages: {
        missingDraftMessage: "missing",
        initialStatusLabel: "sharing",
        copiedMessage: "copied",
        revokedMessage: "revoked",
        fallbackMessage: "failed",
        revokeFallbackMessage: "revoke failed",
      },
    });

    expect(reloadedFlow.shares.value).toEqual([]);

    lateDraft.value = createDraft();
    await nextTick();

    await vi.waitFor(() => {
      expect(reloadedFlow.shares.value).toHaveLength(1);
    });
    expect(reloadedFlow.shares.value[0]?.public_path).toBe("/share/classroom/current/klass-7a");
  });
});
