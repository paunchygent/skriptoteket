/**
 * Classroom planner share-flow tests.
 *
 * These tests lock the authenticated Dela länk orchestration around the
 * reviewed PR-0274 contract: export preparation runs first, the post-flush
 * revision is sent, and owned share links remain copyable/revocable.
 */

import { createPinia, setActivePinia } from "pinia";
import { reactive, nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PlanDraft } from "./classroomPlannerTypes";
import type { ClassroomPlannerShareArtifact } from "./classroomPlannerShareApi";
import { createClassroomPlannerShareFlow } from "./classroomPlannerShareFlow";

function makeDraft(revision: number): PlanDraft {
  return {
    id: "draft-1",
    roster_id: "roster-1",
    draft_kind: "grouping",
    status: "active",
    revision,
    last_opened_at: "2026-04-30T10:00:00Z",
  };
}

function makeShare(params: {
  id: string;
  publicUrl: string | null;
  revokedAt?: string | null;
}): ClassroomPlannerShareArtifact {
  return {
    id: params.id,
    source: "authenticated",
    draft_kind: "grouping",
    draft_id: "draft-1",
    roster_id: "roster-1",
    template_id: null,
    source_revision: 8,
    title: "Klass 7A",
    slug: "klass-7a",
    public_path: params.publicUrl ? "/share/classroom/public-token/klass-7a" : null,
    public_url: params.publicUrl,
    preview_description: null,
    renderer_version: "klassrumskartan-share-renderer-v1",
    presentation_schema_version: "grouping-share-v1",
    presentation_hash: "sha256:presentation",
    content_hash: "sha256:content",
    created_at: "2026-04-30T10:00:00Z",
    updated_at: "2026-04-30T10:00:00Z",
    revoked_at: params.revokedAt ?? null,
    expires_at: null,
  };
}

async function flushPromises(): Promise<void> {
  for (let attempt = 0; attempt < 4; attempt += 1) {
    await Promise.resolve();
    await nextTick();
  }
}

describe("createClassroomPlannerShareFlow", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("prepares the draft and sends the post-flush revision before copying the link", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const state = reactive({
      draft: makeDraft(7),
      prepareForExport: vi.fn().mockImplementation(async () => {
        state.draft = makeDraft(8);
        return { status: "saved", message: null };
      }),
    });
    const createdShare = makeShare({
      id: "share-1",
      publicUrl: "https://skriptoteket.hule.education/share/classroom/public-token/klass-7a",
    });
    const createShare = vi.fn().mockResolvedValue({
      artifact: createdShare,
      public_path: "/share/classroom/public-token/klass-7a",
      public_url: createdShare.public_url,
    });
    const listShares = vi.fn().mockResolvedValue([]);
    const revokeShare = vi.fn().mockResolvedValue(createdShare);

    const flow = createClassroomPlannerShareFlow({
      plannerState: state,
      draftKind: "grouping",
      createShare,
      listShares,
      revokeShare,
      messages: {
        missingDraftMessage: "missing",
        scopeChangedMessage: "changed",
        initialStatusLabel: "Skapar delningslänk…",
        copiedMessage: "copied",
        createFallbackMessage: "create failed",
        listFallbackMessage: "list failed",
        revokeFallbackMessage: "revoke failed",
        copyUnavailableMessage: "copy unavailable",
      },
    });
    await flushPromises();

    await flow.startShare();

    expect(state.prepareForExport).toHaveBeenCalledWith({
      conflictMessage: "Lös sparkonflikten innan du delar länken.",
      fallbackMessage: "Kunde inte spara ändringarna innan delning.",
    });
    expect(createShare).toHaveBeenCalledWith({
      draftId: "draft-1",
      expectedRevision: 8,
    });
    expect(writeText).toHaveBeenCalledWith(createdShare.public_url);
    expect(flow.shares.value).toEqual([createdShare]);
  });

  it("copies and revokes listed owned shares", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const listedShare = makeShare({
      id: "share-2",
      publicUrl: "https://skriptoteket.hule.education/share/classroom/listed-token/klass-7a",
    });
    const revokedShare = makeShare({
      id: "share-2",
      publicUrl: listedShare.public_url,
      revokedAt: "2026-04-30T11:00:00Z",
    });
    const state = reactive({
      draft: makeDraft(3),
      prepareForExport: vi.fn().mockResolvedValue({ status: "saved", message: null }),
    });
    const revokeShare = vi.fn().mockResolvedValue(revokedShare);
    const flow = createClassroomPlannerShareFlow({
      plannerState: state,
      draftKind: "grouping",
      createShare: vi.fn(),
      listShares: vi.fn().mockResolvedValue([listedShare]),
      revokeShare,
      messages: {
        missingDraftMessage: "missing",
        scopeChangedMessage: "changed",
        initialStatusLabel: "Skapar delningslänk…",
        copiedMessage: "copied",
        createFallbackMessage: "create failed",
        listFallbackMessage: "list failed",
        revokeFallbackMessage: "revoke failed",
        copyUnavailableMessage: "copy unavailable",
      },
    });
    await flushPromises();

    await flow.copyShareLink(listedShare);
    await flow.revokeOwnedShare(listedShare);

    expect(writeText).toHaveBeenCalledWith(listedShare.public_url);
    expect(revokeShare).toHaveBeenCalledWith("share-2");
    expect(flow.shares.value).toEqual([revokedShare]);
  });
});
