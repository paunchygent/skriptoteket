/**
 * Document Converter single-file selection helpers.
 *
 * Domain purpose:
 *   Centralize source/output format inference and labels for local uploads and
 *   Mina filer batches so route state can stay focused on orchestration.
 *
 * Relationships:
 *   - Used by `useDocumentConverterSingleFile.ts`.
 *   - Mirrors the backend Document Converter source/output format contract.
 */

import type { components } from "../../../api/openapi";
import type { DocumentConverterSingleFileRoute } from "./documentConverterFileApi";

type ConversionHubJobStatus = components["schemas"]["ConversionHubJobStatus"];
type NamedSourceFile = { name: string };

export type DocumentConverterSingleFileOutput =
  | "pdf"
  | "docx"
  | "md";
export type DocumentConverterSingleFileSource =
  | "html"
  | "docx"
  | "md"
  | "pdf";

const SOURCE_EXTENSIONS: Record<DocumentConverterSingleFileSource, string[]> = {
  html: [".html", ".htm"],
  docx: [".docx"],
  md: [".md", ".markdown"],
  pdf: [".pdf"],
};

export const OUTPUT_LABELS: Record<DocumentConverterSingleFileOutput, string> = {
  docx: "DOCX",
  md: "Markdown",
  pdf: "PDF",
};

export const SOURCE_LABELS: Record<DocumentConverterSingleFileSource, string> = {
  docx: "DOCX",
  html: "HTML",
  md: "Markdown",
  pdf: "PDF",
};

export const TERMINAL_STATUSES = new Set<ConversionHubJobStatus>([
  "canceled",
  "failed",
  "succeeded",
]);

export function isSingleFileSource(value: string): value is DocumentConverterSingleFileSource {
  return value === "html" || value === "docx" || value === "md" || value === "pdf";
}

export function isSingleFileOutput(value: string): value is DocumentConverterSingleFileOutput {
  return value === "pdf" || value === "docx" || value === "md";
}

export function sourceFormatFromFilename(
  filename: string,
): DocumentConverterSingleFileSource | null {
  const normalized = filename.toLowerCase();
  for (const [format, extensions] of Object.entries(SOURCE_EXTENSIONS)) {
    if (extensions.some((extension) => normalized.endsWith(extension))) {
      return format as DocumentConverterSingleFileSource;
    }
  }
  return null;
}

export function sourceAcceptForFormats(
  formats: readonly DocumentConverterSingleFileSource[],
): string {
  const extensions = formats.flatMap((format) => SOURCE_EXTENSIONS[format] ?? []);
  return Array.from(new Set(extensions)).join(",");
}

export function sourceBatchLabel(files: readonly NamedSourceFile[]): string {
  if (files.length === 0) {
    return "Ingen fil vald";
  }
  if (files.length === 1) {
    return files[0]?.name ?? "Ingen fil vald";
  }
  return `${files.length.toLocaleString("sv-SE")} filer valda`;
}

export function outputFormatsForSource(
  routes: readonly DocumentConverterSingleFileRoute[],
  sourceFormat: DocumentConverterSingleFileSource,
): DocumentConverterSingleFileOutput[] {
  return routes
    .filter((route) => route.source_format === sourceFormat)
    .map((route) => route.output_format)
    .filter(isSingleFileOutput);
}

export function removeListItem<T>(items: readonly T[], index: number): T[] | null {
  if (index < 0 || index >= items.length) {
    return null;
  }
  return items.filter((_item, itemIndex) => itemIndex !== index);
}

export function moveListItem<T>(
  items: readonly T[],
  fromIndex: number,
  toIndex: number,
): T[] | null {
  if (fromIndex < 0 || toIndex < 0 || fromIndex >= items.length || toIndex >= items.length) {
    return null;
  }
  const nextItems = [...items];
  const [item] = nextItems.splice(fromIndex, 1);
  if (!item) {
    return null;
  }
  nextItems.splice(toIndex, 0, item);
  return nextItems;
}
