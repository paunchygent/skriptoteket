/**
 * Test-support telemetry helpers for Flunk-Out Frenzy physics proofs.
 *
 * This module keeps legacy proof-test imports stable while delegating the
 * canonical launch-trace contract and deterministic matrix runner to shared
 * non-test modules. Only test-only filesystem persistence and generic physics
 * stepping helpers remain local here.
 */

import type { PhysicsWorld as PhysicsWorldType } from "../PhysicsWorld";
import type { MachineEvent } from "../physicsTypes";
import type { LaunchToDropTraceArtifactPayload } from "../launchTraceContract";

export {
  buildLaunchToDropTraceArtifactPayload,
  classifyStrikeFromContact,
  distinctPhases,
  evaluateTraceCaseInvariants,
  firstDefinedStep,
  normalizeRouteCaptureDecision,
  normalizeRouteCaptureReason,
  PR0206_DT_MS,
  PR0206_OBSERVATION_STEPS,
  PR0206_PRE_RELEASE_STABILITY_STEPS,
  PR0206_PROOF_MATRIX_CASES,
  PR0206_RELAUNCH_GAP_STEPS,
  PR0209_BOARD_DROP_OBSERVATION_STEPS,
  summarizeInvariantFailures,
  toLaunchToDropTraceStepRecord,
  type LaunchProofCaseContract,
  type LaunchProofCaseRecord,
  type LaunchProofHoldProfile,
  type LaunchProofRouteCaptureDecision,
  type LaunchProofRouteRejectReason,
  type LaunchProofStrikeClassification,
  type LaunchToDropPhase,
  type LaunchToDropTraceCaseRecord,
  type LaunchToDropTraceStepRecord,
} from "../launchTraceContract";
export { collectEventsUntil, executeRelease, runLaunchToDropTraceCase } from "../launchTraceMatrix";

export async function writeLaunchToDropTraceArtifact(
  payload: LaunchToDropTraceArtifactPayload,
): Promise<void> {
  const loadFsPromises = Function(
    "return typeof require !== 'undefined' ? require('fs/promises') : null",
  ) as () => {
    mkdir(path: string, options?: { recursive?: boolean }): Promise<void>;
    writeFile(path: string, data: string, encoding: "utf-8"): Promise<void>;
  } | null;
  const fsPromises = loadFsPromises();
  if (!fsPromises) {
    return;
  }
  const artifactDir = ".artifacts/flunk-out-frenzy-launch-to-drop";
  const artifactPath = `${artifactDir}/launch-to-drop-trace-matrix.json`;
  await fsPromises.mkdir(artifactDir, { recursive: true });
  await fsPromises.writeFile(
    artifactPath,
    `${JSON.stringify(payload, null, 2)}\n`,
    "utf-8",
  );
}

export function collectEventsForSteps(
  world: PhysicsWorldType,
  steps: number,
): MachineEvent[] {
  const events: MachineEvent[] = [];

  for (let index = 0; index < steps; index += 1) {
    events.push(...world.step(16));
  }

  return events;
}

export function trackMinimumBallY(world: PhysicsWorldType, steps: number): number {
  let minY = world.currentSnapshot().ball?.y ?? Number.POSITIVE_INFINITY;

  for (let index = 0; index < steps; index += 1) {
    world.step(16);
    minY = Math.min(minY, world.currentSnapshot().ball?.y ?? minY);
  }

  return minY;
}

export function trackMinimumBallX(world: PhysicsWorldType, steps: number): number {
  let minX = world.currentSnapshot().ball?.x ?? Number.POSITIVE_INFINITY;

  for (let index = 0; index < steps; index += 1) {
    world.step(16);
    minX = Math.min(minX, world.currentSnapshot().ball?.x ?? minX);
  }

  return minX;
}
