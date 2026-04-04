import type { PhysicsWorld as PhysicsWorldType } from "../PhysicsWorld";
import type { MachineEvent } from "../physicsTypes";

export type LaunchProofHoldProfile = "rest" | "short" | "medium" | "full" | "relaunch";
export type LaunchProofStrikeClassification =
  | "no_effective_strike"
  | "post_strike_route_rejection"
  | "strike_and_route_accepted";
export type LaunchProofRouteCaptureDecision = "none" | "accepted" | "rejected";
export type LaunchProofRouteRejectReason =
  | "distance_xy"
  | "distance_z"
  | "vy_gate"
  | "window_expired"
  | "no_route";

export type LaunchProofCaseContract = Readonly<{
  caseId: string;
  holdProfile: LaunchProofHoldProfile;
  holdSteps: number;
  thresholdPx: number;
  thresholdVy: number;
  relaunchSecondHoldSteps?: number;
}>;

export type LaunchProofCaseRecord = Readonly<{
  case_id: string;
  hold_profile: LaunchProofHoldProfile;
  dt_ms: number;
  hold_steps: number;
  relaunch_gap_steps: number;
  observation_steps: number;
  threshold_px: number;
  threshold_vy: number;
  plunger_delta: number;
  ball_displacement_magnitude: number;
  max_vy: number;
  min_vy: number;
  feed_inside_at_rest: boolean;
  separation_px_at_rest: number;
  route_capture_decision: LaunchProofRouteCaptureDecision;
  route_capture_reason: LaunchProofRouteRejectReason | null;
  sw16_exit_observed: boolean;
  contact_diagnostics: {
    maxOverlapPx: number;
    minRelativeVyAtContact: number | null;
    impulseTransferMarker: number;
    lastContactAtStep: number | null;
  };
  strike_classification: LaunchProofStrikeClassification;
}>;

export type LaunchToDropPhase =
  | "feed_rest"
  | "charge_pull"
  | "release_strike_window"
  | "route_overhead"
  | "route_endpoint_bridge"
  | "route_descent"
  | "handoff_to_board"
  | "board_drop_preimpact"
  | "board_drop_postimpact";

export type LaunchToDropTraceStepRecord = Readonly<{
  step_index: number;
  dt_ms: number;
  phase: LaunchToDropPhase;
  ball_owner: "launcher_chain" | "main_world" | "none";
  ball_position: { x: number; y: number; z: number } | null;
  ball_velocity: { x: number; y: number; z: number } | null;
  plunger: {
    currentY: number;
    targetY: number;
    chargeRatio: number | null;
    phase: "idle" | "feeding" | "fed" | "charging" | "released" | "relaunch";
  };
  route: {
    pendingReleaseChargeRatio: number | null;
    activeRouteTag: string | null;
    captureWindowMsRemaining: number;
    routeProgressDistancePx: number;
  };
  route_capture: {
    lastDecision: "none" | "accepted" | "rejected";
    lastRejectReason: LaunchProofRouteRejectReason | null;
  };
  sensors: {
    feedInside: boolean;
    exitInside: boolean;
    lastSw16ExitStep: number | null;
  };
  contact: {
    plungerBallContactActive: boolean;
    contactEnteredThisStep: boolean;
    contactExitedThisStep: boolean;
    separationPx: number | null;
    overlapPx: number;
    relativeVyAtContact: number | null;
    lastContactAtStep: number | null;
    impulseTransferMarker: number;
  };
  seam_transition: {
    fromRouteTag: string;
    toRouteTag: string;
    xyDeltaPx: number;
    zDeltaPx: number;
  } | null;
  events: MachineEvent[];
  handoff_to_board_step: number | null;
  first_board_collision_step: number | null;
  board_collision_started_this_step: boolean;
}>;

export type LaunchToDropTraceCaseRecord = Readonly<{
  case_id: string;
  hold_profile: LaunchProofHoldProfile;
  dt_ms: number;
  hold_steps: number;
  relaunch_gap_steps: number;
  observation_steps: number;
  board_drop_observation_steps: number;
  phase_order_observed: LaunchToDropPhase[];
  sw16_exit_observed: boolean;
  handoff_to_board_step: number | null;
  first_board_collision_step: number | null;
  peak_speed: number;
  min_vy: number;
  max_displacement_px: number;
  strike_classification: LaunchProofStrikeClassification;
  invariant_violations: string[];
  trace_steps: LaunchToDropTraceStepRecord[];
}>;

export const PR0206_DT_MS = 16;
export const PR0206_PRE_RELEASE_STABILITY_STEPS = 10;
export const PR0206_OBSERVATION_STEPS = 60;
export const PR0206_RELAUNCH_GAP_STEPS = 16;
export const PR0209_BOARD_DROP_OBSERVATION_STEPS = 300;
export const PR0206_PROOF_MATRIX_CASES: readonly LaunchProofCaseContract[] = [
  {
    caseId: "K-REST-STEADY",
    holdProfile: "rest",
    holdSteps: 0,
    thresholdPx: 0,
    thresholdVy: 0,
  },
  {
    caseId: "K-SHORT-STEADY",
    holdProfile: "short",
    holdSteps: 8,
    thresholdPx: 2,
    thresholdVy: -8,
  },
  {
    caseId: "K-MEDIUM-STEADY",
    holdProfile: "medium",
    holdSteps: 26,
    thresholdPx: 4,
    thresholdVy: -20,
  },
  {
    caseId: "K-FULL-STEADY",
    holdProfile: "full",
    holdSteps: 56,
    thresholdPx: 8,
    thresholdVy: -40,
  },
  {
    caseId: "K-RELAUNCH-MEDIUM",
    holdProfile: "relaunch",
    holdSteps: 26,
    relaunchSecondHoldSteps: 26,
    thresholdPx: 4,
    thresholdVy: -20,
  },
];

