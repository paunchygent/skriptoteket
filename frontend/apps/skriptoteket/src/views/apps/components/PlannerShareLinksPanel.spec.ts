/**
 * Planner share-link management tests.
 *
 * These tests keep the compact owned-link management surface focused on public
 * outcomes: the Dela trigger opens management, active links can be copied or
 * revoked, and revoked links stay out of the visible management list.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import PlannerShareLinksPanel from "./PlannerShareLinksPanel.vue";

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

describe("PlannerShareLinksPanel", () => {
  it("opens from the Dela trigger and emits create, copy, and revoke intents", async () => {
    const share = makeShare({
      id: "share-1",
      publicUrl: "https://skriptoteket.hule.education/share/classroom/public-token/klass-7a",
    });
    const wrapper = mount(PlannerShareLinksPanel, {
      props: {
        shares: [share],
      },
    });

    expect(wrapper.find('[data-test="planner-share-links-panel"]').exists()).toBe(false);

    await wrapper.get('[data-test="planner-share-links-trigger"]').trigger("click");
    await wrapper.get('[data-test="planner-share-create"]').trigger("click");
    await wrapper.get('[data-test="planner-share-copy-share-1"]').trigger("click");
    await wrapper.get('[data-test="planner-share-revoke-share-1"]').trigger("click");

    expect(wrapper.emitted("create-share")).toEqual([[]]);
    expect(wrapper.emitted("copy-share")).toEqual([[share]]);
    expect(wrapper.emitted("revoke-share")).toEqual([[share]]);
  });

  it("disables copy for metadata that lacks a public URL", async () => {
    const share = makeShare({
      id: "share-2",
      publicUrl: null,
    });
    const wrapper = mount(PlannerShareLinksPanel, {
      props: {
        shares: [share],
      },
    });

    await wrapper.get('[data-test="planner-share-links-trigger"]').trigger("click");

    expect(wrapper.get('[data-test="planner-share-copy-share-2"]').attributes("disabled"))
      .toBeDefined();
  });

  it("keeps revoked links out of the visible management list", async () => {
    const activeShare = makeShare({
      id: "share-3",
      publicUrl: "https://skriptoteket.hule.education/share/classroom/active/klass-7a",
    });
    const revokedShare = makeShare({
      id: "share-4",
      publicUrl: "https://skriptoteket.hule.education/share/classroom/revoked/klass-7a",
      revokedAt: "2026-04-30T11:00:00Z",
    });
    const wrapper = mount(PlannerShareLinksPanel, {
      props: {
        shares: [activeShare, revokedShare],
      },
    });

    await wrapper.get('[data-test="planner-share-links-trigger"]').trigger("click");

    expect(wrapper.find('[data-test="planner-share-link-share-3"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="planner-share-link-share-4"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="planner-share-archive-link-share-4"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="planner-share-archive-toggle"]').exists()).toBe(false);
  });
});
