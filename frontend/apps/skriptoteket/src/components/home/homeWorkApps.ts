/**
 * Authenticated home work-app lane definitions.
 *
 * Domain purpose:
 * - defines the approved primary app lanes for the authenticated home surface
 * - keeps truthful route ownership separate from the rendering components so
 *   `HomeView` and `HomeWorkAppsSection` share one reviewed lane model
 */

import classroomMapSymbolUrl from "../../assets/home/klassrumskartan/catalog/classroom-map-symbol.png";
import documentConverterSymbolUrl from "../../assets/home/work-apps/dokumentkonverteraren.png";
import codeEditorSymbolUrl from "../../assets/home/work-apps/kodredigerare.png";
import audioTranscriptionSymbolUrl from "../../assets/home/work-apps/ljudtranskribering.png";
import examConverterSymbolUrl from "../../assets/home/work-apps/provkonverteraren.png";

export type HomeWorkAppMinRole = "user" | "contributor" | "admin" | "superuser";

export type HomeWorkApp = {
  id: string;
  title: string;
  description: string;
  imageSrc: string;
  to?: string;
  availabilityLabel?: string;
  minRole?: HomeWorkAppMinRole;
};

export const HOME_PRIMARY_WORK_APPS: readonly HomeWorkApp[] = [
  {
    id: "classroom",
    title: "Klassrumskartan",
    description: "Skapa klassrum, placera elever och exportera till PDF eller Excel.",
    imageSrc: classroomMapSymbolUrl,
    to: "/apps/classroom.group-seating-studio",
  },
  {
    id: "exam-converter",
    title: "Provhantering",
    description: "Skapa, redigera och konvertera prov.",
    imageSrc: examConverterSymbolUrl,
    to: "/apps/exam-converter",
  },
  {
    id: "audio-transcription",
    title: "Ljudtranskribering",
    description: "Transkribera tal till text och spara resultatet bland dina filer.",
    imageSrc: audioTranscriptionSymbolUrl,
    to: "/apps/audio-transcription",
  },
  {
    id: "document-converter",
    title: "Dokumentkonvertering",
    description: "Skapa PDF:er med hjälp av HTML och CSS.",
    imageSrc: documentConverterSymbolUrl,
    availabilityLabel: "Kommer senare",
  },
  {
    id: "editor",
    title: "Kodredigerare",
    description: "Fortsätt där du slutade.",
    imageSrc: codeEditorSymbolUrl,
    to: "/editor",
    minRole: "contributor",
  },
] as const;
