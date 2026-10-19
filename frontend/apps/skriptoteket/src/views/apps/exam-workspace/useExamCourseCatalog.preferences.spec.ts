import { flushPromises } from "@vue/test-utils";
import { beforeEach, expect, it, vi } from "vitest";

import { getExamCourseCatalog, type ExamCourse } from "../../../api/examWorkspace";

import { serverExamWorkspaceStore } from "./examWorkspaceStore";

vi.mock("../../../api/examWorkspace", () => ({ getExamCourseCatalog: vi.fn() }));

const COURSES: ExamCourse[] = [
  { key: "SVESVE01", code: "SVESVE01", name: "Svenska 1", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska" },
  { key: "SVESVE02", code: "SVESVE02", name: "Svenska 2", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska" },
];

let auth: ReturnType<typeof import("../../../stores/auth")["useAuthStore"]>;

function setActor(id: string | null): void {
  auth.user = id === null ? null : {
    id, email: `${id}@example.test`, role: "user", auth_provider: "local",
  };
}

beforeEach(async () => {
  vi.resetModules();
  vi.mocked(getExamCourseCatalog).mockReset();
  const { createPinia, setActivePinia } = await import("pinia");
  setActivePinia(createPinia());
  const { useAuthStore } = await import("../../../stores/auth");
  auth = useAuthStore();
  setActor("teacher-a");
});

it("existing three-argument workspace search uses loaded preferences and a later profile save", async () => {
  vi.mocked(getExamCourseCatalog).mockResolvedValue({
    courses: COURSES, generated_at: "2026-10-17", registered_course_keys: ["SVESVE02"],
  });
  const { useExamCourseCatalog, searchCourses } = await import("./useExamCourseCatalog");
  const profileConsumer = useExamCourseCatalog(serverExamWorkspaceStore.shared);
  await flushPromises();
  expect(searchCourses(profileConsumer.courses.value, "", 1)[0]?.key).toBe("SVESVE02");

  profileConsumer.setRegisteredCourseKeys(["SVESVE01"]);
  const workspaceConsumer = useExamCourseCatalog(serverExamWorkspaceStore.shared);
  expect(searchCourses(workspaceConsumer.courses.value, "Svenska", 1)[0]?.key).toBe("SVESVE01");
  expect(getExamCourseCatalog).toHaveBeenCalledTimes(1);
});

it("a late catalog response cannot restore preferences replaced by a successful profile save", async () => {
  let resolve!: (response: Awaited<ReturnType<typeof getExamCourseCatalog>>) => void;
  vi.mocked(getExamCourseCatalog).mockReturnValue(new Promise((done) => { resolve = done; }));
  const { useExamCourseCatalog, searchCourses } = await import("./useExamCourseCatalog");
  const profileConsumer = useExamCourseCatalog(serverExamWorkspaceStore.shared);
  profileConsumer.setRegisteredCourseKeys([]);
  resolve({ courses: COURSES, generated_at: "2026-10-17", registered_course_keys: ["SVESVE02"] });
  await flushPromises();

  expect(searchCourses(profileConsumer.courses.value, "", 1)[0]?.key).toBe("SVESVE01");
  expect(profileConsumer.registeredCourseKeys.value).toEqual([]);
});

it("clears teacher A's saved ranking on identity replacement and logout without reloading the module", async () => {
  vi.mocked(getExamCourseCatalog)
    .mockResolvedValueOnce({ courses: COURSES, generated_at: "2026-10-17", registered_course_keys: ["SVESVE02"] })
    .mockResolvedValueOnce({ courses: COURSES, generated_at: "2026-10-17", registered_course_keys: ["SVESVE01"] });
  const { useExamCourseCatalog, searchCourses } = await import("./useExamCourseCatalog");
  const consumer = useExamCourseCatalog(serverExamWorkspaceStore.shared);
  await flushPromises();
  expect(consumer.registeredCourseKeys.value).toEqual(["SVESVE02"]);

  setActor("teacher-b");
  expect(consumer.registeredCourseKeys.value).toEqual([]);
  useExamCourseCatalog(serverExamWorkspaceStore.shared);
  await flushPromises();
  expect(searchCourses(consumer.courses.value, "", 1)[0]?.key).toBe("SVESVE01");
  expect(consumer.registeredCourseKeys.value).toEqual(["SVESVE01"]);

  const requestCount = vi.mocked(getExamCourseCatalog).mock.calls.length;
  for (const query of ["S", "Sv", "Sve", "Svenska"]) {
    searchCourses(consumer.courses.value, query);
  }
  expect(getExamCourseCatalog).toHaveBeenCalledTimes(requestCount);
  setActor(null);
  expect(consumer.registeredCourseKeys.value).toEqual([]);
});

it("rejects teacher A's pending response after teacher B's preference has loaded", async () => {
  let resolveOld!: (response: Awaited<ReturnType<typeof getExamCourseCatalog>>) => void;
  vi.mocked(getExamCourseCatalog)
    .mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }))
    .mockResolvedValueOnce({ courses: COURSES, generated_at: "2026-10-17", registered_course_keys: ["SVESVE01"] });
  const { useExamCourseCatalog } = await import("./useExamCourseCatalog");
  const original = useExamCourseCatalog(serverExamWorkspaceStore.shared);
  setActor("teacher-b");
  const replacement = useExamCourseCatalog(serverExamWorkspaceStore.shared);
  await flushPromises();
  expect(replacement.registeredCourseKeys.value).toEqual(["SVESVE01"]);

  resolveOld({ courses: COURSES, generated_at: "2026-10-17", registered_course_keys: ["SVESVE02"] });
  await flushPromises();
  expect(replacement.registeredCourseKeys.value).toEqual(["SVESVE01"]);
  original.setRegisteredCourseKeys(["SVESVE02"]);
  expect(replacement.registeredCourseKeys.value).toEqual(["SVESVE01"]);
});

it("rejects a prior login's pending response even when the same teacher signs in again", async () => {
  let resolveOld!: (response: Awaited<ReturnType<typeof getExamCourseCatalog>>) => void;
  vi.mocked(getExamCourseCatalog)
    .mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }))
    .mockResolvedValueOnce({ courses: COURSES, generated_at: "2026-10-17", registered_course_keys: ["SVESVE01"] });
  const { useExamCourseCatalog } = await import("./useExamCourseCatalog");
  const consumer = useExamCourseCatalog(serverExamWorkspaceStore.shared);
  setActor(null);
  setActor("teacher-a");
  useExamCourseCatalog(serverExamWorkspaceStore.shared);
  await flushPromises();
  resolveOld({ courses: COURSES, generated_at: "2026-10-17", registered_course_keys: ["SVESVE02"] });
  await flushPromises();
  expect(consumer.registeredCourseKeys.value).toEqual(["SVESVE01"]);
});

it("does not restore preferences or start an anonymous request after logout", async () => {
  let resolveOld!: (response: Awaited<ReturnType<typeof getExamCourseCatalog>>) => void;
  vi.mocked(getExamCourseCatalog).mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }));
  const { useExamCourseCatalog } = await import("./useExamCourseCatalog");
  const consumer = useExamCourseCatalog(serverExamWorkspaceStore.shared);
  setActor(null);
  useExamCourseCatalog(serverExamWorkspaceStore.shared);
  resolveOld({ courses: COURSES, generated_at: "2026-10-17", registered_course_keys: ["SVESVE02"] });
  await flushPromises();
  expect(consumer.registeredCourseKeys.value).toEqual([]);
  expect(getExamCourseCatalog).toHaveBeenCalledTimes(1);
});
