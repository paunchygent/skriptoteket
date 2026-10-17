import { ref } from "vue";

import { apiFetch, apiGet } from "../api/client";
import type { components } from "../api/openapi";
import { SupersededAuthSessionError, useAuthStore } from "../stores/auth";

type UserProfile = components["schemas"]["UserProfile"];
type ProfileResponse = components["schemas"]["ProfileResponse"];

/** School forms a teacher can record for their own exam courses. */
export const EXAM_COURSE_SCHOOL_FORMS: readonly ExamCourseSchoolForm[] = [
  "gymnasiet",
  "grundskolan",
];

export type ExamCourseSchoolForm =
  components["schemas"]["UpdateExamCoursesRequest"]["school_forms"][number];

/**
 * The teacher's recorded school forms and ordered catalog keys, sent as one
 * full-replacement value. The catalog key is the only identity; names resolve
 * from the committed catalog.
 */
export type ProfileExamCourses = components["schemas"]["UpdateExamCoursesRequest"];

type UpdateProfilePayload = {
  first_name?: string | null;
  last_name?: string | null;
  display_name?: string | null;
  locale?: string | null;
};

export function useProfile() {
  const auth = useAuthStore();
  const profile = ref<UserProfile | null>(null);

  async function load(): Promise<ProfileResponse> {
    const session = auth.captureSession();
    const response = await apiGet<ProfileResponse>("/api/v1/profile", { session });
    if (!auth.applyResponse(session, response)) throw new SupersededAuthSessionError();
    profile.value = response.profile;
    return response;
  }

  async function updateProfile(
    payload: UpdateProfilePayload,
  ): Promise<ProfileResponse> {
    const session = auth.captureSession();
    const response = await apiFetch<ProfileResponse>("/api/v1/profile", {
      session,
      method: "PATCH",
      body: payload,
    });
    if (!auth.applyResponse(session, response)) throw new SupersededAuthSessionError();
    profile.value = response.profile;
    return response;
  }

  /** Full replacement of the teacher's recorded school forms and course keys. */
  async function updateExamCourses(
    examCourses: ProfileExamCourses,
  ): Promise<ProfileResponse> {
    const session = auth.captureSession();
    const response = await apiFetch<ProfileResponse>(
      "/api/v1/profile/exam-courses",
      {
        session,
        method: "PATCH",
        body: examCourses,
      },
    );
    if (!auth.applyResponse(session, response)) throw new SupersededAuthSessionError();
    profile.value = response.profile;
    return response;
  }

  return {
    profile,
    load,
    updateProfile,
    updateExamCourses,
  };
}
