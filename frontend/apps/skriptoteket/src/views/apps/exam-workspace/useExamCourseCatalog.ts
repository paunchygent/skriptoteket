/** Page-local catalog loading and browser-only course search. */
import { ref } from "vue";

import { getExamCourseCatalog, type ExamCourse } from "../../../api/examWorkspace";

const courses = ref<ExamCourse[]>([]);
const isLoading = ref(false);
const error = ref<string | null>(null);
let catalogPromise: Promise<void> | null = null;

function normalize(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase("sv-SE")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

/** Every query token must prefix a name or code token; no text-specific rules. */
export function searchCourses(
  catalog: readonly ExamCourse[],
  query: string,
  limit = 50,
): ExamCourse[] {
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
    .sort((a, b) => a.rank - b.rank || a.course.name.localeCompare(b.course.name, "sv"))
    .slice(0, Math.max(0, limit))
    .map((entry) => entry.course);
}

export function useExamCourseCatalog() {
  if (!catalogPromise) {
    isLoading.value = true;
    catalogPromise = getExamCourseCatalog().then((response) => {
      courses.value = response.courses;
    }).catch(() => {
      error.value = "Det gick inte att hämta kurserna. Ladda om sidan och försök igen.";
    }).finally(() => {
      isLoading.value = false;
    });
  }

  function courseByKey(key: string | null): ExamCourse | null {
    return courses.value.find((course) => course.key === key) ?? null;
  }

  return { courses, isLoading, error, courseByKey };
}
