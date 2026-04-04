/**
 * Pulse-resolution helpers for the Flunk-Out Frenzy Pixi renderer.
 *
 * The renderer itself stays focused on canvas orchestration while this module
 * translates semantic game effects into concrete pulse descriptors.
 */

import type { GameEffectEvent } from "../presentation/gameEffectTypes";
import { PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";
import type { TableTriggerShapeDefinition } from "../table/tableDefinitionTypes";

export type PixiPulseDescriptor = Readonly<{
  x: number;
  y: number;
  radius: number;
  color: number;
  durationMs: number;
}>;

export function resolvePixiPulseDescriptors(
  effects: readonly GameEffectEvent[],
): PixiPulseDescriptor[] {
  const descriptors: PixiPulseDescriptor[] = [];

  for (const effect of effects) {
    switch (effect.type) {
      case "bumper-hit": {
        const bumper = PROTOTYPE_ALPHA_TABLE.bumpers.find((item) => item.tag === effect.tag);
        if (bumper) {
          descriptors.push({ x: bumper.x, y: bumper.y, radius: 32, color: 0x69ff7d, durationMs: 170 });
        }
        break;
      }
      case "sling-hit": {
        const sling = PROTOTYPE_ALPHA_TABLE.slings.find((item) => item.tag === effect.tag);
        if (sling) {
          descriptors.push({
            x: (sling.vertices[0].x + sling.vertices[1].x + sling.vertices[2].x) / 3,
            y: (sling.vertices[0].y + sling.vertices[1].y + sling.vertices[2].y) / 3,
            radius: 26,
            color: 0xff8a47,
            durationMs: 150,
          });
        }
        break;
      }
      case "rollover-lit": {
        const rollover = PROTOTYPE_ALPHA_TABLE.rollovers.find((item) => item.tag === effect.tag);
        if (rollover) {
          descriptors.push({ x: rollover.x, y: rollover.y, radius: 22, color: 0xffee8d, durationMs: 130 });
        }
        break;
      }
      case "tripwire-crossed": {
        const tripwire = PROTOTYPE_ALPHA_TABLE.tripwires.find((item) => item.tag === effect.tag);
        if (tripwire) {
          const center = resolveTriggerEffectCenter(tripwire);
          descriptors.push({ x: center.x, y: center.y, radius: 28, color: 0x6be9ff, durationMs: 140 });
        }
        break;
      }
      case "standup-target-hit": {
        const target = PROTOTYPE_ALPHA_TABLE.standupTargets.find((item) => item.tag === effect.tag);
        if (target) {
          descriptors.push({ x: target.x, y: target.y, radius: 24, color: 0xffc769, durationMs: 155 });
        }
        break;
      }
      case "popup-target-hit": {
        const target = PROTOTYPE_ALPHA_TABLE.popupTargets.find((item) => item.tag === effect.tag);
        if (target) {
          descriptors.push({
            x: target.x,
            y: target.y,
            radius: target.radius + 10,
            color: 0xff8df0,
            durationMs: 165,
          });
        }
        break;
      }
      case "gate-passed": {
        const gate = PROTOTYPE_ALPHA_TABLE.gates.find((item) => item.tag === effect.tag);
        if (gate) {
          const center = resolveTriggerEffectCenter(gate);
          descriptors.push({ x: center.x, y: center.y, radius: 22, color: 0x9ee081, durationMs: 130 });
        }
        break;
      }
      case "ball-captured": {
        const captureDevice = PROTOTYPE_ALPHA_TABLE.captureDevices.find((item) => item.tag === effect.tag);
        if (captureDevice) {
          descriptors.push({
            x: captureDevice.x,
            y: captureDevice.y,
            radius: Math.max(captureDevice.width, captureDevice.height) * 0.62,
            color: 0x66f0ff,
            durationMs: 170,
          });
        }
        break;
      }
      case "ball-ejected": {
        const captureDevice = PROTOTYPE_ALPHA_TABLE.captureDevices.find((item) => item.tag === effect.tag);
        if (captureDevice) {
          descriptors.push({
            x: captureDevice.x,
            y: captureDevice.y,
            radius: Math.max(captureDevice.width, captureDevice.height) * 0.82,
            color: 0xffbf72,
            durationMs: 180,
          });
        }
        break;
      }
      case "ball-saved": {
        const saveDevice = PROTOTYPE_ALPHA_TABLE.saveDevices.find((item) => item.tag === effect.tag);
        if (saveDevice) {
          descriptors.push({
            x: saveDevice.x,
            y: saveDevice.y,
            radius: Math.max(saveDevice.width, saveDevice.height) * 0.7,
            color: 0x91ffc6,
            durationMs: 175,
          });
        }
        break;
      }
      case "late-bank-complete":
        descriptors.push({ x: 300, y: 146, radius: 110, color: 0xffee8d, durationMs: 280 });
        break;
      case "bonus-awarded":
        descriptors.push({ x: 300, y: 1030, radius: 72, color: 0xffcf7c, durationMs: 240 });
        break;
      case "jackpot-lit":
        descriptors.push({ x: 300, y: 250, radius: 48, color: 0xff8df0, durationMs: 200 });
        break;
      case "jackpot-awarded":
        descriptors.push({ x: 300, y: 420, radius: 126, color: 0xff8df0, durationMs: 300 });
        break;
      case "capture-awarded":
        descriptors.push({ x: 300, y: 980, radius: 62, color: 0x66f0ff, durationMs: 240 });
        break;
      case "eject-awarded":
        descriptors.push({ x: 300, y: 900, radius: 56, color: 0xffbf72, durationMs: 220 });
        break;
      case "save-awarded":
        descriptors.push({ x: 300, y: 850, radius: 64, color: 0x91ffc6, durationMs: 250 });
        break;
      case "shoot-again-lit":
        descriptors.push({
          x: PROTOTYPE_ALPHA_TABLE.ball.spawn.x,
          y: 930,
          radius: 42,
          color: 0x8dffcf,
          durationMs: 220,
        });
        break;
      case "ball-drained":
        descriptors.push({ x: 300, y: 1136, radius: 54, color: 0xff5d92, durationMs: 200 });
        break;
      case "ball-spawned":
        descriptors.push({
          x: PROTOTYPE_ALPHA_TABLE.ball.spawn.x,
          y: PROTOTYPE_ALPHA_TABLE.ball.spawn.y,
          radius: 24,
          color: 0xb8c5ff,
          durationMs: 150,
        });
        break;
      case "game-over":
        descriptors.push({ x: 300, y: 680, radius: 150, color: 0xff5d92, durationMs: 360 });
        break;
      case "round-started":
      case "flipper-fired":
      case "launch-released":
        break;
    }
  }

  return descriptors;
}

function resolveTriggerEffectCenter(
  trigger:
    | (typeof PROTOTYPE_ALPHA_TABLE.tripwires)[number]
    | (typeof PROTOTYPE_ALPHA_TABLE.gates)[number],
): { x: number; y: number } {
  if ("shape" in trigger) {
    return centerForTriggerShape(trigger.shape);
  }
  return { x: trigger.x, y: trigger.y };
}

function centerForTriggerShape(shape: TableTriggerShapeDefinition): { x: number; y: number } {
  switch (shape.kind) {
    case "rect":
    case "circle":
    case "capsule":
    case "donor-wire-rollover":
      return shape.center;
    case "polygon":
      return polygonCentroid(shape.points);
  }
}

function polygonCentroid(points: readonly { x: number; y: number }[]): { x: number; y: number } {
  const count = points.length || 1;
  return {
    x: points.reduce((sum, point) => sum + point.x, 0) / count,
    y: points.reduce((sum, point) => sum + point.y, 0) / count,
  };
}
