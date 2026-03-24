/**
 * Typed Flunk-Out Frenzy SPA contracts.
 *
 * These interfaces mirror the app-specific bootstrap payload used by the
 * bespoke game shell. They stay deliberately small so later runtime slices can
 * add richer state without rewriting the initial route contract.
 */

export type FlunkOutFrenzyFeatureFlags = {
  audio_enabled: boolean;
  replay_capture_enabled: boolean;
  score_submission_enabled: boolean;
};

export type FlunkOutFrenzyBootstrap = {
  app_id: string;
  title: string;
  summary: string;
  app_version: string;
  ruleset_id: string;
  feature_flags: FlunkOutFrenzyFeatureFlags;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readStringField(source: Record<string, unknown>, field: string): string {
  const value = source[field];
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Ogiltigt bootstrap-svar: saknar strängfältet "${field}".`);
  }
  return value;
}

function readBooleanField(source: Record<string, unknown>, field: string): boolean {
  const value = source[field];
  if (typeof value !== "boolean") {
    throw new Error(`Ogiltigt bootstrap-svar: saknar booleska fältet "${field}".`);
  }
  return value;
}

export function parseFlunkOutFrenzyBootstrap(payload: unknown): FlunkOutFrenzyBootstrap {
  if (!isRecord(payload)) {
    throw new Error("Ogiltigt bootstrap-svar: förväntade ett objekt.");
  }

  const featureFlags = payload.feature_flags;
  if (!isRecord(featureFlags)) {
    throw new Error('Ogiltigt bootstrap-svar: saknar objektet "feature_flags".');
  }

  return {
    app_id: readStringField(payload, "app_id"),
    title: readStringField(payload, "title"),
    summary: readStringField(payload, "summary"),
    app_version: readStringField(payload, "app_version"),
    ruleset_id: readStringField(payload, "ruleset_id"),
    feature_flags: {
      audio_enabled: readBooleanField(featureFlags, "audio_enabled"),
      replay_capture_enabled: readBooleanField(featureFlags, "replay_capture_enabled"),
      score_submission_enabled: readBooleanField(featureFlags, "score_submission_enabled"),
    },
  };
}
