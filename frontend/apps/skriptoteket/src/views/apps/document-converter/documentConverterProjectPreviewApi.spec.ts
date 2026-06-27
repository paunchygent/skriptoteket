/**
 * Document Converter project-preview API boundary specs.
 *
 * Domain purpose:
 *   Prove the route-visible Document Converter UI submits HTML/CSS project
 *   preview work through Skriptoteket-owned scoped endpoints with locked
 *   frontend output choices.
 *
 * Relationships:
 *   - Exercises `documentConverterProjectPreviewApi.ts`.
 *   - Complements the route component spec that proves visible copy and
 *     workflow state.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  discardDocumentConverterProjectPreview,
  downloadDocumentConverterProjectPreviewArtifact,
  renderDocumentConverterProjectPreview,
  saveDocumentConverterProjectPreviewArtifact,
  type DocumentConverterProjectPreviewArtifact,
} from "./documentConverterProjectPreviewApi";
import { useAuthStore } from "../../../stores/auth";

function textFile(name: string, content: string, type: string): File {
  return new File([content], name, { type });
}

describe("documentConverterProjectPreviewApi", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
    const auth = useAuthStore();
    auth.csrfToken = "csrf-token";
  });

  it("builds the project-preview manifest and multipart files with the two approved output modes", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          artifacts: [],
          created_at: "2026-06-25T12:00:00Z",
          error: null,
          expires_at: "2026-06-26T12:00:00Z",
          output_mode: "combined_pdf",
          preview_id: "preview-1",
          status: "succeeded",
          template_id: "academic_phd",
        }),
        {
          headers: { "content-type": "application/json" },
          status: 200,
        },
      ),
    );

    await renderDocumentConverterProjectPreview({
      files: [
        textFile("index.html", "<h1>Hej</h1>", "text/html"),
        textFile("styles.css", "h1{}", "text/css"),
        textFile("cover.png", "png", "image/png"),
      ],
      htmlEntryFilename: "index.html",
      outputMode: "combined_pdf",
      paperSize: "a3",
      templateId: "academic_phd",
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/document-converter/project-previews",
      expect.objectContaining({
        credentials: "include",
        method: "POST",
      }),
    );
    const body = vi.mocked(fetch).mock.calls[0]?.[1]?.body as FormData;
    const manifest = JSON.parse(String(body.get("manifest_json"))) as Record<string, unknown>;
    expect(manifest).toMatchObject({
      html_entries: [{ entry_id: "index", filename: "index.html", title: "index.html" }],
      css_files: ["styles.css"],
      image_files: ["cover.png"],
      font_files: [],
      output_mode: "combined_pdf",
      pdf_controls: {
        orientation: "portrait",
        paper_size: "a3",
        template_id: "academic_phd",
      },
    });
    expect(body.getAll("files")).toHaveLength(3);
    expect(JSON.stringify(manifest)).not.toContain("both");
  });

  it("rejects backend-only output modes before building a preview request", async () => {
    await expect(
      renderDocumentConverterProjectPreview({
        files: [textFile("index.html", "<h1>Hej</h1>", "text/html")],
        htmlEntryFilename: "index.html",
        outputMode: "both" as "combined_pdf",
        paperSize: "a4",
        templateId: "academic_phd",
      }),
    ).rejects.toThrow("Unsupported Document Converter output mode");

    expect(fetch).not.toHaveBeenCalled();
  });

  it("uses owner-scoped preview artifact download, save, and discard endpoints", async () => {
    const artifact: DocumentConverterProjectPreviewArtifact = {
      artifact_id: "artifact-1",
      content_type: "application/pdf",
      download_url: null,
      filename: "preview.pdf",
      kind: "combined_pdf",
      size_bytes: 12,
      source_entry_id: null,
    };

    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response("pdf", {
          headers: {
            "content-disposition": 'attachment; filename="preview.pdf"',
            "content-type": "application/pdf",
          },
          status: 200,
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            source_artifact_id: "document-converter:project-preview:preview-1:artifact-1",
            vault_artifact: {
              bytes: 12,
              created_at: "2026-06-25T12:10:00Z",
              file_id: "file-1",
              name: "preview.pdf",
            },
          }),
          { headers: { "content-type": "application/json" }, status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ preview_id: "preview-1", status: "discarded" }), {
          headers: { "content-type": "application/json" },
          status: 200,
        }),
      );

    const download = await downloadDocumentConverterProjectPreviewArtifact({
      artifact,
      filenameStem: "Lärarens projekt.pdf",
      previewId: "preview-1",
    });
    const saved = await saveDocumentConverterProjectPreviewArtifact({
      artifact,
      filenameStem: "Lärarens projekt.pdf",
      previewId: "preview-1",
    });
    const discarded = await discardDocumentConverterProjectPreview({ previewId: "preview-1" });

    expect(download.filename).toBe("preview.pdf");
    expect(saved.vault_artifact.name).toBe("preview.pdf");
    expect(discarded.status).toBe("discarded");
    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/apps/documents.conversion_hub/document-converter/project-previews/preview-1/artifacts/artifact-1?filename_stem=L%C3%A4rarens+projekt.pdf",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/documents.conversion_hub/document-converter/project-previews/preview-1/artifacts/artifact-1/save?filename_stem=L%C3%A4rarens+projekt.pdf",
      expect.objectContaining({ credentials: "include", method: "POST" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      3,
      "/api/v1/apps/documents.conversion_hub/document-converter/project-previews/preview-1",
      expect.objectContaining({ credentials: "include", method: "DELETE" }),
    );
  });
});
