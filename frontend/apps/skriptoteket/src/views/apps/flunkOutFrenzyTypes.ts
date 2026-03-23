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
