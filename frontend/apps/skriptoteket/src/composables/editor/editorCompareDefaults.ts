import type { components } from "../../api/openapi";

import type { EditorCompareTarget } from "./useEditorCompareState";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];

export type DefaultCompareContext = {
  baseVersion: EditorVersionSummary | null;
  toolIsPublished: boolean;
  activeVersionId: string | null;
  versions: EditorVersionSummary[];
  parentVersionId: string | null;
};

export type DefaultCompareResult = {
  target: EditorCompareTarget | null;
  reason: string | null;
};

function dateScore(value: string | null): number {
  if (!value) return Number.NEGATIVE_INFINITY;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? Number.NEGATIVE_INFINITY : parsed;
}

function resolveActiveCompareVersionId(context: DefaultCompareContext): string | null {
  const { baseVersion, activeVersionId, versions } = context;
  if (!baseVersion) return null;

  if (activeVersionId && activeVersionId !== baseVersion.id) {
    return activeVersionId;
  }

  const fallback = versions.find((version) => version.state === "active" && version.id !== baseVersion.id);
  return fallback?.id ?? null;
}

export function resolveMostRecentRejectedReviewVersionId(
  versions: EditorVersionSummary[],
): string | null {
  let best: EditorVersionSummary | null = null;
  let bestScore = Number.NEGATIVE_INFINITY;

  for (const version of versions) {
    if (version.state !== "archived") continue;
    if (!version.reviewed_at) continue;
    if (version.published_at) continue;

    const score = dateScore(version.reviewed_at);
    if (score > bestScore) {
      best = version;
      bestScore = score;
      continue;
    }
    if (score === bestScore && best && version.version_number > best.version_number) {
      best = version;
    }
  }

  return best?.id ?? null;
}

export function resolvePreviousVisibleVersionId(params: {
  versions: EditorVersionSummary[];
  baseVersion: EditorVersionSummary;
}): string | null {
  const { versions, baseVersion } = params;

  let best: EditorVersionSummary | null = null;

  for (const version of versions) {
    if (version.id === baseVersion.id) continue;
    if (version.version_number >= baseVersion.version_number) continue;
    if (!best || version.version_number > best.version_number) {
      best = version;
    }
  }

  return best?.id ?? null;
}

export function resolveDefaultCompareTarget(context: DefaultCompareContext): DefaultCompareResult {
  const { baseVersion, toolIsPublished, versions, parentVersionId } = context;

  if (!baseVersion) {
    return { target: null, reason: "Ingen version att diffa." };
  }

  if (baseVersion.state === "in_review") {
    if (toolIsPublished) {
      const activeId = resolveActiveCompareVersionId(context);
      if (activeId) {
        return { target: { kind: "version", versionId: activeId }, reason: null };
      }
    }

    const rejectedId = resolveMostRecentRejectedReviewVersionId(versions);
    if (rejectedId) {
      return { target: { kind: "version", versionId: rejectedId }, reason: null };
    }

    return {
      target: null,
      reason: "Ingen publicerad version eller tidigare avvisad granskning att diffa mot.",
    };
  }

  if (baseVersion.state === "draft") {
    if (parentVersionId && parentVersionId !== baseVersion.id) {
      const parentVisible = versions.some((version) => version.id === parentVersionId);
      if (parentVisible) {
        return { target: { kind: "version", versionId: parentVersionId }, reason: null };
      }
    }

    const previousVisibleId = resolvePreviousVisibleVersionId({ versions, baseVersion });
    if (previousVisibleId) {
      return { target: { kind: "version", versionId: previousVisibleId }, reason: null };
    }

    return { target: null, reason: "Ingen tidigare version att diffa mot." };
  }

  return { target: null, reason: "Den här versionen går inte att diffa automatiskt." };
}
