import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, expect, it, vi } from "vitest";

import { getExamCourseCatalog, type ExamCourse } from "../../api/examWorkspace";

const { updateExamCourses, success, failure } = vi.hoisted(() => ({
  updateExamCourses: vi.fn(), success: vi.fn(), failure: vi.fn(),
}));
vi.mock("../../api/examWorkspace", () => ({ getExamCourseCatalog: vi.fn() }));
vi.mock("../../composables/useProfile", () => ({
  EXAM_COURSE_SCHOOL_FORMS: ["gymnasiet", "grundskolan"],
  useProfile: () => ({ updateExamCourses }),
}));
vi.mock("../../composables/useToast", () => ({ useToast: () => ({ success, failure }) }));

const COURSES: ExamCourse[] = [
  { key: "ENGENG05", code: "ENGENG05", name: "Engelska 5", school_form: "gymnasiet", reform: "GY11", subject_code: "ENG", subject_name: "Engelska" },
  { key: "SVESVE01", code: "SVESVE01", name: "Svenska 1", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska" },
  { key: "GRGRMAT01/7-9", code: "GRGRMAT01", name: "Matematik, åk 7–9", school_form: "grundskolan", subject_code: "GRGRMAT01", subject_name: "Matematik", year_band: "7-9", year_band_label: "åk 7–9" },
];

beforeEach(async () => {
  vi.resetModules();
  vi.clearAllMocks();
  const { createPinia, setActivePinia } = await import("pinia");
  setActivePinia(createPinia());
  const { useAuthStore } = await import("../../stores/auth");
  useAuthStore().user = {
    id: "f13c4ea9-8247-47e9-b212-c047714c1648", email: "teacher@example.test",
    role: "user", auth_provider: "huleedu",
  };
  vi.mocked(getExamCourseCatalog).mockResolvedValue({
    courses: COURSES, generated_at: "2026-10-17", registered_course_keys: [],
  });
  updateExamCourses.mockImplementation(async (payload: { school_forms: string[]; course_keys: string[] }) => ({
    user: {
      id: "f13c4ea9-8247-47e9-b212-c047714c1648", email: "teacher@example.test",
      role: "user", auth_provider: "huleedu", is_active: true, email_verified: true,
      failed_login_attempts: 0, created_at: "2026-10-17T10:00:00Z", updated_at: "2026-10-17T10:00:00Z",
    },
    profile: {
      user_id: "f13c4ea9-8247-47e9-b212-c047714c1648", locale: "sv-SE",
      created_at: "2026-10-17T10:00:00Z", updated_at: "2026-10-17T10:00:00Z",
      exam_courses: { school_forms: [...payload.school_forms], course_keys: [...payload.course_keys] },
    },
  }));
});

async function mountCourses(examCourses: { school_forms: ("gymnasiet" | "grundskolan")[]; course_keys: string[] }) {
  const { default: ProfileExamCourses } = await import("./ProfileExamCourses.vue");
  const wrapper = mount(ProfileExamCourses, { props: { examCourses } });
  await flushPromises();
  return wrapper;
}

async function choose(wrapper: Awaited<ReturnType<typeof mountCourses>>, query: string) {
  const picker = wrapper.get('[role="combobox"]');
  await picker.trigger("focus");
  await picker.setValue(query);
  await wrapper.get('[role="option"]').trigger("click");
}

function deferred() {
  let resolve!: () => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<void>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

it("adds a chosen course at once, clears the search box and saves without a second step", async () => {
  const wrapper = await mountCourses({ school_forms: [], course_keys: [] });

  expect(wrapper.find('[aria-label="Lägg till kurs"]').exists()).toBe(false);
  expect(wrapper.find('[data-test="profile-courses-save"]').exists()).toBe(false);
  await choose(wrapper, "Svenska 1");
  await flushPromises();

  const rows = wrapper.findAll("ol li");
  expect(rows).toHaveLength(1);
  expect(rows[0]!.text()).toContain("Svenska 1");
  expect(rows[0]!.text()).toContain("SVESVE01");
  expect((wrapper.get('[role="combobox"]').element as HTMLInputElement).value).toBe("");
  expect(updateExamCourses).toHaveBeenCalledTimes(1);
  expect(updateExamCourses).toHaveBeenCalledWith({ school_forms: [], course_keys: ["SVESVE01"] });
  expect(wrapper.get('[data-test="profile-courses-status"]').text()).toBe("Sparat");
  expect(success).not.toHaveBeenCalled();
  expect(failure).not.toHaveBeenCalled();
  expect(wrapper.emitted("profileUpdated")).toBeUndefined();

  await choose(wrapper, "åk 7-9");
  await flushPromises();
  await wrapper.get('[data-test="profile-school-form-grundskolan"] input').setValue(true);
  await flushPromises();
  await wrapper.get('[data-test="profile-school-form-gymnasiet"] input').setValue(true);
  await flushPromises();
  await wrapper.get('[aria-label="Ta bort Svenska 1"]').trigger("click");
  await flushPromises();

  expect(updateExamCourses).toHaveBeenCalledTimes(5);
  expect(updateExamCourses).toHaveBeenLastCalledWith({
    school_forms: ["gymnasiet", "grundskolan"], course_keys: ["GRGRMAT01/7-9"],
  });
  expect(wrapper.findAll("ol li").map((row) => row.text())).toEqual([
    expect.stringContaining("Matematik, åk 7–9"),
  ]);
  expect(success).not.toHaveBeenCalled();
  const { searchCourses } = await import("../../views/apps/exam-workspace/useExamCourseCatalog");
  expect(searchCourses(COURSES, "", 1)[0]?.key).toBe("GRGRMAT01/7-9");
  wrapper.unmount();
});

it("ignores a course that is already listed and sends no save for it", async () => {
  const wrapper = await mountCourses({ school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] });

  await choose(wrapper, "Svenska 1");
  await flushPromises();

  expect(wrapper.findAll("ol li")).toHaveLength(1);
  expect(updateExamCourses).not.toHaveBeenCalled();
  expect((wrapper.get('[role="combobox"]').element as HTMLInputElement).value).toBe("");
  wrapper.unmount();
});

it("restores the last saved list and school forms and toasts when a save fails", async () => {
  const wrapper = await mountCourses({ school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] });
  const failing = deferred();
  updateExamCourses.mockImplementationOnce(() => failing.promise);

  await wrapper.get('[aria-label="Ta bort Svenska 1"]').trigger("click");
  expect(wrapper.findAll("ol li")).toHaveLength(0);
  failing.reject(new Error("Network unavailable"));
  await flushPromises();

  expect(wrapper.findAll("ol li").map((row) => row.text())).toEqual([expect.stringContaining("Svenska 1")]);
  expect((wrapper.get('[data-test="profile-school-form-gymnasiet"] input').element as HTMLInputElement).checked).toBe(true);
  expect(failure).toHaveBeenCalledTimes(1);
  expect(failure).toHaveBeenCalledWith("Kunde inte spara.");
  expect(success).not.toHaveBeenCalled();
  expect(wrapper.get('[data-test="profile-courses-status"]').text()).toBe("");

  await wrapper.get('[aria-label="Ta bort Svenska 1"]').trigger("click");
  await flushPromises();
  expect(updateExamCourses).toHaveBeenLastCalledWith({ school_forms: ["gymnasiet"], course_keys: [] });
  expect(wrapper.findAll("ol li")).toHaveLength(0);
  expect(failure).toHaveBeenCalledTimes(1);
  wrapper.unmount();
});

