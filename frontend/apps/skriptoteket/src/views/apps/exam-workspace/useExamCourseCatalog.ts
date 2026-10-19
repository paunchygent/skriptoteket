/** Shared immutable catalog, actor-bound preferences and browser-only search. */
import { effectScope, ref, watch, type EffectScope } from "vue";

import type { ExamCourse } from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";

const courses = ref<ExamCourse[]>([]);
const registeredCourseKeys = ref<string[]>([]);
const isLoading = ref(false);
const error = ref<string | null>(null);
let preferenceRevision = 0;
let observedAuth: ReturnType<typeof useAuthStore> | null = null;
let identityScope: EffectScope | null = null;

function bindActor(auth: ReturnType<typeof useAuthStore>, shared: ExamWorkspaceSharedStore): void {
  if (observedAuth === auth) return;
  identityScope?.stop();
  observedAuth = auth;
  // Outlive individual consumers so logout invalidates pending responses even
  // when the profile/workspace has unmounted. One watcher per auth store.
  identityScope = effectScope(true);
  identityScope.run(() => watch(() => auth.actorSession, () => {
    registeredCourseKeys.value = [];
    error.value = null;
    isLoading.value = false;
    if (auth.user === null) return;

    isLoading.value = true;
    const requestSession = auth.captureSession();
    const requestPreferenceRevision = preferenceRevision;
    void shared.getExamCourseCatalog().then((response) => {
      if (!auth.isCurrentSession(requestSession)) return;
      courses.value = response.courses;
      if (preferenceRevision === requestPreferenceRevision) {
        registeredCourseKeys.value = response.registered_course_keys;
      }
    }).catch(() => {
      if (!auth.isCurrentSession(requestSession)) return;
      error.value = "Det gick inte att hämta kurserna. Ladda om sidan och försök igen.";
    }).finally(() => {
      if (auth.isCurrentSession(requestSession)) isLoading.value = false;
    });
  }, { immediate: true, flush: "sync" }));
}

function normalize(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase("sv-SE")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

/** Every query token must prefix a name or code token; no text-specific rules. */
export function searchCourses(
  catalog: readonly ExamCourse[],
  query: string,
  limit = 50,
  registeredKeys: readonly string[] = registeredCourseKeys.value,
): ExamCourse[] {
  const positions = new Map(registeredKeys.map((key, index) => [key, index]));
  const normalized = normalize(query);
  const queryTokens = normalized ? normalized.split(/\s+/u) : [];
  return catalog.map((course) => {
    const name = normalize(course.name);
    const code = normalize(course.code);
    const tokens = `${name} ${code}`.split(/\s+/u);
    const matches = queryTokens.every((queryToken) => tokens.some((token) => token.startsWith(queryToken)));
    const rank = name === normalized ? 0 : name.startsWith(normalized) ? 1
      : queryTokens.length > 0 && queryTokens.every((token) => code.startsWith(token)) ? 2 : 3;
    return { course, matches, rank };
  }).filter((entry) => entry.matches)
    .sort((a, b) =>
      (positions.get(a.course.key) ?? positions.size) - (positions.get(b.course.key) ?? positions.size)
      || a.rank - b.rank || a.course.name.localeCompare(b.course.name, "sv"))
    .slice(0, Math.max(0, limit))
    .map((entry) => entry.course);
}

export function useExamCourseCatalog(shared: ExamWorkspaceSharedStore) {
  const auth = useAuthStore();
  bindActor(auth, shared);
  const consumerSession = auth.captureSession();

  function courseByKey(key: string | null): ExamCourse | null {
    return courses.value.find((course) => course.key === key) ?? null;
  }

  function setRegisteredCourseKeys(keys: readonly string[]): void {
    if (auth.user === null || !auth.isCurrentSession(consumerSession)) return;
    preferenceRevision += 1;
    registeredCourseKeys.value = [...keys];
  }

  return { courses, registeredCourseKeys, isLoading, error, courseByKey, setRegisteredCourseKeys };
}
