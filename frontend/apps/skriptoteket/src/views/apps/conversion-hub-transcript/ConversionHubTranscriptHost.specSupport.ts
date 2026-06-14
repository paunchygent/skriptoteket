/**
 * Conversion Hub transcript host test harness.
 *
 * Domain purpose:
 *   Provides the mocked product-edge runtime used by transcript host specs so
 *   autosave, speaker-overlay, and selected-format export behavior can be
 *   exercised as one authenticated workspace flow.
 *
 * Relationships:
 *   - Owns mocks for transcript persistence, formatter export, artifact actions,
 *     browser downloads, source-file state, and gateway runtime state.
 *   - Mounts `ConversionHubTranscriptHost.vue` for focused host-level specs.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { computed, ref } from "vue";
import { vi } from "vitest";

import type {
  ConversionHubTranscriptFormatterExportResponse,
} from "../../../api/conversionHubTranscriptFormatterExports";
import type {
  ConversionHubSavedTranscriptResponse,
  ConversionHubTranscriptSpeakerOverlaysResponse,
} from "../../../api/conversionHubTranscriptSaves";
import type { TranscriptJson, TranscriptSpeakerControl } from "../../../api/sirConvertGateway";
import ConversionHubTranscriptHost from "./ConversionHubTranscriptHost.vue";

const hoistedTranscriptSaveMocks = vi.hoisted(() => ({
  buildSaveTranscriptRequest: vi.fn(() => ({
    artifact_key: "transcript_json" as const,
    correlation_id: "corr_transcript_1",
    diarization_mode: "known_speaker_count" as const,
    generated_at: null,
    language_code: "sv",
    sir_convert_job_id: "sir_job_1",
    source_filename: "lektion.mp3",
    speaker_count: 2,
    speaker_max: null,
    speaker_min: null,
    transcript_json: {},
    transcript_schema_version: "transcript_json_v1",
  })),
  getConversionHubTranscriptSpeakerOverlays: vi.fn(),
  registerTranscriptConversionHubJob: vi.fn(),
  saveConversionHubTranscript: vi.fn(),
  updateConversionHubTranscriptSpeakerOverlays: vi.fn(),
}));
const hoistedFormatterExportMocks = vi.hoisted(() => ({
  getConversionHubTranscriptFormatterExport: vi.fn(),
  requestConversionHubTranscriptFormatterExport: vi.fn(),
}));
const hoistedArtifactActionMocks = vi.hoisted(() => ({
  downloadConversionHubTranscriptFormatterArtifact: vi.fn(),
  saveConversionHubTranscriptFormatterArtifact: vi.fn(),
}));
const hoistedBrowserDownloadMocks = vi.hoisted(() => ({
  triggerBrowserDownload: vi.fn(),
}));
export const transcriptSaveMocks = hoistedTranscriptSaveMocks;
export const formatterExportMocks = hoistedFormatterExportMocks;
export const artifactActionMocks = hoistedArtifactActionMocks;
export const browserDownloadMocks = hoistedBrowserDownloadMocks;

type MockSourceState = ReturnType<typeof createSourceState>;
type MockRuntimeState = ReturnType<typeof createRuntimeState>;
let sourceState: MockSourceState;
let runtimeState: MockRuntimeState;

vi.mock("../../../api/conversionHubTranscriptSaves", () => ({
  buildSaveTranscriptRequest: hoistedTranscriptSaveMocks.buildSaveTranscriptRequest,
  getConversionHubTranscriptSpeakerOverlays:
    hoistedTranscriptSaveMocks.getConversionHubTranscriptSpeakerOverlays,
  registerTranscriptConversionHubJob: hoistedTranscriptSaveMocks.registerTranscriptConversionHubJob,
  saveConversionHubTranscript: hoistedTranscriptSaveMocks.saveConversionHubTranscript,
  updateConversionHubTranscriptSpeakerOverlays:
    hoistedTranscriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays,
}));
vi.mock("../../../api/conversionHubTranscriptFormatterExports", () => ({
  getConversionHubTranscriptFormatterExport:
    hoistedFormatterExportMocks.getConversionHubTranscriptFormatterExport,
  requestConversionHubTranscriptFormatterExport:
    hoistedFormatterExportMocks.requestConversionHubTranscriptFormatterExport,
}));
vi.mock("../../../api/conversionHubTranscriptFormatterArtifactActions", () => ({
  downloadConversionHubTranscriptFormatterArtifact:
    hoistedArtifactActionMocks.downloadConversionHubTranscriptFormatterArtifact,
  saveConversionHubTranscriptFormatterArtifact:
    hoistedArtifactActionMocks.saveConversionHubTranscriptFormatterArtifact,
}));
vi.mock("../exam-converter/browserDownload", () => ({
  triggerBrowserDownload: hoistedBrowserDownloadMocks.triggerBrowserDownload,
}));
vi.mock("./useTranscriptSourceFile", () => ({
  useTranscriptSourceFile: () => sourceState,
}));
vi.mock("./useTranscriptGatewayRuntime", () => ({
  useTranscriptGatewayRuntime: () => runtimeState,
}));

function transcriptFixture(): TranscriptJson {
  return {
    schemaVersion: "transcript_json_v1",
    segments: [
      { endSeconds: 1, id: "seg_1", speakerLabel: "SPEAKER_00", startSeconds: 0, text: "Hej." },
      { endSeconds: 2, id: "seg_2", speakerLabel: "SPEAKER_01", startSeconds: 1, text: "Välkomna." },
    ],
    transcriptText: "Hej. Välkomna.",
  };
}

function selectedTranscriptFile(): File {
  return new File(["audio"], "lektion.mp3", { type: "audio/mpeg" });
}

function createSourceState() {
  const file = selectedTranscriptFile();
  const selectedTranscriptFileRef = ref({ file, name: file.name, sizeLabel: "1,0 kB" });
  const speakerMode = ref<TranscriptSpeakerControl["mode"]>("known_speaker_count");
  const speakerCount = ref(2);
  const minSpeakers = ref(2);
  const maxSpeakers = ref(4);

  return {
    clearTranscriptFile: vi.fn(),
    maxSpeakers,
    minSpeakers,
    resetTranscriptChoices: vi.fn(),
    selectDroppedTranscriptFiles: vi.fn(),
    selectTranscriptFile: vi.fn(),
    selectedTranscriptFile: selectedTranscriptFileRef,
    speakerControl: computed<TranscriptSpeakerControl>(() => ({
      mode: "known_speaker_count",
      speakerCount: speakerCount.value,
    })),
    speakerCount,
    speakerError: computed(() => null),
    speakerMode,
    transcriptFileError: ref<string | null>(null),
  };
}

function createRuntimeState() {
  return {
    abortState: ref({ message: null, status: "idle" as const }),
    cancelTranscript: vi.fn(),
    currentJob: ref(null),
    errorMessage: ref<string | null>(null),
    lastCorrelationId: ref("corr_transcript_1"),
    lastJobId: ref("sir_job_1"),
    resetRuntime: vi.fn(),
    status: ref<"idle" | "running" | "succeeded" | "failed" | "canceled">("idle"),
    submitAndPoll: vi.fn().mockImplementation(async () => {
      runtimeState.status.value = "succeeded";
      runtimeState.transcript.value = transcriptFixture();
      return runtimeState.transcript.value;
    }),
    transcript: ref<TranscriptJson | null>(null),
    uploadState: ref({
      loadedBytes: 0,
      percentComplete: null,
      status: "idle" as const,
      totalBytes: null,
    }),
  };
}

export function savedTranscriptResponse(): ConversionHubSavedTranscriptResponse {
  return {
    artifact_key: "transcript_json",
    conversion_hub_job_id: "local_job_1",
    correlation_id: "corr_transcript_1",
    created_at: "2026-06-13T18:18:47Z",
    diarization_mode: "known_speaker_count",
    generated_at: null,
    language_code: "sv",
    owner_user_id: "user_1",
    sir_convert_job_id: "sir_job_1",
    source_filename: "lektion.mp3",
    speaker_count: 2,
    speaker_max: null,
    speaker_min: null,
    transcript_id: "saved_transcript_1",
    transcript_json: {},
    transcript_schema_version: "transcript_json_v1",
    updated_at: "2026-06-13T18:18:47Z",
  };
}

export function overlaysResponse(
  overlays: ConversionHubTranscriptSpeakerOverlaysResponse["overlays"],
): ConversionHubTranscriptSpeakerOverlaysResponse {
  return {
    overlays,
    transcript_id: "saved_transcript_1",
    updated_at: overlays.length > 0 ? "2026-06-13T18:18:48Z" : null,
  };
}

export function formatterExportResponse(
  patch: Partial<ConversionHubTranscriptFormatterExportResponse> = {},
): ConversionHubTranscriptFormatterExportResponse {
  return {
    artifacts: [
      {
        artifact_key: "transcript_txt",
        content_type: "text/plain",
        filename: "transcript_txt.txt",
        requested_artifact: "txt",
        size_bytes: 12,
      },
    ],
    conversion_hub_job_id: "local_export_job_1",
    created_at: "2026-06-14T08:00:00Z",
    error_message: null,
    requested_artifacts: ["txt", "md", "vtt", "srt"],
    status: "succeeded",
    transcript_id: "saved_transcript_1",
    updated_at: "2026-06-14T08:00:01Z",
    ...patch,
  };
}

export type Deferred<T> = {
  promise: Promise<T>;
  reject: (reason?: unknown) => void;
  resolve: (value: T) => void;
};

export function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, reject, resolve };
}

export function resetTranscriptHostHarness(): void {
  sourceState = createSourceState();
  runtimeState = createRuntimeState();
  [
    transcriptSaveMocks.registerTranscriptConversionHubJob,
    transcriptSaveMocks.saveConversionHubTranscript,
    transcriptSaveMocks.getConversionHubTranscriptSpeakerOverlays,
    transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays,
    formatterExportMocks.requestConversionHubTranscriptFormatterExport,
    formatterExportMocks.getConversionHubTranscriptFormatterExport,
    artifactActionMocks.downloadConversionHubTranscriptFormatterArtifact,
    artifactActionMocks.saveConversionHubTranscriptFormatterArtifact,
    browserDownloadMocks.triggerBrowserDownload,
  ].forEach((mock) => mock.mockReset());
  transcriptSaveMocks.registerTranscriptConversionHubJob.mockResolvedValue({
    job_id: "local_job_1",
    status: "succeeded",
    upstream_job_id: "sir_job_1",
  });
  transcriptSaveMocks.saveConversionHubTranscript.mockResolvedValue(savedTranscriptResponse());
  transcriptSaveMocks.getConversionHubTranscriptSpeakerOverlays.mockResolvedValue(
    overlaysResponse([]),
  );
  transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays.mockResolvedValue(
    overlaysResponse([
      { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
      { canonical_speaker_label: "SPEAKER_01", display_name: "Bo Berg" },
    ]),
  );
  formatterExportMocks.requestConversionHubTranscriptFormatterExport.mockResolvedValue(
    formatterExportResponse(),
  );
  formatterExportMocks.getConversionHubTranscriptFormatterExport.mockResolvedValue(
    formatterExportResponse(),
  );
  artifactActionMocks.downloadConversionHubTranscriptFormatterArtifact.mockResolvedValue({
    blob: new Blob(["Hej"], { type: "text/plain" }),
    filename: "transcript_txt.txt",
  });
  artifactActionMocks.saveConversionHubTranscriptFormatterArtifact.mockResolvedValue({
    source_artifact_id: "artifact_1",
    vault_artifact: {
      bytes: 12,
      created_at: "2026-06-14T08:00:02Z",
      file_id: "vault_file_1",
      name: "transcript_txt.txt",
    },
  });
}

export function mountHost() {
  return mount(ConversionHubTranscriptHost);
}

export async function startSuccessfulTranscript(
  wrapper: ReturnType<typeof mountHost>,
): Promise<void> {
  await wrapper.get("[data-test='transcript-start']").trigger("click");
  await flushPromises();
}

export async function saveTranscript(_wrapper: ReturnType<typeof mountHost>): Promise<void> {
  await flushPromises();
}

export async function saveSpeakerNames(wrapper: ReturnType<typeof mountHost>): Promise<void> {
  await wrapper
    .get<HTMLInputElement>("[data-test='transcript-speaker-name-SPEAKER_00']")
    .setValue("Anna Andersson");
  await wrapper
    .get<HTMLInputElement>("[data-test='transcript-speaker-name-SPEAKER_01']")
    .setValue("Bo Berg");
  await wrapper.get("[data-test='transcript-speaker-overlays-save']").trigger("click");
  await flushPromises();
}

export async function startExportReadyTranscript(
  wrapper: ReturnType<typeof mountHost>,
): Promise<void> {
  await startSuccessfulTranscript(wrapper);
  await saveTranscript(wrapper);
  await saveSpeakerNames(wrapper);
}
