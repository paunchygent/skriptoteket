import type { components } from "../../api/openapi";

export type FileRefSource = components["schemas"]["UiFileRefSource"];

export type FileRefInfo = {
  ref: string;
  name: string;
  bytes: number;
  field?: string | null;
};

export function getFileRefSource(ref: string): FileRefSource | null {
  const index = ref.indexOf(":");
  const prefix = index > 0 ? ref.slice(0, index) : "";
  if (prefix === "session" || prefix === "vault") return prefix;
  return null;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} kB`;
  const mb = kb / 1024;
  return `${mb.toFixed(1)} MB`;
}

export function filterFileRefsBySources(
  refs: FileRefInfo[],
  sources?: FileRefSource[] | null,
): FileRefInfo[] {
  if (!sources || sources.length === 0) return refs;
  const allowed = new Set(sources);
  return refs.filter((ref) => {
    const source = getFileRefSource(ref.ref);
    return source !== null && allowed.has(source);
  });
}
