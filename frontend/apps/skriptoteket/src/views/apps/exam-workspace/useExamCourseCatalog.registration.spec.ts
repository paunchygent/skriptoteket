import { describe, expect, it } from "vitest";

import type { ExamCourse } from "../../../api/examWorkspace";
import { searchCourses } from "./useExamCourseCatalog";

const COURSES: ExamCourse[] = [
  { key: "gy11:SVESVE01", code: "SVESVE01", name: "Svenska 1", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska" },
  { key: "gy11:SVESVE02", code: "SVESVE02", name: "Svenska 2", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska" },
  { key: "gy25:SVEN2000X", code: "SVEN2000X", name: "Svenska nivå 2", school_form: "gymnasiet", reform: "GY25", subject_code: "SVEN", subject_name: "Svenska" },
  { key: "gr:GRGRMAT01:7-9", code: "GRGRMAT01", name: "Matematik, åk 7–9", school_form: "grundskolan", subject_code: "GRGRMAT01", subject_name: "Matematik", year_band: "7-9", year_band_label: "åk 7–9" },
];

const REGISTERED = ["gy25:SVEN2000X", "gy11:SVESVE02"];

function keys(courses: ExamCourse[]): string[] {
  return courses.map((course) => course.key);
}

describe("registered course search priority", () => {
  it("uses profile order ahead of alphabetic order and applies the result limit afterward", () => {
    expect(keys(searchCourses(COURSES, "", 3, REGISTERED))).toEqual([
      "gy25:SVEN2000X", "gy11:SVESVE02", "gr:GRGRMAT01:7-9",
    ]);
    expect(keys(searchCourses(COURSES, "", 1, REGISTERED))).toEqual(["gy25:SVEN2000X"]);
  });

  it("prioritizes registered matches over a closer unregistered text match without expanding the matcher", () => {
    expect(keys(searchCourses(COURSES, "Svenska", 50, REGISTERED))).toEqual([
      "gy25:SVEN2000X", "gy11:SVESVE02", "gy11:SVESVE01",
    ]);
    expect(keys(searchCourses(COURSES, "Svenska 2", 50, ["gy25:SVEN2000X"]))).toEqual([
      "gy25:SVEN2000X", "gy11:SVESVE02",
    ]);
    expect(keys(searchCourses(COURSES, "Svenska 1", 50, REGISTERED))).toEqual(["gy11:SVESVE01"]);
    expect(searchCourses(COURSES, "venska", 50, REGISTERED)).toEqual([]);
  });

  it("searches unregistered school forms and leaves caller-owned catalog and preference arrays unchanged", () => {
    const catalog = Object.freeze([...COURSES]);
    const registered = Object.freeze([...REGISTERED]);
    expect(keys(searchCourses(catalog, "åk 7—9", 50, registered))).toEqual(["gr:GRGRMAT01:7-9"]);
    expect(catalog).toEqual(COURSES);
    expect(registered).toEqual(REGISTERED);
  });
});
