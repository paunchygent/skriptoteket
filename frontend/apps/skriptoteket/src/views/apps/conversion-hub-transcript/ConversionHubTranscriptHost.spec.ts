/**
 * Transcript host race and replay-state specs.
 *
 * Domain purpose:
 *   Prove the authenticated transcript host keeps speaker-overlay loading,
 *   saving, and replay affordances truthful across the saved-transcript flow.
 *
 * Relationships:
 *   - Exercises `ConversionHubTranscriptHost.vue` as the stateful DOM boundary.
 *   - Mocks only product-edge API/composable seams.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { computed, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ConversionHubSavedTranscriptResponse,
  ConversionHubTranscriptSpeakerOverlaysResponse,
} from "../../../api/conversionHubTranscriptSaves";
import ConversionHubTranscriptHost from "./ConversionHubTranscriptHost.vue";
import type { TranscriptJson, TranscriptSpeakerControl } from "../../../api/sirConvertGateway";

const transcriptSaveMocks = vi.hoisted(() => ({
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

const replayMocks = vi.hoisted(() => ({
  requestConversionHubTranscriptFormatterReplay: vi.fn(),
}));

const artifactActionMocks = vi.hoisted(() => ({
  downloadConversionHubTranscriptFormatterArtifact: vi.fn(),
  saveConversionHubTranscriptFormatterArtifact: vi.fn(),
}));

const browserDownloadMocks = vi.hoisted(() => ({
  triggerBrowserDownload: vi.fn(),
}));

type MockSourceState = ReturnType<typeof createSourceState>;
type MockRuntimeState = ReturnType<typeof createRuntimeState>;

let sourceState: MockSourceState;
let runtimeState: MockRuntimeState;

vi.mock("../../../api/conversionHubTranscriptSaves", () => ({
  buildSaveTranscriptRequest: transcriptSaveMocks.buildSaveTranscriptRequest,
  getConversionHubTranscriptSpeakerOverlays:
    transcriptSaveMocks.getConversionHubTranscriptSpeakerOverlays,
  registerTranscriptConversionHubJob: transcriptSaveMocks.registerTranscriptConversionHubJob,
  saveConversionHubTranscript: transcriptSaveMocks.saveConversionHubTranscript,
  updateConversionHubTranscriptSpeakerOverlays:
    transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays,
}));

vi.mock("../../../api/conversionHubTranscriptFormatterReplay", () => ({
  requestConversionHubTranscriptFormatterReplay:
    replayMocks.requestConversionHubTranscriptFormatterReplay,
}));

vi.mock("../../../api/conversionHubTranscriptFormatterArtifactActions", () => ({
  downloadConversionHubTranscriptFormatterArtifact:
    artifactActionMocks.downloadConversionHubTranscriptFormatterArtifact,
  saveConversionHubTranscriptFormatterArtifact:
    artifactActionMocks.saveConversionHubTranscriptFormatterArtifact,
}));

vi.mock("../exam-converter/browserDownload", () => ({
  triggerBrowserDownload: browserDownloadMocks.triggerBrowserDownload,
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
      {
        endSeconds: 1,
        id: "seg_1",
        speakerLabel: "SPEAKER_00",
        startSeconds: 0,
        text: "Hej.",
      },
      {
        endSeconds: 2,
        id: "seg_2",
        speakerLabel: "SPEAKER_01",
        startSeconds: 1,
        text: "Välkomna.",
      },
    ],
    transcriptText: "Hej. Välkomna.",
  };
}

function selectedTranscriptFile(): File {
  return new File(["audio"], "lektion.mp3", { type: "audio/mpeg" });
}

function createSourceState() {
  const file = selectedTranscriptFile();
  const selectedTranscriptFileRef = ref({
    file,
    name: file.name,
    sizeLabel: "1,0 kB",
  });
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

function savedTranscriptResponse(): ConversionHubSavedTranscriptResponse {
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

function overlaysResponse(
  overlays: ConversionHubTranscriptSpeakerOverlaysResponse["overlays"],
): ConversionHubTranscriptSpeakerOverlaysResponse {
  return {
    overlays,
    transcript_id: "saved_transcript_1",
    updated_at: overlays.length > 0 ? "2026-06-13T18:18:48Z" : null,
  };
}

type Deferred<T> = {
  promise: Promise<T>;
  reject: (reason?: unknown) => void;
  resolve: (value: T) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, reject, resolve };
}

function mountHost() {
  return mount(ConversionHubTranscriptHost);
}

async function startSuccessfulTranscript(wrapper: ReturnType<typeof mountHost>): Promise<void> {
  await wrapper.get("[data-test='transcript-start']").trigger("click");
  await flushPromises();
}

async function saveTranscript(wrapper: ReturnType<typeof mountHost>): Promise<void> {
  await wrapper.get("[data-test='transcript-save-button']").trigger("click");
  await flushPromises();
}

describe("ConversionHubTranscriptHost", () => {
  beforeEach(() => {
    sourceState = createSourceState();
    runtimeState = createRuntimeState();
    transcriptSaveMocks.registerTranscriptConversionHubJob.mockReset();
    transcriptSaveMocks.saveConversionHubTranscript.mockReset();
    transcriptSaveMocks.getConversionHubTranscriptSpeakerOverlays.mockReset();
    transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays.mockReset();
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
      ]),
    );
  });

  it("waits for overlay readback before rendering editable speaker inputs", async () => {
    const pendingOverlays = deferred<ConversionHubTranscriptSpeakerOverlaysResponse>();
    transcriptSaveMocks.getConversionHubTranscriptSpeakerOverlays.mockReturnValueOnce(
      pendingOverlays.promise,
    );

    const wrapper = mountHost();

    await startSuccessfulTranscript(wrapper);
    await saveTranscript(wrapper);

    expect(wrapper.html()).not.toContain('data-test="transcript-speaker-overlays"');
    expect(wrapper.get("[data-test='transcript-save-state']").text()).toContain("Sparar");

    pendingOverlays.resolve(overlaysResponse([]));
    await flushPromises();

    expect(wrapper.html()).toContain('data-test="transcript-speaker-overlays"');
    expect(wrapper.get("[data-test='transcript-save-state']").text()).toContain("Sparat");
  });

  it("keeps replay disabled and truthful when overlay save returns an empty persisted list", async () => {
    transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays.mockResolvedValueOnce(
      overlaysResponse([]),
    );

    const wrapper = mountHost();

    await startSuccessfulTranscript(wrapper);
    await saveTranscript(wrapper);

    await wrapper
      .get<HTMLInputElement>("[data-test='transcript-speaker-name-SPEAKER_00']")
      .setValue("Anna Andersson");
    await wrapper.get("[data-test='transcript-speaker-overlays-save']").trigger("click");
    await flushPromises();

    expect(wrapper.get("[data-test='transcript-speaker-overlay-state']").text()).toContain(
      "Talarnamn kan sparas.",
    );
    expect(wrapper.get("[data-test='transcript-formatter-replay-state']").text()).toContain(
      "Spara talarnamnen innan exportfiler skapas.",
    );
    expect(wrapper.get("[data-test='transcript-formatter-replay-button']").attributes("disabled"))
      .toBe("");
    expect(wrapper.text()).toContain("SPEAKER_00");
  });

  it("enables replay only after non-empty overlays are persisted", async () => {
    transcriptSaveMocks.updateConversionHubTranscriptSpeakerOverlays.mockResolvedValueOnce(
      overlaysResponse([
        { canonical_speaker_label: "SPEAKER_00", display_name: "Anna Andersson" },
        { canonical_speaker_label: "SPEAKER_01", display_name: "Bo Berg" },
      ]),
    );

    const wrapper = mountHost();

    await startSuccessfulTranscript(wrapper);
    await saveTranscript(wrapper);

    expect(wrapper.get("[data-test='transcript-formatter-replay-button']").attributes("disabled"))
      .toBe("");

    await wrapper
      .get<HTMLInputElement>("[data-test='transcript-speaker-name-SPEAKER_00']")
      .setValue("Anna Andersson");
    await wrapper
      .get<HTMLInputElement>("[data-test='transcript-speaker-name-SPEAKER_01']")
      .setValue("Bo Berg");
    await wrapper.get("[data-test='transcript-speaker-overlays-save']").trigger("click");
    await flushPromises();

    expect(wrapper.get("[data-test='transcript-speaker-overlay-state']").text()).toContain(
      "Talarnamn sparade.",
    );
    expect(wrapper.get("[data-test='transcript-formatter-replay-state']").text()).toContain(
      "Exportfiler kan skapas.",
    );
    expect(
      wrapper.get("[data-test='transcript-formatter-replay-button']").attributes("disabled"),
    ).toBeUndefined();
    expect(wrapper.text()).toContain("Anna Andersson");
    expect(wrapper.text()).toContain("Bo Berg");
  });
});
