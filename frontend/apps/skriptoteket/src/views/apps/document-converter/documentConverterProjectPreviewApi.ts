/**
 * Document Converter project-preview API client.
 *
 * Domain purpose:
 *   Submit HTML/CSS project preview work and artifact actions through
 *   Skriptoteket-owned Document Converter endpoints.
 *
 * Relationships:
 *   - Consumed by `DocumentConverterView.vue`.
 *   - Uses generated OpenAPI response types and the protected API client.
 *   - Builds the multipart manifest accepted by the project-preview backend.
 */

import {
  apiDelete,
  apiFetchBlobResponse,
  apiPost,
  type ApiBlobResponse,
} from "../../../api/client";
import type { components } from "../../../api/openapi";
import {
  getDocumentConverterHtmlEntryId,
  summarizeDocumentConverterProjectFiles,
} from "./documentConverterProjectFiles";

export type DocumentConverterProjectPreviewArtifact =
  components["schemas"]["DocumentConverterProjectPreviewArtifact"];
export type DocumentConverterProjectPreviewResult =
  components["schemas"]["DocumentConverterProjectPreviewResult"];
export type DocumentConverterProjectPreviewArtifactSaveResult =
  components["schemas"]["SaveDocumentConverterProjectPreviewArtifactResult"];
export type DocumentConverterProjectPreviewDiscardResult =
  components["schemas"]["DiscardDocumentConverterProjectPreviewResult"];
export type DocumentConverterProjectTemplateId =
  components["schemas"]["DocumentConverterProjectTemplateId"];
export type DocumentConverterProjectOutputMode = Exclude<
  components["schemas"]["DocumentConverterProjectOutputMode"],
  "both"
>;
export type DocumentConverterProjectPaperSize = "a3" | "a4" | "a5";

export type RenderDocumentConverterProjectPreviewParams = {
  files: readonly File[];
  htmlEntryFilename: string;
  outputMode: DocumentConverterProjectOutputMode;
  paperSize: DocumentConverterProjectPaperSize;
  templateId: DocumentConverterProjectTemplateId;
};

const PROJECT_PREVIEWS_ROOT =
  "/api/v1/apps/documents.conversion_hub/document-converter/project-previews";

const FRONTEND_OUTPUT_MODES = new Set<DocumentConverterProjectOutputMode>([
  "separate_pdfs",
  "combined_pdf",
]);
const PAPER_SIZES = new Set<DocumentConverterProjectPaperSize>(["a3", "a4", "a5"]);

type ProjectPreviewManifest = {
  html_entries: { entry_id: string; filename: string; title: string }[];
  css_files: string[];
  image_files: string[];
  font_files: [];
  output_mode: DocumentConverterProjectOutputMode;
  pdf_controls: {
    paper_size: DocumentConverterProjectPaperSize;
    orientation: "portrait";
    margins: {
      top_mm: number;
      right_mm: number;
      bottom_mm: number;
      left_mm: number;
    };
    template_id: DocumentConverterProjectTemplateId;
  };
};

function assertOutputMode(value: string): asserts value is DocumentConverterProjectOutputMode {
  if (!FRONTEND_OUTPUT_MODES.has(value as DocumentConverterProjectOutputMode)) {
    throw new Error("Unsupported Document Converter output mode");
  }
}

function assertPaperSize(value: string): asserts value is DocumentConverterProjectPaperSize {
  if (!PAPER_SIZES.has(value as DocumentConverterProjectPaperSize)) {
    throw new Error("Unsupported Document Converter paper size");
  }
}

function orderedHtmlFiles(params: {
  htmlFiles: File[];
  preferredFilename: string;
}): File[] {
  const preferred = params.htmlFiles.find((file) => file.name === params.preferredFilename);
  if (!preferred) {
    return params.htmlFiles;
  }
  return [
    preferred,
    ...params.htmlFiles.filter((file) => file.name !== params.preferredFilename),
  ];
}

function buildProjectPreviewManifest(
  params: RenderDocumentConverterProjectPreviewParams,
): ProjectPreviewManifest {
  assertOutputMode(params.outputMode);
  assertPaperSize(params.paperSize);
  const summary = summarizeDocumentConverterProjectFiles(params.files);
  const htmlFiles = orderedHtmlFiles({
    htmlFiles: summary.html,
    preferredFilename: params.htmlEntryFilename,
  });
  if (htmlFiles.length === 0) {
    throw new Error("Document Converter project preview requires an HTML file");
  }

  return {
    html_entries: htmlFiles.map((file) => ({
      entry_id: getDocumentConverterHtmlEntryId(file.name),
      filename: file.name,
      title: file.name,
    })),
    css_files: summary.css.map((file) => file.name),
    image_files: summary.images.map((file) => file.name),
    font_files: [],
    output_mode: params.outputMode,
    pdf_controls: {
      paper_size: params.paperSize,
      orientation: "portrait",
      margins: {
        top_mm: 12,
        right_mm: 12,
        bottom_mm: 12,
        left_mm: 12,
      },
      template_id: params.templateId,
    },
  };
}

function previewArtifactUrl(params: {
  previewId: string;
  artifactId?: string;
  action?: "save";
}): string {
  const base = [
    PROJECT_PREVIEWS_ROOT,
    encodeURIComponent(params.previewId),
    params.artifactId ? "artifacts" : null,
    params.artifactId ? encodeURIComponent(params.artifactId) : null,
    params.action ?? null,
  ].filter(Boolean);
  return base.join("/");
}

export async function renderDocumentConverterProjectPreview(
  params: RenderDocumentConverterProjectPreviewParams,
): Promise<DocumentConverterProjectPreviewResult> {
  const manifest = buildProjectPreviewManifest(params);
  const form = new FormData();
  form.append("manifest_json", JSON.stringify(manifest));
  params.files.forEach((file) => {
    form.append("files", file, file.name);
  });

  return await apiPost<DocumentConverterProjectPreviewResult>(
    PROJECT_PREVIEWS_ROOT,
    form,
  );
}

export async function downloadDocumentConverterProjectPreviewArtifact(params: {
  previewId: string;
  artifact: DocumentConverterProjectPreviewArtifact;
}): Promise<ApiBlobResponse> {
  return await apiFetchBlobResponse(
    previewArtifactUrl({
      previewId: params.previewId,
      artifactId: params.artifact.artifact_id,
    }),
    { method: "GET" },
  );
}

export async function saveDocumentConverterProjectPreviewArtifact(params: {
  previewId: string;
  artifact: DocumentConverterProjectPreviewArtifact;
}): Promise<DocumentConverterProjectPreviewArtifactSaveResult> {
  return await apiPost<DocumentConverterProjectPreviewArtifactSaveResult>(
    previewArtifactUrl({
      previewId: params.previewId,
      artifactId: params.artifact.artifact_id,
      action: "save",
    }),
  );
}

export async function discardDocumentConverterProjectPreview(params: {
  previewId: string;
}): Promise<DocumentConverterProjectPreviewDiscardResult> {
  return await apiDelete<DocumentConverterProjectPreviewDiscardResult>(
    previewArtifactUrl({ previewId: params.previewId }),
  );
}
