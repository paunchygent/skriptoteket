/**
 * Launcher-telemetry proof regressions for Flunk-Out Frenzy runtime.
 *
 * These checks protect the exported debug schema and frozen proof-matrix
 * contract independently from the broader runtime lifecycle tests.
 */

import { describe, expect, it } from "vitest";

import { GameRuntime } from "./GameRuntime";
import { ManualAnimationScheduler } from "./manualAnimationScheduler.spec-support";
import type { GameEffectEvent } from "../presentation/gameEffectTypes";
import {
  createLaunchProofCaseRecord,
  FakeAudioDirector,
  FakeRenderer,
  FakeRuntimeEngine,
  PR_0206_ALLOWED_ROUTE_REJECT_REASONS,
  PR_0206_PROOF_MATRIX_CONTRACT,
} from "./GameRuntime.spec-support";

describe("GameRuntime telemetry", () => {
  it("does not synthesize a launch-release effect from raw input alone", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const renderer = new FakeRenderer();
    const audio = new FakeAudioDirector();
    const runtime = new GameRuntime({ scheduler, engine, renderer, audio });

    runtime.start();
    runtime.enqueueCommand({ type: "launch", pressed: true });
    runtime.enqueueCommand({ type: "launch", pressed: false });

    scheduler.runFrame(0);

    const consumedEffects = audio.consumeEffects.mock.calls.flatMap(
      ([effects]) => effects as GameEffectEvent[],
    );

    expect(consumedEffects).not.toContainEqual({
      type: "launch-released",
      chargeActive: true,
    });
  });

  it("exposes launcher telemetry and proof-record schema without gate-passed alias", () => {
    const scheduler = new ManualAnimationScheduler();
    const engine = new FakeRuntimeEngine();
    const runtime = new GameRuntime({
      scheduler,
      engine,
      renderer: new FakeRenderer(),
      audio: new FakeAudioDirector(),
    });

    runtime.start();
    runtime.enqueueCommand({ type: "launch", pressed: true });
    scheduler.runFrame(0);
    runtime.enqueueCommand({ type: "launch", pressed: false });
    scheduler.runFrame(16);

    const telemetry = runtime.debugLauncherTelemetry();
    expect(telemetry.input.launchPressed).toBe(false);
    expect(telemetry.input.lastTransitionMs).not.toBeNull();
    expect(telemetry.launcher).not.toBeNull();
    expect(telemetry.launchToDropTraceStep).not.toBeNull();

    const proofCase = createLaunchProofCaseRecord({
      caseId: "K-FULL-STEADY",
      inputMode: "keyboard",
      holdProfile: "full",
      dtMs: 16,
      holdMs: 896,
      holdSteps: 56,
      relaunchGapMs: 256,
      relaunchGapSteps: 16,
      observationSteps: 60,
      plungerDelta: 0,
      ballDisplacementMagnitude: 0,
      maxVy: 0,
      minVy: 0,
      sw16ExitObserved: false,
      telemetry,
    });

    expect(proofCase).toEqual(expect.objectContaining({
      case_id: "K-FULL-STEADY",
      input_mode: "keyboard",
      hold_profile: "full",
      route_capture_decision: "none",
      route_capture_reason: null,
      sw16_exit_observed: false,
      strike_classification: expect.any(String),
    }));
    expect(["none", "accepted", "rejected"]).toContain(proofCase.route_capture_decision);
    if (proofCase.route_capture_reason !== null) {
      expect(PR_0206_ALLOWED_ROUTE_REJECT_REASONS).toContain(proofCase.route_capture_reason);
    }
    expect("gate-passed" in proofCase).toBe(false);
  });

  it("locks the unchanged PR-0206 launch matrix contract used by proof telemetry", () => {
    expect(PR_0206_PROOF_MATRIX_CONTRACT).toEqual([
      { caseId: "K-REST-STEADY", holdProfile: "rest", holdSteps: 0, thresholdPx: 0, thresholdVy: 0 },
      { caseId: "K-SHORT-STEADY", holdProfile: "short", holdSteps: 8, thresholdPx: 2, thresholdVy: -8 },
      { caseId: "K-MEDIUM-STEADY", holdProfile: "medium", holdSteps: 26, thresholdPx: 4, thresholdVy: -20 },
      { caseId: "K-FULL-STEADY", holdProfile: "full", holdSteps: 56, thresholdPx: 8, thresholdVy: -40 },
      { caseId: "K-RELAUNCH-MEDIUM", holdProfile: "relaunch", holdSteps: 26, thresholdPx: 4, thresholdVy: -20 },
    ]);
    expect(PR_0206_ALLOWED_ROUTE_REJECT_REASONS).toEqual([
      "distance_xy",
      "distance_z",
      "vy_gate",
      "window_expired",
      "no_route",
    ]);
  });
});
