/**
 * Authenticated home work-app lane definitions.
 *
 * Domain purpose:
 * - defines the approved primary app lanes for the authenticated home surface
 * - keeps truthful route ownership separate from the rendering components so
 *   `HomeView` and `HomeWorkAppsSection` share one reviewed lane model
 */

export type HomeWorkAppGraphic =
  | "classroom"
  | "exam"
  | "audio"
  | "document"
  | "code";

export type HomeWorkApp = {
  id: string;
  title: string;
  description: string;
  graphic: HomeWorkAppGraphic;
  to?: string;
  availabilityLabel: string;
};

export const HOME_PRIMARY_WORK_APPS: readonly HomeWorkApp[] = [
  {
    id: "classroom",
    title: "Klassrumskartan",
    description: "Planera salar, grupper och placeringar i den egna arbetsytan.",
    graphic: "classroom",
    to: "/apps/classroom.group-seating-studio",
    availabilityLabel: "Direkt i appen",
  },
  {
    id: "exam-converter",
    title: "Exam Converter",
    description: "Importera prov, arbeta vidare med facit och spara filspår.",
    graphic: "exam",
    to: "/apps/documents.conversion_hub?mode=exam",
    availabilityLabel: "Direkt i appen",
  },
  {
    id: "audio-transcription",
    title: "Audio Transcription",
    description: "Konvertera ljud till sparad transkriptarbetsyta och exportera vidare.",
    graphic: "audio",
    to: "/apps/documents.conversion_hub?mode=transcript",
    availabilityLabel: "Direkt i appen",
  },
  {
    id: "document-converter",
    title: "Document Converter",
    description: "PDF, DOCX, HTML och mallformat i en egen dokumentyta när den är redo.",
    graphic: "document",
    availabilityLabel: "Visas här när arbetsytan är redo",
  },
  {
    id: "editor",
    title: "Kodredigerare",
    description: "Skriv, underhåll och vidareutveckla verktyg utan att lämna startsidan först.",
    graphic: "code",
    to: "/editor",
    availabilityLabel: "Direkt i appen",
  },
] as const;
