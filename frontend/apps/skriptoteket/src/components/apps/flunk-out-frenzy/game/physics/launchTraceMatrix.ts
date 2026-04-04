/**
 * Deterministic launch-to-drop proof runner for Flunk-Out Frenzy.
 *
 * This module owns the fixed-step matrix execution used by focused proof tests
 * and the browser-side debug seam. Keeping the runner outside `__tests__`
 * prevents live Playwright proof collection from inventing a second shaping
 * path or drifting away from the canonical trace contract.
 */

import type { PhysicsWorld as PhysicsWorldType } from "./PhysicsWorld";
import type { MachineEvent } from "./physicsTypes";
import {
  buildLaunchToDropTraceArtifactPayload,
  classifyStrikeFromContact,
  distinctPhases,
  evaluateTraceCaseInvariants,
  firstDefinedStep,
  normalizeRouteCaptureDecision,
  PR0206_DT_MS,
  PR0206_OBSERVATION_STEPS,
  PR0206_PROOF_MATRIX_CASES,
  PR0206_RELAUNCH_GAP_STEPS,
  PR0209_BOARD_DROP_OBSERVATION_STEPS,
  toLaunchToDropTraceStepRecord,
  type LaunchProofCaseContract,
  type LaunchProofRouteCaptureDecision,
  type LaunchToDropTraceArtifactPayload,
  type LaunchToDropTraceCaseRecord,
  type LaunchToDropTraceStepRecord,
} from "./launchTraceContract";

export function collectEventsUntil(
  world: PhysicsWorldType,
  maxSteps: number,
  predicate: (events: MachineEvent[]) => boolean,
): MachineEvent[] {
  for (let index = 0; index < maxSteps; index += 1) {
    const events = world.step(PR0206_DT_MS);
    if (predicate(events)) {
      return events;
    }
  }

  throw new Error("Expected machine events were not emitted in time.");
}

export function executeRelease(
  world: PhysicsWorldType,
  holdSteps: number,
  events: MachineEvent[],
): void {
  world.applyCommand({ type: "launch", pressed: true });
  for (let index = 0; index < holdSteps; index += 1) {
    events.push(...world.step(PR0206_DT_MS));
  }
  world.applyCommand({ type: "launch", pressed: false });
  events.push(...world.step(PR0206_DT_MS));
}

