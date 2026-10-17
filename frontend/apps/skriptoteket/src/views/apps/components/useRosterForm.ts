import { computed, ref, watch } from "vue";

import { apiDelete, apiPost, apiPut } from "../../../api/client";
import type { Roster, Student } from "../classroomPlannerTypes";

export interface RosterFormOptions {
  readonly roster?: Roster | null;
  saveRoster?: (payload: {
    existingRoster: Roster | null;
    name: string;
    students: Student[];
  }) => Promise<Roster>;
  deleteRoster?: (rosterId: string) => Promise<void>;
}

function buildStudentsForSubmit(lines: string[], existingStudents: Student[]): Student[] {
  const availableIdsByName = new Map<string, string[]>();

  for (const student of existingStudents) {
    const trimmedName = student.display_name.trim();
    const idsForName = availableIdsByName.get(trimmedName) ?? [];
    idsForName.push(student.id);
    availableIdsByName.set(trimmedName, idsForName);
  }

  return lines.map((displayName) => {
    const existingId = availableIdsByName.get(displayName)?.shift();
    return {
      id: existingId ?? crypto.randomUUID(),
      display_name: displayName,
    };
  });
}

export function useRosterForm(
  options: RosterFormOptions,
  events: { saved: (roster: Roster) => void; deleted: (id: string) => void },
) {
  const name = ref("");
  const rawStudents = ref("");
  const isSubmitting = ref(false);
  const isDeleting = ref(false);
  const formError = ref<string | null>(null);

  const isEditing = computed(() => Boolean(options.roster));

  watch(
    () => options.roster,
    (roster) => {
      name.value = roster?.name ?? "";
      rawStudents.value = roster?.students.map((student) => student.display_name).join("\n") ?? "";
      formError.value = null;
    },
    { immediate: true },
  );

  const parsedStudents = computed<Student[]>(() => {
    const lines = rawStudents.value
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    return buildStudentsForSubmit(lines, options.roster?.students ?? []);
  });

  const isValid = computed(() => {
    return name.value.trim().length > 0 && parsedStudents.value.length > 0;
  });

  async function submit(): Promise<void> {
    if (!isValid.value) {
      return;
    }

    isSubmitting.value = true;
    formError.value = null;

    try {
      const payload = {
        name: name.value.trim(),
        students: parsedStudents.value,
      };
      const response = options.saveRoster
        ? await options.saveRoster({
            existingRoster: options.roster ?? null,
            name: payload.name,
            students: payload.students,
          })
        : isEditing.value && options.roster
          ? await apiPut<Roster>(
              `/api/v1/apps/classroom.group-seating-studio/rosters/${options.roster.id}`,
              payload,
            )
          : await apiPost<Roster>("/api/v1/apps/classroom.group-seating-studio/rosters", payload);
      events.saved(response);
    } catch (submitError: unknown) {
      formError.value =
        submitError instanceof Error ? submitError.message : "Kunde inte spara klasslistan.";
    } finally {
      isSubmitting.value = false;
    }
  }

  async function removeRoster(): Promise<void> {
    if (!options.roster) {
      return;
    }

    isDeleting.value = true;
    formError.value = null;

    try {
      if (options.deleteRoster) {
        await options.deleteRoster(options.roster.id);
      } else {
        await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/rosters/${options.roster.id}`);
      }
      events.deleted(options.roster.id);
    } catch {
      formError.value =
        "Det gick inte att ta bort klasslistan. Försök igen eller stäng dialogrutan.";
    } finally {
      isDeleting.value = false;
    }
  }

  return {
    name,
    rawStudents,
    formError,
    isSubmitting,
    isDeleting,
    parsedStudents,
    isValid,
    isEditing,
    submit,
    removeRoster,
  };
}
