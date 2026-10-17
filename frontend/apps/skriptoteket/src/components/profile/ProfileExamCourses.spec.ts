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

it("adds gymnasiet and subject-band entries in selection order, removes one, and saves keys only", async () => {
  const { default: ProfileExamCourses } = await import("./ProfileExamCourses.vue");
  const wrapper = mount(ProfileExamCourses, {
    props: { examCourses: { school_forms: [], course_keys: [] } },
  });
  await flushPromises();
  await wrapper.get('[data-test="profile-school-form-gymnasiet"] input').setValue(true);
  await wrapper.get('[data-test="profile-school-form-grundskolan"] input').setValue(true);
  const picker = wrapper.get('[role="combobox"]');
  await picker.setValue("Svenska 1");
  await wrapper.get('[role="option"]').trigger("click");
  await wrapper.get('[aria-label="Lägg till kurs"]').trigger("click");
  await picker.setValue("åk 7-9");
  await wrapper.get('[role="option"]').trigger("click");
  await wrapper.get('[aria-label="Lägg till kurs"]').trigger("click");

  const rows = wrapper.findAll("ol li");
  expect(rows).toHaveLength(2);
  expect(rows[0]!.text()).toContain("Svenska 1");
  expect(rows[0]!.text()).toContain("SVESVE01");
  expect(rows[0]!.text()).toContain("Gymnasiet");
  expect(rows[1]!.text()).toContain("Matematik, åk 7–9");
  expect(rows[1]!.text()).toContain("Grundskolan");
  await wrapper.get('[aria-label="Ta bort Svenska 1"]').trigger("click");
  await wrapper.get('[data-test="profile-courses-save"]').trigger("click");
  await flushPromises();

  expect(updateExamCourses).toHaveBeenCalledWith({
    school_forms: ["gymnasiet", "grundskolan"], course_keys: ["GRGRMAT01/7-9"],
  });
  expect(wrapper.emitted("profileUpdated")).toHaveLength(1);
  const { searchCourses } = await import("../../views/apps/exam-workspace/useExamCourseCatalog");
  expect(searchCourses(COURSES, "", 1)[0]?.key).toBe("GRGRMAT01/7-9");
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

it("keeps an unsaved removal and reports no success when saving fails, then permits retry", async () => {
  const { default: ProfileExamCourses } = await import("./ProfileExamCourses.vue");
  const wrapper = mount(ProfileExamCourses, {
    props: { examCourses: { school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] } },
  });
  await flushPromises();
  await wrapper.get('[aria-label="Ta bort Svenska 1"]').trigger("click");
  updateExamCourses.mockRejectedValueOnce(new Error("Network unavailable"));
  await wrapper.get('[data-test="profile-courses-save"]').trigger("click");
  await flushPromises();
  expect(wrapper.findAll("ol li")).toHaveLength(0);
  expect(wrapper.emitted("profileUpdated")).toBeUndefined();
  expect(failure).toHaveBeenCalledTimes(1);
  expect(success).not.toHaveBeenCalled();

  await wrapper.get('[data-test="profile-courses-save"]').trigger("click");
  await flushPromises();
  expect(updateExamCourses).toHaveBeenLastCalledWith({ school_forms: ["gymnasiet"], course_keys: [] });
  expect(wrapper.emitted("profileUpdated")).toHaveLength(1);
  wrapper.unmount();
});
