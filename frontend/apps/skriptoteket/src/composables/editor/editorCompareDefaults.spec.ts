import { describe, expect, it } from "vitest";

import type { components } from "../../api/openapi";

import {
  resolveDefaultCompareTarget,
  resolveMostRecentRejectedReviewVersionId,
  resolvePreviousVisibleVersionId,
} from "./editorCompareDefaults";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];

function version(
  id: string,
  params: Partial<EditorVersionSummary> & Pick<EditorVersionSummary, "state" | "version_number">,
): EditorVersionSummary {
  return {
    id,
    version_number: params.version_number,
    state: params.state,
    created_at: params.created_at ?? "2026-01-01T00:00:00Z",
    reviewed_at: params.reviewed_at ?? null,
    published_at: params.published_at ?? null,
  };
}

describe("editorCompareDefaults", () => {
  describe("resolveMostRecentRejectedReviewVersionId", () => {
    it("returns null when no rejected reviews exist", () => {
      expect(
        resolveMostRecentRejectedReviewVersionId([
          version("v1", { state: "archived", version_number: 1, reviewed_at: null, published_at: null }),
          version("v2", { state: "archived", version_number: 2, reviewed_at: "2026-01-02T00:00:00Z", published_at: "2026-01-03T00:00:00Z" }),
        ]),
      ).toBeNull();
    });

    it("selects by reviewed_at desc (tie-breaker: version_number desc)", () => {
      expect(
        resolveMostRecentRejectedReviewVersionId([
          version("old", { state: "archived", version_number: 3, reviewed_at: "2026-01-01T10:00:00Z", published_at: null }),
          version("new", { state: "archived", version_number: 2, reviewed_at: "2026-01-02T10:00:00Z", published_at: null }),
          version("tie-low", { state: "archived", version_number: 1, reviewed_at: "2026-01-05T10:00:00Z", published_at: null }),
          version("tie-high", { state: "archived", version_number: 9, reviewed_at: "2026-01-05T10:00:00Z", published_at: null }),
        ]),
      ).toBe("tie-high");
    });
  });

  describe("resolvePreviousVisibleVersionId", () => {
    it("returns the highest version_number strictly below base", () => {
      const base = version("base", { state: "draft", version_number: 10 });
      expect(
        resolvePreviousVisibleVersionId({
          baseVersion: base,
          versions: [
            version("base", { state: "draft", version_number: 10 }),
            version("v7", { state: "archived", version_number: 7 }),
            version("v9", { state: "archived", version_number: 9 }),
            version("v12", { state: "archived", version_number: 12 }),
          ],
        }),
      ).toBe("v9");
    });
  });

  describe("resolveDefaultCompareTarget", () => {
    it("uses active version when in_review + published", () => {
      const base = version("review", { state: "in_review", version_number: 3 });
      const active = version("active", { state: "active", version_number: 2 });

      expect(
        resolveDefaultCompareTarget({
          baseVersion: base,
          toolIsPublished: true,
          activeVersionId: active.id,
          versions: [base, active],
          parentVersionId: null,
        }).target,
      ).toEqual({ kind: "version", versionId: "active" });
    });

    it("uses most recent rejected review when in_review + not published", () => {
      const base = version("review", { state: "in_review", version_number: 3 });
      const rejected = version("rejected", {
        state: "archived",
        version_number: 2,
        reviewed_at: "2026-01-02T10:00:00Z",
        published_at: null,
      });

      expect(
        resolveDefaultCompareTarget({
          baseVersion: base,
          toolIsPublished: false,
          activeVersionId: null,
          versions: [base, rejected],
          parentVersionId: null,
        }).target,
      ).toEqual({ kind: "version", versionId: "rejected" });
    });

    it("returns null when in_review and no active/rejected exists", () => {
      const base = version("review", { state: "in_review", version_number: 1 });
      const result = resolveDefaultCompareTarget({
        baseVersion: base,
        toolIsPublished: false,
        activeVersionId: null,
        versions: [base],
        parentVersionId: null,
      });

      expect(result.target).toBeNull();
      expect(result.reason).toBeTruthy();
    });

    it("uses parent_version_id when drafting and parent is visible", () => {
      const base = version("draft", { state: "draft", version_number: 5 });
      const parent = version("parent", { state: "archived", version_number: 4 });

      expect(
        resolveDefaultCompareTarget({
          baseVersion: base,
          toolIsPublished: false,
          activeVersionId: null,
          versions: [base, parent],
          parentVersionId: parent.id,
        }).target,
      ).toEqual({ kind: "version", versionId: "parent" });
    });

    it("falls back to previous visible version when drafting and parent is missing", () => {
      const base = version("draft", { state: "draft", version_number: 5 });
      const previous = version("previous", { state: "archived", version_number: 4 });

      expect(
        resolveDefaultCompareTarget({
          baseVersion: base,
          toolIsPublished: false,
          activeVersionId: null,
          versions: [base, previous],
          parentVersionId: "missing",
        }).target,
      ).toEqual({ kind: "version", versionId: "previous" });
    });
  });
});
