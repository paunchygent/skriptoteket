export type RecentEditorTool = {
  toolId: string;
  title: string;
  slug: string;
  openedAt: number;
};

const RECENTS_KEY_PREFIX = "skriptoteket.editor.recents.v1";
const RECENTS_LIMIT = 12;

function storageKey(userId: string): string {
  return `${RECENTS_KEY_PREFIX}:${userId}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

function normalizeRecentTool(value: unknown): RecentEditorTool | null {
  if (!isRecord(value)) return null;

  const toolId = typeof value.toolId === "string" ? value.toolId : "";
  if (!toolId) return null;

  const title = typeof value.title === "string" ? value.title : "";
  const slug = typeof value.slug === "string" ? value.slug : "";
  const openedAt = typeof value.openedAt === "number" ? value.openedAt : 0;

  return {
    toolId,
    title,
    slug,
    openedAt,
  };
}

export function listRecentEditorTools(userId: string): RecentEditorTool[] {
  if (typeof window === "undefined") return [];
  if (!userId) return [];

  const raw = window.localStorage.getItem(storageKey(userId));
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];

    return parsed
      .map(normalizeRecentTool)
      .filter((item): item is RecentEditorTool => item !== null)
      .sort((a, b) => b.openedAt - a.openedAt)
      .slice(0, RECENTS_LIMIT);
  } catch {
    return [];
  }
}

export function getLastRecentEditorToolId(userId: string): string | null {
  const items = listRecentEditorTools(userId);
  return items[0]?.toolId ?? null;
}

export function recordRecentEditorTool(
  userId: string,
  tool: { toolId: string; title: string; slug: string },
): RecentEditorTool[] {
  if (typeof window === "undefined") return [];
  if (!userId) return [];
  if (!tool.toolId) return listRecentEditorTools(userId);

  const nextItem: RecentEditorTool = {
    toolId: tool.toolId,
    title: tool.title,
    slug: tool.slug,
    openedAt: Date.now(),
  };

  const prev = listRecentEditorTools(userId);
  const deduped = prev.filter((item) => item.toolId !== tool.toolId);
  const next = [nextItem, ...deduped].slice(0, RECENTS_LIMIT);

  try {
    window.localStorage.setItem(storageKey(userId), JSON.stringify(next));
  } catch {
    // ignore (storage may be full or blocked)
  }

  return next;
}

export function removeRecentEditorTool(userId: string, toolId: string): RecentEditorTool[] {
  if (typeof window === "undefined") return [];
  if (!userId) return [];
  if (!toolId) return listRecentEditorTools(userId);

  const prev = listRecentEditorTools(userId);
  const next = prev.filter((item) => item.toolId !== toolId);

  try {
    window.localStorage.setItem(storageKey(userId), JSON.stringify(next));
  } catch {
    // ignore
  }

  return next;
}