it("waits for a running save, then saves every later change in one request with the latest value", async () => {
  const wrapper = await mountCourses({ school_forms: [], course_keys: ["ENGENG05", "SVESVE01"] });
  const first = deferred();
  const save = updateExamCourses.getMockImplementation()!;
  updateExamCourses.mockImplementationOnce(async (payload) => { await first.promise; return save(payload); });

  await wrapper.get('[aria-label="Ta bort Engelska 5"]').trigger("click");
  await wrapper.get('[aria-label="Ta bort Svenska 1"]').trigger("click");
  await wrapper.get('[data-test="profile-school-form-gymnasiet"] input').setValue(true);
  await flushPromises();
  expect(updateExamCourses).toHaveBeenCalledTimes(1);
  expect(updateExamCourses).toHaveBeenLastCalledWith({ school_forms: [], course_keys: ["SVESVE01"] });
  expect(wrapper.get('[data-test="profile-courses-status"]').text()).toBe("Sparar…");

  // A profile reload that lands mid-save must not replace the unsaved changes.
  await wrapper.setProps({ examCourses: { school_forms: [], course_keys: ["ENGENG05", "SVESVE01"] } });
  expect(wrapper.findAll("ol li")).toHaveLength(0);

  first.resolve();
  await flushPromises();
  expect(updateExamCourses).toHaveBeenCalledTimes(2);
  expect(updateExamCourses).toHaveBeenLastCalledWith({ school_forms: ["gymnasiet"], course_keys: [] });
  expect(wrapper.findAll("ol li")).toHaveLength(0);
  expect(wrapper.get('[data-test="profile-courses-status"]').text()).toBe("Sparat");
  wrapper.unmount();
});

it("rolls back changes queued behind a failed save and does not send them", async () => {
  const wrapper = await mountCourses({ school_forms: [], course_keys: ["ENGENG05", "SVESVE01"] });
  const first = deferred();
  updateExamCourses.mockImplementationOnce(() => first.promise);

  await wrapper.get('[aria-label="Ta bort Engelska 5"]').trigger("click");
  await wrapper.get('[aria-label="Ta bort Svenska 1"]').trigger("click");
  first.reject(new Error("Network unavailable"));
  await flushPromises();

  expect(updateExamCourses).toHaveBeenCalledTimes(1);
  expect(wrapper.findAll("ol li")).toHaveLength(2);
  expect(failure).toHaveBeenCalledTimes(1);
  wrapper.unmount();
});

it("keeps the package-sized remove control non-shrinking beside a long course label", async () => {
  const longName = "Svenska med fördjupning i språk, litteratur och vetenskaplig kommunikation";
  vi.mocked(getExamCourseCatalog).mockResolvedValue({
    courses: [{ ...COURSES[1]!, name: longName }],
    generated_at: "2026-10-17",
    registered_course_keys: ["SVESVE01"],
  });
  const { default: ProfileExamCourses } = await import("./ProfileExamCourses.vue");
  const wrapper = mount(ProfileExamCourses, {
    props: { examCourses: { school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] } },
  });
  await flushPromises();

  expect(wrapper.get("ol li span").text()).toContain(longName);
  const remove = wrapper.get('[data-test="profile-course-remove"]');
  expect(remove.attributes("aria-label")).toBe(`Ta bort ${longName}`);
  expect(remove.classes()).toContain("shrink-0");
  expect(remove.classes()).toEqual(expect.arrayContaining(["h-9", "w-9"]));
  wrapper.unmount();
});
