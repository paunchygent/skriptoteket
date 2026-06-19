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

export type HomeWorkApp = {
  id: string;
  title: string;
  description: string;
  imageSrc: string;
  to?: string;
  availabilityLabel: string;
};

export const HOME_PRIMARY_WORK_APPS: readonly HomeWorkApp[] = [
  {
    id: "classroom",
    title: "Klassrumskartan",
    description: "Skapa salen, placera eleverna, spara som PDF eller för Excel.",
    imageSrc: classroomMapSymbolUrl,
    to: "/apps/classroom.group-seating-studio",
    availabilityLabel: "Direkt i appen",
  },
  {
    id: "exam-converter",
    title: "Provkonverteraren",
    description: "Importera prov, kontrollera frågor och facit, exportera vidare.",
    imageSrc: examConverterSymbolUrl,
    to: "/apps/documents.conversion_hub?mode=exam",
    availabilityLabel: "Direkt i appen",
  },
  {
    id: "audio-transcription",
    title: "Ljudtranskribering",
    description: "Transkribera ljudfiler och spara texten bland dina filer.",
    imageSrc: audioTranscriptionSymbolUrl,
    to: "/apps/documents.conversion_hub?mode=transcript",
    availabilityLabel: "Direkt i appen",
  },
  {
    id: "document-converter",
    title: "Dokumentkonverteraren",
    description: "PDF, DOCX, HTML och andra dokumentformat.",
    imageSrc: documentConverterSymbolUrl,
    availabilityLabel: "Kommer senare",
  },
  {
    id: "editor",
    title: "Kodredigerare",
    description: "Fortsätt där du slutade eller välj ett verktyg att redigera.",
    imageSrc: codeEditorSymbolUrl,
    to: "/editor",
    availabilityLabel: "Direkt i appen",
  },
] as const;
