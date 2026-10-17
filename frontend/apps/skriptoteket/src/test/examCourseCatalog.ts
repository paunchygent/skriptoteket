import type { ExamCourseCatalogResponse } from "../api/examWorkspace";

/** Three entries copied from the committed Skolverket snapshot (GY11, GY25 and GR). */
export async function getExamCourseCatalog(): Promise<ExamCourseCatalogResponse> {
  return {
    generated_at: "2026-10-16T17:48:27.460179+00:00",
    registered_course_keys: [],
    courses: [
      {
        code: "ADMADM01",
        key: "ADMADM01",
        name: "Administration 1",
        points: 100,
        reform: "GY11",
        school_form: "gymnasiet",
        subject_code: "ADM",
        subject_name: "Administration",
        year_band: null,
        year_band_label: null,
      },
      {
        code: "ADMI1000X",
        key: "ADMI1000X",
        name: "Administration nivå 1",
        points: 100,
        reform: "GY25",
        school_form: "gymnasiet",
        subject_code: "ADMI",
        subject_name: "Administration",
        year_band: null,
        year_band_label: null,
      },
      {
        code: "GRGRBIL01",
        key: "GRGRBIL01/7-9",
        name: "Bild, åk 7–9",
        points: null,
        reform: null,
        school_form: "grundskolan",
        subject_code: "GRGRBIL01",
        subject_name: "Bild",
        year_band: "7-9",
        year_band_label: "åk 7–9",
      },
    ],
  };
}
