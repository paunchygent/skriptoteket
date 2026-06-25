/**
 * Document Converter project-file helpers.
 *
 * Domain purpose:
 *   Classify teacher-selected HTML/CSS/image files for the route-visible
 *   Document Converter project workflow and manifest construction.
 *
 * Relationships:
 *   - Used by the project-preview API client and route component.
 *   - Mirrors the backend project manifest filename classes without exposing
 *     renderer or storage mechanics in UI state.
 */

export type DocumentConverterProjectFileKind = "html" | "css" | "image" | "other";

export type DocumentConverterProjectFileSummary = {
  html: File[];
  css: File[];
  images: File[];
  other: File[];
};

const HTML_EXTENSIONS = new Set([".html", ".htm"]);
const CSS_EXTENSIONS = new Set([".css"]);
const IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".webp"]);

function extensionOf(filename: string): string {
  const normalized = filename.trim().toLowerCase();
  const dotIndex = normalized.lastIndexOf(".");
  return dotIndex >= 0 ? normalized.slice(dotIndex) : "";
}

export function getDocumentConverterProjectFileKind(
  filename: string,
): DocumentConverterProjectFileKind {
  const extension = extensionOf(filename);
  if (HTML_EXTENSIONS.has(extension)) {
    return "html";
  }
  if (CSS_EXTENSIONS.has(extension)) {
    return "css";
  }
  if (IMAGE_EXTENSIONS.has(extension)) {
    return "image";
  }
  return "other";
}

export function getDocumentConverterHtmlEntryId(filename: string): string {
  const baseName = filename.replace(/\.[^.]+$/, "");
  const entryId = baseName
    .normalize("NFKD")
    .replace(/[^\w-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 64);
  return entryId || "index";
}

export function summarizeDocumentConverterProjectFiles(
  files: readonly File[],
): DocumentConverterProjectFileSummary {
  return files.reduce<DocumentConverterProjectFileSummary>(
    (summary, file) => {
      const kind = getDocumentConverterProjectFileKind(file.name);
      if (kind === "html") {
        summary.html.push(file);
      } else if (kind === "css") {
        summary.css.push(file);
      } else if (kind === "image") {
        summary.images.push(file);
      } else {
        summary.other.push(file);
      }
      return summary;
    },
    { html: [], css: [], images: [], other: [] },
  );
}
