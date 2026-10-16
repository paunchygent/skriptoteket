import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getExamCourseCatalog, type ExamCourse } from "../../../api/examWorkspace";

vi.mock("../../../api/examWorkspace", () => ({ getExamCourseCatalog: vi.fn() }));

const COURSES: ExamCourse[] = [
  { key: "gy11:SVESVE02", code: "SVESVE02", name: "Svenska 2", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska" },
  { key: "gy25:SVEN2000X", code: "SVEN2000X", name: "Svenska nivå 2", school_form: "gymnasiet", reform: "GY25", subject_code: "SVEN", subject_name: "Svenska" },
  { key: "gy11:SVESVE01", code: "SVESVE01", name: "Svenska 1", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska" },
  { key: "gr:GRGRMAT01:7-9", code: "GRGRMAT01", name: "Matematik, åk 7–9", school_form: "grundskolan", subject_code: "GRGRMAT01", subject_name: "Matematik", year_band: "7-9", year_band_label: "åk 7–9" },
];

beforeEach(() => {
  vi.resetModules();
  vi.mocked(getExamCourseCatalog).mockReset();
});

describe("searchCourses", () => {
  it.each([
    ["sve 2", ["gy11:SVESVE02", "gy25:SVEN2000X"]],
    ["SVESVE02", ["gy11:SVESVE02"]],
    [" ÅK   7-9 ", ["gr:GRGRMAT01:7-9"]],
    ["åk 7—9", ["gr:GRGRMAT01:7-9"]],
    ["venska", []],
    ["sve 3", []],
    ["gymnasiet", []],
  ])("searches name/code token prefixes for %j, without synonyms or substring guessing", async (query, expected) => {
    const { searchCourses } = await import("./useExamCourseCatalog");
    expect(searchCourses(COURSES, query, 50).map((course) => course.key)).toEqual(expected);
  });

  it("ranks exact name before name prefix, code match, then other token matches", async () => {
    const { searchCourses } = await import("./useExamCourseCatalog");
    // Synthetic ranking probe: deliberately scrambled to defeat source-order sorting.
    const ranked: ExamCourse[] = [
      { ...COURSES[0]!, key: "other", name: "Tillämpad svenska", code: "ZZ01" },
      { ...COURSES[0]!, key: "code", name: "Algebra", code: "SVENSKA01" },
      { ...COURSES[0]!, key: "prefix", name: "Svenska 2", code: "ZZ02" },
      { ...COURSES[0]!, key: "exact", name: "Svenska", code: "ZZ03" },
      { ...COURSES[0]!, key: "prefix-first", name: "Svenska 1", code: "ZZ04" },
    ];
    expect(searchCourses(ranked, "svenska", 50).map((course) => course.key))
      .toEqual(["exact", "prefix-first", "prefix", "code", "other"]);
    expect(searchCourses(ranked, "svenska", 2).map((course) => course.key))
      .toEqual(["exact", "prefix-first"]);
    expect(ranked.map((course) => course.key)).toEqual(["other", "code", "prefix", "exact", "prefix-first"]);
  });

  it("orders an empty-query catalog by name and respects a zero limit", async () => {
    const { searchCourses } = await import("./useExamCourseCatalog");
    expect(searchCourses(COURSES, "  ", 2).map((course) => course.key))
      .toEqual(["gr:GRGRMAT01:7-9", "gy11:SVESVE01"]);
    expect(searchCourses(COURSES, "sve", 0)).toEqual([]);
  });
});

describe("useExamCourseCatalog", () => {
  it("shares one pending request across concurrent consumers and later consumers", async () => {
    let finish!: (value: Awaited<ReturnType<typeof getExamCourseCatalog>>) => void;
    vi.mocked(getExamCourseCatalog).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const { useExamCourseCatalog } = await import("./useExamCourseCatalog");
    const first = useExamCourseCatalog();
    const second = useExamCourseCatalog();
    expect(first.isLoading.value).toBe(true);
    expect(second.isLoading.value).toBe(true);
    expect(getExamCourseCatalog).toHaveBeenCalledTimes(1);
    finish({ courses: COURSES, generated_at: "2026-10-16T17:00:00Z" });
    await flushPromises();
    for (const consumer of [first, second, useExamCourseCatalog()]) {
      expect(consumer.isLoading.value).toBe(false);
      expect(consumer.error.value).toBeFalsy();
      expect(consumer.courses.value).toEqual(COURSES);
      expect(consumer.courseByKey("gy11:SVESVE02")).toEqual(COURSES[0]);
      expect(consumer.courseByKey("absent")).toBeFalsy();
    }
    expect(getExamCourseCatalog).toHaveBeenCalledTimes(1);
  });

  it("settles loading and exposes a failed request to every consumer without an unhandled rejection", async () => {
    vi.mocked(getExamCourseCatalog).mockRejectedValue(new Error("Catalog unavailable"));
    const { useExamCourseCatalog } = await import("./useExamCourseCatalog");
    const first = useExamCourseCatalog();
    const second = useExamCourseCatalog();
    await flushPromises();
    for (const consumer of [first, second]) {
      expect(consumer.isLoading.value).toBe(false);
      expect(consumer.error.value).toBeTruthy();
      expect(consumer.courses.value).toEqual([]);
    }
    expect(getExamCourseCatalog).toHaveBeenCalledTimes(1);
  });
});
