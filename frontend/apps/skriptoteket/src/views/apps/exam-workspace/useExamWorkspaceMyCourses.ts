/**
 * Exam workspace "Lägg till i mina kurser".
 *
 * Domain purpose:
 *   Add the exam's course to the teacher's own courses from Provets
 *   uppgifter, so it comes first in course lists and in Öppna. The profile
 *   route replaces the whole list, so the current school forms and courses
 *   are read first and the course is added last, with its school form.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceDetailsDrawer`; writes through `useProfile` and
 *     tells `useExamCourseCatalog` the new order.
 */

import { ref } from "vue";

import type { ExamCourse } from "../../../api/examWorkspace";
import { useProfile } from "../../../composables/useProfile";
import { useToast } from "../../../composables/useToast";
import { useExamCourseCatalog } from "./useExamCourseCatalog";

const FAILURE_COPY = "Kursen kunde inte läggas till i dina kurser. Försök igen.";

export function useExamWorkspaceMyCourses() {
  const profile = useProfile();
  const toast = useToast();
  const { registeredCourseKeys, setRegisteredCourseKeys } = useExamCourseCatalog();
  const adding = ref(false);

  function isMine(courseKey: string | null): boolean {
    return courseKey !== null && registeredCourseKeys.value.includes(courseKey);
  }

  async function addCourse(course: ExamCourse): Promise<void> {
    if (adding.value || isMine(course.key)) return;
    adding.value = true;
    try {
      const current = (await profile.load()).profile.exam_courses;
      const schoolForms = current?.school_forms ?? [];
      const courseKeys = current?.course_keys ?? [];
      const response = await profile.updateExamCourses({
        course_keys: courseKeys.includes(course.key) ? courseKeys : [...courseKeys, course.key],
        school_forms: schoolForms.includes(course.school_form) ? schoolForms : [...schoolForms, course.school_form],
      });
      setRegisteredCourseKeys(response.profile.exam_courses?.course_keys ?? []);
    } catch {
      toast.failure(FAILURE_COPY);
    } finally {
      adding.value = false;
    }
  }

  return { adding, addCourse, isMine };
}
