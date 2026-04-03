/**
 * Capture/save lifecycle state for Flunk-Out Frenzy physics.
 *
 * This helper owns capture hold/eject timing and per-device cooldown handling.
 * `PhysicsWorld` feeds semantic machine events into this state machine and
 * applies the returned actions to the active ball body.
 */

import type {
  TableCaptureDeviceDefinition,
  TablePoint,
  TableSaveDeviceDefinition,
} from "../table/tableDefinitionTypes";
import type {
  CaptureMachineEventKind,
  MachineEvent,
} from "./physicsTypes";

interface ActiveCaptureState {
  tag: string;
  deviceKind: CaptureMachineEventKind;
  center: TablePoint;
  holdRemainingMs: number;
  ejectImpulse: TablePoint;
}

export interface CaptureLifecycleState {
  readonly deviceCooldownsMs: Map<string, number>;
  activeCapture: ActiveCaptureState | null;
}

export interface CaptureLifecycleStepResult {
  readonly forwardedEvents: MachineEvent[];
  readonly postStepEvents: MachineEvent[];
  readonly impulses: readonly TablePoint[];
  readonly holdPosition: TablePoint | null;
}

export interface CaptureLifecycleStepArgs {
  state: CaptureLifecycleState;
  events: readonly MachineEvent[];
  dtMs: number;
  hasBall: boolean;
  captureDevicesByTag: ReadonlyMap<string, TableCaptureDeviceDefinition>;
  saveDevicesByTag: ReadonlyMap<string, TableSaveDeviceDefinition>;
}

export function createCaptureDeviceTagIndex(
  devices: readonly TableCaptureDeviceDefinition[],
): ReadonlyMap<string, TableCaptureDeviceDefinition> {
  return new Map(devices.map((device) => [device.tag, device]));
}

export function createSaveDeviceTagIndex(
  devices: readonly TableSaveDeviceDefinition[],
): ReadonlyMap<string, TableSaveDeviceDefinition> {
  return new Map(devices.map((device) => [device.tag, device]));
}

export function createInitialCaptureLifecycleState(): CaptureLifecycleState {
  return {
    deviceCooldownsMs: new Map(),
    activeCapture: null,
  };
}

export function resetCaptureLifecycleState(state: CaptureLifecycleState): void {
  state.deviceCooldownsMs.clear();
  state.activeCapture = null;
}

export function applyCaptureLifecycleStep(args: CaptureLifecycleStepArgs): CaptureLifecycleStepResult {
  const {
    state,
    events,
    dtMs,
    hasBall,
    captureDevicesByTag,
    saveDevicesByTag,
  } = args;

  tickDeviceCooldowns(state.deviceCooldownsMs, dtMs);

  if (!hasBall) {
    state.activeCapture = null;
    return {
      forwardedEvents: [...events],
      postStepEvents: [],
      impulses: [],
      holdPosition: null,
    };
  }

  const forwardedEvents: MachineEvent[] = [];
  const postStepEvents: MachineEvent[] = [];
  const impulses: TablePoint[] = [];

  for (const event of events) {
    if (event.type === "ball-captured") {
      const capture = captureDevicesByTag.get(event.tag);
      if (!capture || hasActiveCooldown(state.deviceCooldownsMs, capture.tag)) {
        continue;
      }

      state.deviceCooldownsMs.set(capture.tag, capture.cooldownMs);
      state.activeCapture = {
        tag: capture.tag,
        deviceKind: capture.kind,
        center: { x: capture.x, y: capture.y },
        holdRemainingMs: capture.holdMs,
        ejectImpulse: capture.ejectImpulse,
      };
      forwardedEvents.push(event);
      continue;
    }

    if (event.type === "ball-saved") {
      const save = saveDevicesByTag.get(event.tag);
      if (!save || hasActiveCooldown(state.deviceCooldownsMs, save.tag)) {
        continue;
      }

      state.deviceCooldownsMs.set(save.tag, save.cooldownMs);
      impulses.push(save.saveImpulse);
      forwardedEvents.push(event);
      continue;
    }

    forwardedEvents.push(event);
  }

  let holdPosition: TablePoint | null = null;

  if (state.activeCapture) {
    state.activeCapture.holdRemainingMs -= dtMs;
    if (state.activeCapture.holdRemainingMs <= 0) {
      impulses.push(state.activeCapture.ejectImpulse);
      postStepEvents.push({
        type: "ball-ejected",
        tag: state.activeCapture.tag,
        deviceKind: state.activeCapture.deviceKind,
      });
      state.activeCapture = null;
    } else {
      holdPosition = state.activeCapture.center;
    }
  }

  return {
    forwardedEvents,
    postStepEvents,
    impulses,
    holdPosition,
  };
}

function hasActiveCooldown(cooldowns: ReadonlyMap<string, number>, tag: string): boolean {
  return cooldowns.has(tag);
}

function tickDeviceCooldowns(cooldowns: Map<string, number>, dtMs: number): void {
  for (const [tag, remainingMs] of [...cooldowns.entries()]) {
    const nextRemaining = remainingMs - dtMs;
    if (nextRemaining <= 0) {
      cooldowns.delete(tag);
      continue;
    }
    cooldowns.set(tag, nextRemaining);
  }
}
