import { describe, expect, it } from "vitest";

import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import { examWorkspaceOpenGroups } from "./examWorkspaceOpenGroups";

function exam(id: string, courseKey: string | null, savedAt: string): ExamWorkspaceDocumentSummary {
  return {
    course_key: courseKey,
    lineage_id: id,
    name: `${id}.provdokument.zip`,
    saved_at: savedAt,
    title: id,
    vault_file_id: `file-${id}`,
    version: 1,
  };
}

const NAMES: Record<string, string> = {
  ENGENG05: "Engelska 5",
  SVESVE01: "Svenska 1",
  ÅSVSVA01: "Åländsk svenska 1",
  ÖVRMAT01: "Matematik 1a",
};
const courseName = (key: string) => NAMES[key] ?? null;
const ids = (groups: ReturnType<typeof examWorkspaceOpenGroups>) =>
  groups.map((group) => [group.heading, group.documents.map((entry) => entry.lineage_id)]);

describe("examWorkspaceOpenGroups", () => {
  it("puts registered courses first in profile order, not by name or by newest exam", () => {
    const documents = [
      exam("a", "ENGENG05", "2026-10-17T10:00:00Z"),
      exam("b", "SVESVE01", "2026-10-10T10:00:00Z"),
      exam("c", "ÖVRMAT01", "2026-10-17T12:00:00Z"),
    ];

    const groups = examWorkspaceOpenGroups(documents, "course", ["SVESVE01", "ENGENG05"], courseName);

    expect(ids(groups)).toEqual([
      ["Svenska 1", ["b"]],
      ["Engelska 5", ["a"]],
      ["Matematik 1a", ["c"]],
    ]);
  });

  it("orders unregistered courses by Swedish collation, so Å and Ö sort after Z", () => {
    const documents = [
      exam("x", "ÅSVSVA01", "2026-10-17T10:00:00Z"),
      exam("y", "ÖVRMAT01", "2026-10-17T10:00:00Z"),
      exam("z", "SVESVE01", "2026-10-17T10:00:00Z"),
    ];
    NAMES.ÖVRMAT01 = "Zoologi 1";

    const groups = examWorkspaceOpenGroups(documents, "course", [], courseName);
    NAMES.ÖVRMAT01 = "Matematik 1a";

    expect(groups.map((group) => group.heading)).toEqual(["Svenska 1", "Zoologi 1", "Åländsk svenska 1"]);
  });

  it("puts exams without a course last under Utan kurs, newest first in every group", () => {
    const documents = [
      exam("old", null, "2026-09-01T10:00:00Z"),
      exam("eng-old", "ENGENG05", "2026-09-01T10:00:00Z"),
      exam("new", null, "2026-10-17T10:00:00Z"),
      exam("eng-new", "ENGENG05", "2026-10-17T10:00:00Z"),
    ];

    expect(ids(examWorkspaceOpenGroups(documents, "course", [], courseName))).toEqual([
      ["Engelska 5", ["eng-new", "eng-old"]],
      ["Utan kurs", ["new", "old"]],
    ]);
  });

  it("names a course the catalog does not know by its key instead of dropping its exams", () => {
    const groups = examWorkspaceOpenGroups([exam("a", "OKÄND01", "2026-10-17T10:00:00Z")], "course", [], courseName);

    expect(ids(groups)).toEqual([["OKÄND01", ["a"]]]);
  });

  it("lists every exam in one newest-first list for Senaste, ignoring course", () => {
    const documents = [
      exam("a", "ENGENG05", "2026-10-01T10:00:00Z"),
      exam("b", null, "2026-10-17T10:00:00Z"),
      exam("c", "SVESVE01", "2026-10-09T10:00:00Z"),
    ];

    expect(ids(examWorkspaceOpenGroups(documents, "newest", ["SVESVE01"], courseName))).toEqual([
      [null, ["b", "c", "a"]],
    ]);
  });

  it("returns no group at all when there are no exams", () => {
    expect(examWorkspaceOpenGroups([], "newest", [], courseName)).toEqual([]);
    expect(examWorkspaceOpenGroups([], "course", [], courseName)).toEqual([]);
  });
});
