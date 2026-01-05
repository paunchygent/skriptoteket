import { computed, watch, type ComputedRef } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

import { isVirtualFileId, type VirtualFileId } from "./virtualFiles";

export type EditorCompareTarget = { kind: "version"; versionId: string } | { kind: "working" };

export const DEFAULT_COMPARE_FIELD: VirtualFileId = "tool.py";

type QueryRecord = Record<string, string | string[] | null | undefined>;

function queryStringValue(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function withoutQueryKey(query: QueryRecord, key: string): QueryRecord {
  const next = { ...query };
  delete next[key];
  return next;
}

function withQueryValue(
  query: QueryRecord,
  key: string,
  value: string | null,
): QueryRecord {
  if (value === null) {
    return withoutQueryKey(query, key);
  }
  return { ...query, [key]: value };
}

function parseCompareTarget(value: string | null): EditorCompareTarget | null {
  if (!value) return null;
  if (value === "working") return { kind: "working" };
  return { kind: "version", versionId: value };
}

export function useEditorCompareState(options: {
  route: RouteLocationNormalizedLoaded;
  router: Router;
}): {
  compareTarget: ComputedRef<EditorCompareTarget | null>;
  activeFileId: ComputedRef<VirtualFileId | null>;
  setCompareTarget: (target: EditorCompareTarget | null) => Promise<void>;
  setCompareVersionId: (versionId: string | null) => Promise<void>;
  toggleCompareVersionId: (versionId: string) => Promise<void>;
  setActiveFileId: (fileId: VirtualFileId) => Promise<void>;
  closeCompare: () => Promise<void>;
} {
  const { route, router } = options;

  const compareTarget = computed(() => parseCompareTarget(queryStringValue(route.query.compare)));
  const activeFileId = computed<VirtualFileId | null>(() => {
    const value = queryStringValue(route.query.field);
    return value && isVirtualFileId(value) ? value : null;
  });

  async function setCompareTarget(target: EditorCompareTarget | null): Promise<void> {
    const compareValue =
      target === null ? null : target.kind === "working" ? "working" : target.versionId;
    const nextCompare = withQueryValue(route.query as QueryRecord, "compare", compareValue);

    const next = compareValue ? nextCompare : withoutQueryKey(nextCompare, "field");
    await router.replace({ query: next });
  }

  async function setCompareVersionId(versionId: string | null): Promise<void> {
    await setCompareTarget(versionId ? { kind: "version", versionId } : null);
  }

  async function toggleCompareVersionId(versionId: string): Promise<void> {
    const current = compareTarget.value;
    if (current?.kind === "version" && current.versionId === versionId) {
      await setCompareTarget(null);
      return;
    }
    await setCompareVersionId(versionId);
  }

  async function setActiveFileId(fileId: VirtualFileId): Promise<void> {
    if (!compareTarget.value) {
      return;
    }
    await router.replace({
      query: withQueryValue(route.query as QueryRecord, "field", fileId),
    });
  }

  async function closeCompare(): Promise<void> {
    await setCompareTarget(null);
  }

  watch(
    () => [compareTarget.value, activeFileId.value] as const,
    ([target, field]) => {
      if (!target) return;
      if (field) return;
      void router.replace({
        query: withQueryValue(route.query as QueryRecord, "field", DEFAULT_COMPARE_FIELD),
      });
    },
    { immediate: true },
  );

  return {
    compareTarget,
    activeFileId,
    setCompareTarget,
    setCompareVersionId,
    toggleCompareVersionId,
    setActiveFileId,
    closeCompare,
  };
}