export function collectEventsUntil(
  world: PhysicsWorldType,
  maxSteps: number,
  predicate: (events: MachineEvent[]) => boolean,
): MachineEvent[] {
  for (let index = 0; index < maxSteps; index += 1) {
    const events = world.step(16);
    if (predicate(events)) {
      return events;
    }
  }

  throw new Error("Expected machine events were not emitted in time.");
}

export function classifyStrikeFromContact(args: {
  maxOverlapPx: number;
  minRelativeVyAtContact: number | null;
  impulseTransferMarker: number;
  routeCaptureDecision: LaunchProofRouteCaptureDecision;
}): LaunchProofStrikeClassification {
  const strikeEvidencePresent =
    args.maxOverlapPx >= 0.5 ||
    (args.minRelativeVyAtContact ?? Number.POSITIVE_INFINITY) <= -5 ||
    args.impulseTransferMarker >= 0.1;
  if (!strikeEvidencePresent) {
    return "no_effective_strike";
  }
  if (args.routeCaptureDecision === "accepted") {
    return "strike_and_route_accepted";
  }
  return "post_strike_route_rejection";
}

export function normalizeRouteCaptureDecision(
  value: string | null | undefined,
): LaunchProofRouteCaptureDecision {
  if (value === "accepted" || value === "rejected" || value === "none") {
    return value;
  }
  return "none";
}

export function normalizeRouteCaptureReason(
  value: string | null | undefined,
): LaunchProofRouteRejectReason | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (
    value === "distance_xy" ||
    value === "distance_z" ||
    value === "vy_gate" ||
    value === "window_expired" ||
    value === "no_route"
  ) {
    return value;
  }
  return null;
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

export function distinctPhases(
  traceSteps: readonly LaunchToDropTraceStepRecord[],
): LaunchToDropPhase[] {
  const phases: LaunchToDropPhase[] = [];
  for (const step of traceSteps) {
    if (phases.includes(step.phase)) {
      continue;
    }
    phases.push(step.phase);
  }
  return phases;
}

export function firstDefinedStep(
  traceSteps: readonly LaunchToDropTraceStepRecord[],
  key: "handoff_to_board_step" | "first_board_collision_step",
): number | null {
  for (const step of traceSteps) {
    const value = step[key];
    if (value !== null) {
      return value;
    }
  }
  return null;
}

export function evaluateTraceCaseInvariants(args: {
  proofCase: LaunchProofCaseContract;
  phaseOrderObserved: readonly LaunchToDropPhase[];
  sw16ExitObserved: boolean;
  handoffToBoardStep: number | null;
  firstBoardCollisionStep: number | null;
  traceSteps: readonly LaunchToDropTraceStepRecord[];
}): string[] {
  const violations: string[] = [];
  const isQualifyingCase =
    args.proofCase.holdProfile === "medium" ||
    args.proofCase.holdProfile === "full" ||
    args.proofCase.holdProfile === "relaunch";

  if (isQualifyingCase) {
    const requiredPhases: readonly LaunchToDropPhase[] = [
      "route_overhead",
      "route_endpoint_bridge",
      "route_descent",
      "handoff_to_board",
      "board_drop_preimpact",
    ];
    for (const phase of requiredPhases) {
      if (!args.phaseOrderObserved.includes(phase)) {
        violations.push(`missing_phase:${phase}`);
      }
    }
    if (!args.sw16ExitObserved) {
      violations.push("missing_sw16_exit");
    }
    if (args.handoffToBoardStep === null) {
      violations.push("missing_handoff_to_board_step");
    }
  }

  if (args.proofCase.holdProfile === "full" && args.firstBoardCollisionStep === null) {
    violations.push("missing_first_board_collision_step_for_full_case");
  }

  if (args.proofCase.holdProfile === "rest") {
    if (args.sw16ExitObserved) {
      violations.push("rest_case_unexpected_sw16_exit");
    }
    if (args.handoffToBoardStep !== null) {
      violations.push("rest_case_unexpected_handoff");
    }
    if (args.firstBoardCollisionStep !== null) {
      violations.push("rest_case_unexpected_board_collision");
    }
  }

  if (args.firstBoardCollisionStep !== null) {
    if (args.handoffToBoardStep === null) {
      violations.push("board_collision_without_handoff");
    } else if (args.firstBoardCollisionStep <= args.handoffToBoardStep) {
      violations.push("board_collision_not_post_handoff");
    }
  }

  for (const step of args.traceSteps) {
    if (
      step.first_board_collision_step !== null &&
      step.handoff_to_board_step === null
    ) {
      violations.push("trace_step_board_collision_without_handoff_marker");
      break;
    }
  }

  return violations;
}

export function buildLaunchToDropTraceArtifactPayload(
  records: readonly LaunchToDropTraceCaseRecord[],
) {
  return {
    metadata: {
      generated_at_utc: new Date().toISOString(),
      repo_branch: "local",
      engine_version_marker: "pr-0209-launch-to-drop-trace",
    },
    matrix_summaries: records.map((record) => {
      const { trace_steps: _trace_steps, ...summary } = record;
      return summary;
    }),
    traces: Object.fromEntries(
      records.map((record) => [record.case_id, record.trace_steps]),
    ),
  };
}

export async function writeLaunchToDropTraceArtifact(
  payload: ReturnType<typeof buildLaunchToDropTraceArtifactPayload>,
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
