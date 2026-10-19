/**
 * Exam workspace export format list (TASK-SKRIPT-40-04-07, W1, W11).
 *
 * Expected behavior:
 *   The menu offers QTI, the student PDF, PDF med facit and DOCX in that order,
 *   then the Exam.net import PDF last as the fallback for a failed QTI import.
 *   Each format's words match the workspace's Swedish copy.
 */

import { describe, expect, it } from "vitest";

import { EXAM_WORKSPACE_EXPORT_FORMATS } from "./examWorkspaceExportFormats";

describe("exam workspace export formats", () => {
  it("lists the five formats in the workspace's order", () => {
    expect(EXAM_WORKSPACE_EXPORT_FORMATS.map((format) => format.target)).toEqual([
      "qti",
      "pdf",
      "pdf_facit",
      "docx",
      "examnet_pdf",
    ]);
  });

  it("names every format as the workspace offers it", () => {
    expect(EXAM_WORKSPACE_EXPORT_FORMATS.map((format) => format.name)).toEqual([
      "QTI",
      "PDF",
      "PDF med facit",
      "DOCX",
      "PDF för Exam.net",
    ]);
  });

  it("keeps the Exam.net import PDF last, as the fallback for a failed QTI import", () => {
    const fallback = EXAM_WORKSPACE_EXPORT_FORMATS.at(-1);
    expect(fallback).toMatchObject({ target: "examnet_pdf", use: "reserv" });
    expect(fallback?.hint).toContain("Inte för utskrift");
  });

  it("keeps no suffix on PDF med facit and the purpose suffix on the others", () => {
    expect(EXAM_WORKSPACE_EXPORT_FORMATS.map((format) => format.use)).toEqual([
      "Exam.net",
      "utskrift",
      null,
      "Word",
      "reserv",
    ]);
  });
});
