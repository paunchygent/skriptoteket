/**
 * Shared launch-proof helpers for the Flunk-Out Frenzy physics-world launcher suite.
 *
 * The launcher behavior and proof cases import these utilities so the targeted
 * test entrypoint can stay small while preserving the original coverage.
 */

import type { PrototypeAlphaTable } from "../../table/prototypeAlphaTable";
import type { PhysicsWorld as PhysicsWorldType } from "../PhysicsWorld";
import {
  collectEventsUntil,
  executeRelease,
  runLaunchToDropTraceCase as runSharedLaunchToDropTraceCase,
} from "../launchTraceMatrix";
import {
  PR0206_DT_MS,
  PR0206_OBSERVATION_STEPS,
  PR0206_RELAUNCH_GAP_STEPS,
  classifyStrikeFromContact,
  normalizeRouteCaptureDecision,
  normalizeRouteCaptureReason,
  type LaunchProofCaseContract,
  type LaunchProofCaseRecord,
  type LaunchProofRouteCaptureDecision,
  type LaunchProofRouteRejectReason,
} from "../launchTraceContract";

export type LauncherHarness = {
  PhysicsWorld: typeof PhysicsWorldType;
  PROTOTYPE_ALPHA_TABLE: PrototypeAlphaTable;
};

export async function runLaunchProofCase(
  harness: LauncherHarness,
  proofCase: LaunchProofCaseContract,
  gateTag: string,
): Promise<LaunchProofCaseRecord> {
  const world = await harness.PhysicsWorld.create();

  try {
    world.spawnBall();
    const feedEvents = collectEventsUntil(world, 40, (events) => {
      return events.some((event) => event.type === "launcher-fed");
    });
    const allEvents = [...feedEvents];
    const restSnapshot = world.currentSnapshot();
    const restBall = restSnapshot.ball;
    const restTelemetry = restSnapshot.launcherTelemetry;

    if (!restBall || !restTelemetry) {
      throw new Error(`Missing rest telemetry for launch proof case "${proofCase.caseId}".`);
    }
    const restSeparation = restTelemetry.contact.separationPx;
    if (restSeparation === null) {
      throw new Error(`Missing rest-separation telemetry for launch proof case "${proofCase.caseId}".`);
    }

    const restPlungerY = restSnapshot.plunger?.y ?? 0;
    let maxPlungerY = restPlungerY;
    let maxDisplacement = 0;
    let maxVy = Number.NEGATIVE_INFINITY;
    let minVy = Number.POSITIVE_INFINITY;
    let routeCaptureDecision: LaunchProofRouteCaptureDecision = "none";
    let routeCaptureReason: LaunchProofRouteRejectReason | null = null;
    let sw16ExitObserved = allEvents.some((event) => {
      return event.type === "gate-passed" && event.tag === gateTag;
    });
    let maxOverlapPx = 0;
    let minRelativeVyAtContact = Number.POSITIVE_INFINITY;
    let impulseTransferMarker = 0;
    let lastContactAtStep: number | null = null;

    if (proofCase.holdProfile === "rest") {
      for (let index = 0; index < 10; index += 1) {
        allEvents.push(...world.step(PR0206_DT_MS));
      }
    } else {
      executeRelease(world, proofCase.holdSteps, allEvents);
      if (proofCase.holdProfile === "relaunch") {
        for (let index = 0; index < PR0206_RELAUNCH_GAP_STEPS; index += 1) {
          allEvents.push(...world.step(PR0206_DT_MS));
        }
        executeRelease(
          world,
          proofCase.relaunchSecondHoldSteps ?? proofCase.holdSteps,
          allEvents,
        );
      }
    }

    for (let index = 0; index < PR0206_OBSERVATION_STEPS; index += 1) {
      const stepEvents = world.step(PR0206_DT_MS);
      allEvents.push(...stepEvents);
      sw16ExitObserved = sw16ExitObserved || stepEvents.some((event) => {
        return event.type === "gate-passed" && event.tag === gateTag;
      });

      const snapshot = world.currentSnapshot();
      const ball = snapshot.ball;
      if (ball) {
        maxDisplacement = Math.max(
          maxDisplacement,
          Math.hypot(ball.x - restBall.x, ball.y - restBall.y),
        );
      }
      maxPlungerY = Math.max(maxPlungerY, snapshot.plunger?.y ?? maxPlungerY);

      const telemetry = snapshot.launcherTelemetry;
      if (!telemetry) {
        continue;
      }
      const vy = telemetry.ball.velocity?.y;
      if (Number.isFinite(vy)) {
        maxVy = Math.max(maxVy, vy ?? maxVy);
        minVy = Math.min(minVy, vy ?? minVy);
      }
      routeCaptureDecision = normalizeRouteCaptureDecision(
        telemetry.routeCapture.lastDecision ?? routeCaptureDecision,
      );
      routeCaptureReason = normalizeRouteCaptureReason(
        telemetry.routeCapture.lastRejectReason ?? routeCaptureReason,
      );
      maxOverlapPx = Math.max(maxOverlapPx, telemetry.contact.overlapPx);
      const relativeVyAtContact = telemetry.contact.relativeVyAtContact;
      if (Number.isFinite(relativeVyAtContact)) {
        minRelativeVyAtContact = Math.min(
          minRelativeVyAtContact,
          relativeVyAtContact ?? minRelativeVyAtContact,
        );
      }
      impulseTransferMarker = Math.max(
        impulseTransferMarker,
        telemetry.contact.impulseTransferMarker,
      );
      lastContactAtStep = telemetry.contact.lastContactAtStep ?? lastContactAtStep;
    }

    const normalizedMinRelativeVyAtContact = Number.isFinite(minRelativeVyAtContact)
      ? minRelativeVyAtContact
      : null;
    return {
      case_id: proofCase.caseId,
      hold_profile: proofCase.holdProfile,
      dt_ms: PR0206_DT_MS,
      hold_steps: proofCase.holdSteps,
      relaunch_gap_steps: PR0206_RELAUNCH_GAP_STEPS,
      observation_steps: PR0206_OBSERVATION_STEPS,
      threshold_px: proofCase.thresholdPx,
      threshold_vy: proofCase.thresholdVy,
      plunger_delta: Math.max(0, maxPlungerY - restPlungerY),
      ball_displacement_magnitude: maxDisplacement,
      max_vy: Number.isFinite(maxVy) ? maxVy : 0,
      min_vy: Number.isFinite(minVy) ? minVy : 0,
      feed_inside_at_rest: restTelemetry.sensors.feedInside,
      separation_px_at_rest: restSeparation,
      route_capture_decision: routeCaptureDecision,
      route_capture_reason: routeCaptureReason,
      sw16_exit_observed: sw16ExitObserved,
      contact_diagnostics: {
        maxOverlapPx,
        minRelativeVyAtContact: normalizedMinRelativeVyAtContact,
        impulseTransferMarker,
        lastContactAtStep,
      },
      strike_classification: classifyStrikeFromContact({
        maxOverlapPx,
        minRelativeVyAtContact: normalizedMinRelativeVyAtContact,
        impulseTransferMarker,
        routeCaptureDecision,
      }),
    };
  } finally {
    world.dispose();
  }
}

export async function runLaunchToDropTraceCase(
  harness: LauncherHarness,
  proofCase: LaunchProofCaseContract,
  gateTag: string,
) {
  return runSharedLaunchToDropTraceCase(harness.PhysicsWorld, proofCase, gateTag);
}