export async function runLaunchToDropTraceCase(
  PhysicsWorld: typeof PhysicsWorldType,
  proofCase: LaunchProofCaseContract,
  gateTag: string,
): Promise<LaunchToDropTraceCaseRecord> {
  const world = await PhysicsWorld.create();

  try {
    world.spawnBall();
    collectEventsUntil(world, 40, (events) => {
      return events.some((event) => event.type === "launcher-fed");
    });

    const restSnapshot = world.currentSnapshot();
    const restBall = restSnapshot.ball;
    if (!restBall) {
      throw new Error(`Missing rest ball snapshot for trace case "${proofCase.caseId}".`);
    }

    const traceSteps: LaunchToDropTraceStepRecord[] = [];
    let maxDisplacement = 0;
    let minVy = Number.POSITIVE_INFINITY;
    let peakSpeed = 0;
    let routeCaptureDecision: LaunchProofRouteCaptureDecision = "none";
    let maxOverlapPx = 0;
    let minRelativeVyAtContact = Number.POSITIVE_INFINITY;
    let impulseTransferMarker = 0;

    const stepAndCollectTrace = (): void => {
      world.step(PR0206_DT_MS);
      const snapshot = world.currentSnapshot();
      const ball = snapshot.ball;
      if (ball) {
        maxDisplacement = Math.max(
          maxDisplacement,
          Math.hypot(ball.x - restBall.x, ball.y - restBall.y),
        );
      }

      const telemetry = snapshot.launcherTelemetry;
      if (telemetry) {
        routeCaptureDecision = normalizeRouteCaptureDecision(
          telemetry.routeCapture.lastDecision ?? routeCaptureDecision,
        );
        maxOverlapPx = Math.max(maxOverlapPx, telemetry.contact.overlapPx);
        const relativeVy = telemetry.contact.relativeVyAtContact;
        if (Number.isFinite(relativeVy)) {
          minRelativeVyAtContact = Math.min(
            minRelativeVyAtContact,
            relativeVy ?? minRelativeVyAtContact,
          );
        }
        impulseTransferMarker = Math.max(
          impulseTransferMarker,
          telemetry.contact.impulseTransferMarker,
        );
      }

      const traceStep = snapshot.launchTraceStep;
      if (!traceStep) {
        return;
      }
      const vy = traceStep.ballVelocity?.y;
      if (Number.isFinite(vy)) {
        minVy = Math.min(minVy, vy ?? minVy);
      }
      const speed = traceStep.ballVelocity
        ? Math.hypot(traceStep.ballVelocity.x, traceStep.ballVelocity.y, traceStep.ballVelocity.z)
        : 0;
      peakSpeed = Math.max(peakSpeed, speed);
      traceSteps.push(toLaunchToDropTraceStepRecord(traceStep));
    };

    if (proofCase.holdProfile === "rest") {
      for (let index = 0; index < 10; index += 1) {
        stepAndCollectTrace();
      }
    } else {
      world.applyCommand({ type: "launch", pressed: true });
      for (let index = 0; index < proofCase.holdSteps; index += 1) {
        stepAndCollectTrace();
      }
      world.applyCommand({ type: "launch", pressed: false });
      stepAndCollectTrace();

      if (proofCase.holdProfile === "relaunch") {
        for (let index = 0; index < PR0206_RELAUNCH_GAP_STEPS; index += 1) {
          stepAndCollectTrace();
        }
        const secondHoldSteps = proofCase.relaunchSecondHoldSteps ?? proofCase.holdSteps;
        world.applyCommand({ type: "launch", pressed: true });
        for (let index = 0; index < secondHoldSteps; index += 1) {
          stepAndCollectTrace();
        }
        world.applyCommand({ type: "launch", pressed: false });
        stepAndCollectTrace();
      }
    }

    for (
      let index = 0;
      index < PR0206_OBSERVATION_STEPS + PR0209_BOARD_DROP_OBSERVATION_STEPS;
      index += 1
    ) {
      stepAndCollectTrace();
    }

    const normalizedMinRelativeVyAtContact = Number.isFinite(minRelativeVyAtContact)
      ? minRelativeVyAtContact
      : null;
    const phaseOrderObserved = distinctPhases(traceSteps);
    const sw16ExitObserved = traceSteps.some((step) => {
      return step.events.some((event) => event.type === "gate-passed" && event.tag === gateTag);
    });
    const handoffToBoardStep = firstDefinedStep(traceSteps, "handoff_to_board_step");
    const firstBoardCollisionStep = firstDefinedStep(traceSteps, "first_board_collision_step");

    return {
      case_id: proofCase.caseId,
      hold_profile: proofCase.holdProfile,
      dt_ms: PR0206_DT_MS,
      hold_steps: proofCase.holdSteps,
      relaunch_gap_steps: PR0206_RELAUNCH_GAP_STEPS,
      observation_steps: PR0206_OBSERVATION_STEPS,
      board_drop_observation_steps: PR0209_BOARD_DROP_OBSERVATION_STEPS,
      phase_order_observed: phaseOrderObserved,
      sw16_exit_observed: sw16ExitObserved,
      handoff_to_board_step: handoffToBoardStep,
      first_board_collision_step: firstBoardCollisionStep,
      peak_speed: peakSpeed,
      min_vy: Number.isFinite(minVy) ? minVy : 0,
      max_displacement_px: maxDisplacement,
      strike_classification: classifyStrikeFromContact({
        maxOverlapPx,
        minRelativeVyAtContact: normalizedMinRelativeVyAtContact,
        impulseTransferMarker,
        routeCaptureDecision,
      }),
      invariant_violations: evaluateTraceCaseInvariants({
        proofCase,
        phaseOrderObserved,
        sw16ExitObserved,
        handoffToBoardStep,
        firstBoardCollisionStep,
        traceSteps,
      }),
      trace_steps: traceSteps,
    };
  } finally {
    world.dispose();
  }
}

export async function runLaunchToDropTraceMatrix(args: {
  PhysicsWorld: typeof PhysicsWorldType;
  gateTag: string;
  proofCases?: readonly LaunchProofCaseContract[];
}): Promise<LaunchToDropTraceArtifactPayload> {
  const records: LaunchToDropTraceCaseRecord[] = [];

  for (const proofCase of args.proofCases ?? PR0206_PROOF_MATRIX_CASES) {
    records.push(await runLaunchToDropTraceCase(args.PhysicsWorld, proofCase, args.gateTag));
  }

  return buildLaunchToDropTraceArtifactPayload(records);
}
