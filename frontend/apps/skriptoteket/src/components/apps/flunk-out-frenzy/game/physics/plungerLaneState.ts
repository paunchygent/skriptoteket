/**
 * Explicit launcher-lane state machine for Flunk-Out Frenzy.
 *
 * This helper keeps launcher feed, charge, release, and relaunch timing
 * private to the physics layer while emitting a small semantic event seam for
 * downstream rules and presentation work.
 */

import type { MachineEvent } from "./physicsTypes";
import type {
  TableLauncherDefinition,
  TablePoint,
} from "../table/tableDefinitionTypes";

export type PlungerLanePhase =
  | "idle"
  | "feeding"
  | "fed"
  | "charging"
  | "released"
  | "relaunch";

export interface PlungerLaneBallSnapshot {
  position: TablePoint;
  velocity: TablePoint;
}

export interface PlungerLaneState {
  phase: PlungerLanePhase;
  chargeMs: number;
  relaunchCooldownMs: number;
  chargedEventEmitted: boolean;
}

export interface PlungerLaneStepResult {
  nextState: PlungerLaneState;
  machineEvents: MachineEvent[];
  releaseImpulse: TablePoint | null;
}

export interface StepPlungerLaneStateArgs {
  state: PlungerLaneState;
  ball: PlungerLaneBallSnapshot | null;
  launchPressed: boolean;
  launcher: TableLauncherDefinition;
  dtMs: number;
}

export function createInitialPlungerLaneState(): PlungerLaneState {
  return {
    phase: "idle",
    chargeMs: 0,
    relaunchCooldownMs: 0,
    chargedEventEmitted: false,
  };
}

export function stepPlungerLaneState(args: StepPlungerLaneStateArgs): PlungerLaneStepResult {
  const { state, ball, launchPressed, launcher, dtMs } = args;
  const machineEvents: MachineEvent[] = [];

  if (!ball || !isBallInLauncherLane(ball.position, launcher)) {
    return {
      nextState: createInitialPlungerLaneState(),
      machineEvents,
      releaseImpulse: null,
    };
  }

  const ballSettled = isBallSettled(ball, launcher);
  const ballReadyForCharge = ballSettled
    || state.phase === "fed"
    || state.phase === "charging";

  if (state.phase === "released" || state.phase === "relaunch") {
    const relaunchCooldownMs = Math.max(state.relaunchCooldownMs - dtMs, 0);
    const cooledState: PlungerLaneState = {
      phase: relaunchCooldownMs > 0 ? "relaunch" : state.phase,
      chargeMs: 0,
      relaunchCooldownMs,
      chargedEventEmitted: false,
    };

    if (relaunchCooldownMs === 0 && ballSettled) {
      return enterFedState(cooledState, launcher.tag, launchPressed, launcher, dtMs);
    }

    return {
      nextState: {
        ...cooledState,
        phase: relaunchCooldownMs > 0 ? "relaunch" : "feeding",
      },
      machineEvents,
      releaseImpulse: null,
    };
  }

  if (!ballReadyForCharge) {
    return {
      nextState: {
        phase: "feeding",
        chargeMs: 0,
        relaunchCooldownMs: 0,
        chargedEventEmitted: false,
      },
      machineEvents,
      releaseImpulse: null,
    };
  }

  if (state.phase === "charging" && !launchPressed && state.chargeMs > 0) {
    return {
      nextState: {
        phase: "released",
        chargeMs: 0,
        relaunchCooldownMs: launcher.relaunchCooldownMs,
        chargedEventEmitted: false,
      },
      machineEvents: [{ type: "launcher-released", tag: launcher.tag }],
      releaseImpulse: resolveReleaseImpulse(launcher, state.chargeMs),
    };
  }

  return enterFedState(state, launcher.tag, launchPressed, launcher, dtMs);
}

function enterFedState(
  state: PlungerLaneState,
  tag: string,
  launchPressed: boolean,
  launcher: TableLauncherDefinition,
  dtMs: number,
): PlungerLaneStepResult {
  const machineEvents: MachineEvent[] = [];
  const enteringReadyState = state.phase !== "fed" && state.phase !== "charging";

  if (enteringReadyState) {
    machineEvents.push({ type: "launcher-fed", tag });
  }

  if (!launchPressed) {
    return {
      nextState: {
        phase: "fed",
        chargeMs: 0,
        relaunchCooldownMs: 0,
        chargedEventEmitted: false,
      },
      machineEvents,
      releaseImpulse: null,
    };
  }

  const nextChargeMs = Math.min(state.chargeMs + dtMs, launcher.chargeMsMax);
  const crossedChargeThreshold = !state.chargedEventEmitted && nextChargeMs >= launcher.chargeMsMin;
  if (crossedChargeThreshold) {
    machineEvents.push({ type: "launcher-charged", tag });
  }

  return {
    nextState: {
      phase: "charging",
      chargeMs: nextChargeMs,
      relaunchCooldownMs: 0,
      chargedEventEmitted: state.chargedEventEmitted || crossedChargeThreshold,
    },
    machineEvents,
    releaseImpulse: null,
  };
}

function isBallInLauncherLane(
  position: TablePoint,
  launcher: TableLauncherDefinition,
): boolean {
  return position.x >= launcher.laneBounds.minX
    && position.x <= launcher.laneBounds.maxX
    && position.y >= launcher.laneBounds.minY
    && position.y <= launcher.laneBounds.maxY;
}

function isBallSettled(
  ball: PlungerLaneBallSnapshot,
  launcher: TableLauncherDefinition,
): boolean {
  return Math.hypot(ball.velocity.x, ball.velocity.y) <= launcher.feedSettledSpeedMax;
}

function resolveReleaseImpulse(
  launcher: TableLauncherDefinition,
  chargeMs: number,
): TablePoint {
  const chargeRatio = launcher.chargeMsMax === 0
    ? 1
    : clamp(chargeMs / launcher.chargeMsMax, 0, 1);
  const impulse = launcher.launchImpulseMin
    + (launcher.launchImpulseMax - launcher.launchImpulseMin) * chargeRatio;

  return {
    x: launcher.launchAssistX,
    y: -impulse,
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
