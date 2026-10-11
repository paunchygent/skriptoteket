import {
  isVirtualFileId,
  virtualFileLabel,
  virtualFileLanguage,
  type VirtualFileId,
  type VirtualFileLanguage,
} from "./virtualFiles";

/** A bundled tool's files beside its entrypoint, keyed by file name. Empty for a single-file tool. */
export type BundleFiles = Record<string, string>;

/** Name the editor shows for the entrypoint source of a bundled tool. */
export const ENTRY_FILE_NAME = "tool.py";

export type BundleFileId = `bundle/${string}`;

/** A file the editor can show or diff: a virtual file or one bundle file. */
export type EditorFileId = VirtualFileId | BundleFileId;

export type EditorFileDiffItem = {
  virtualFileId: EditorFileId;
  beforeText: string;
  afterText: string;
};

export function bundleFileId(name: string): BundleFileId {
  return `bundle/${name}`;
}

export function isBundleFileId(id: EditorFileId): id is BundleFileId {
  return id.startsWith("bundle/");
}

const BUNDLE_FILE_NAME = /^[A-Za-z0-9_][A-Za-z0-9_.-]*$/;

/** Accepts a virtual file id or `bundle/<name>` with a name the server would accept. */
export function isEditorFileId(value: unknown): value is EditorFileId {
  if (isVirtualFileId(value)) return true;
  return (
    typeof value === "string" &&
    value.startsWith("bundle/") &&
    BUNDLE_FILE_NAME.test(value.slice("bundle/".length))
  );
}

export function bundleFileName(id: BundleFileId): string {
  return id.slice("bundle/".length);
}

export function sortedBundleFileNames(files: BundleFiles): string[] {
  return Object.keys(files).sort((a, b) => a.localeCompare(b));
}

export function areBundleFilesEqual(a: BundleFiles, b: BundleFiles): boolean {
  const names = sortedBundleFileNames(a);
  if (names.length !== Object.keys(b).length) return false;
  return names.every((name) => Object.hasOwn(b, name) && a[name] === b[name]);
}

/** Stable text form of the bundle for fingerprints: sorted names, NUL-separated. */
export function bundleFilesFingerprint(files: BundleFiles): string {
  return sortedBundleFileNames(files)
    .map((name) => `${name}\u0000${files[name]}`)
    .join("\u0000");
}

export function bundleFileLanguage(name: string): VirtualFileLanguage {
  if (name.endsWith(".py")) return "python";
  if (name.endsWith(".json")) return "json";
  return "text";
}

export function editorFileLabel(id: EditorFileId): string {
  return isBundleFileId(id) ? bundleFileName(id) : virtualFileLabel(id);
}

export function editorFileLanguage(id: EditorFileId): VirtualFileLanguage {
  return isBundleFileId(id) ? bundleFileLanguage(bundleFileName(id)) : virtualFileLanguage(id);
}

/** Diff items for every bundle file on either side; a file missing on one side diffs against "". */
export function bundleDiffItems(before: BundleFiles, after: BundleFiles): EditorFileDiffItem[] {
  const names = sortedBundleFileNames({ ...before, ...after });
  return names.map((name) => ({
    virtualFileId: bundleFileId(name),
    beforeText: before[name] ?? "",
    afterText: after[name] ?? "",
  }));
}
