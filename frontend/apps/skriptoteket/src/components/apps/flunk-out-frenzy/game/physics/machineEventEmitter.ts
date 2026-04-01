/**
 * Rapier contact translation for Flunk-Out Frenzy physics.
 *
 * This module converts collider metadata plus authored impulses into the
 * semantic machine events consumed by the rule engine, keeping raw Rapier
 * contact handling out of `PhysicsWorld`.
 */

import RAPIER from "@dimforge/rapier2d-compat";

import type { PrototypeAlphaTable } from "../table/prototypeAlphaTable";
import type { TablePoint } from "../table/tableDefinitionTypes";
import type { ColliderMeta } from "./colliderMeta";
import { resolveMachineColliderMeta } from "./colliderMeta";
import type { MachineEvent } from "./physicsTypes";

export interface MachineEventStepResult {
  events: MachineEvent[];
  shouldRemoveBall: boolean;
}

export interface MachineEventEmitterArgs {
  eventQueue: RAPIER.EventQueue;
  colliderMetaByHandle: ReadonlyMap<number, ColliderMeta>;
  cooldowns: Map<string, number>;
  ballBody: RAPIER.RigidBody | null;
  table: PrototypeAlphaTable;
}

export function collectMachineEvents(args: MachineEventEmitterArgs): MachineEventStepResult {
  const { eventQueue, colliderMetaByHandle, cooldowns, ballBody, table } = args;
  const events: MachineEvent[] = [];
  let shouldRemoveBall = false;

  eventQueue.drainCollisionEvents((handleOne, handleTwo, started) => {
    if (!started) {
      return;
    }

    const metaOne = colliderMetaByHandle.get(handleOne);
    const metaTwo = colliderMetaByHandle.get(handleTwo);
    const sensorMeta = resolveMachineColliderMeta(metaOne, metaTwo);
    if (!sensorMeta || !ballBody) {
      return;
    }

    switch (sensorMeta.kind) {
      case "bumper":
        if (hasActiveCooldown(cooldowns, sensorMeta.tag)) {
          return;
        }
        cooldowns.set(sensorMeta.tag, 90);
        fireBumperImpulse(ballBody, sensorMeta.center, sensorMeta.impulse);
        events.push({ type: "bumper-fired", tag: sensorMeta.tag });
        return;
      case "sling":
        if (hasActiveCooldown(cooldowns, sensorMeta.tag)) {
          return;
        }
        cooldowns.set(sensorMeta.tag, 110);
        ballBody.applyImpulse(sensorMeta.impulse, true);
        events.push({
          type: "sling-fired",
          tag: sensorMeta.tag,
          side: sensorMeta.side,
        });
        return;
      case "rollover":
        events.push({ type: "rollover-enter", tag: sensorMeta.tag });
        return;
      case "drain":
        events.push({ type: "drain-enter", tag: sensorMeta.tag });
        shouldRemoveBall = true;
        return;
      case "tripwire":
        if (hasActiveCooldown(cooldowns, sensorMeta.tag)) {
          return;
        }
        cooldowns.set(sensorMeta.tag, 70);
        events.push({ type: "tripwire-crossed", tag: sensorMeta.tag });
        return;
      case "standup-target":
        if (hasActiveCooldown(cooldowns, sensorMeta.tag)) {
          return;
        }
        cooldowns.set(sensorMeta.tag, 120);
        events.push({ type: "standup-target-hit", tag: sensorMeta.tag });
        return;
      case "popup-target":
        if (hasActiveCooldown(cooldowns, sensorMeta.tag)) {
          return;
        }
        cooldowns.set(sensorMeta.tag, 140);
        events.push({ type: "popup-target-hit", tag: sensorMeta.tag });
        return;
      case "gate":
        if (hasActiveCooldown(cooldowns, sensorMeta.tag)) {
          return;
        }
        cooldowns.set(sensorMeta.tag, 80);
        events.push({ type: "gate-passed", tag: sensorMeta.tag });
        return;
      case "launch-lane":
        events.push({ type: "launch-lane-enter", tag: sensorMeta.tag });
        return;
      case "capture":
        events.push({
          type: "ball-captured",
          tag: sensorMeta.tag,
          deviceKind: sensorMeta.deviceKind,
        });
        return;
      case "save":
        events.push({
          type: "ball-saved",
          tag: sensorMeta.tag,
          deviceKind: sensorMeta.deviceKind,
        });
        return;
    }
  });

  if (ballBody && ballBody.translation().y > table.board.height + 60) {
    events.push({ type: "drain-enter", tag: table.drain.tag });
    shouldRemoveBall = true;
  }

  return {
    events,
    shouldRemoveBall,
  };
}

function hasActiveCooldown(cooldowns: ReadonlyMap<string, number>, tag: string): boolean {
  return cooldowns.has(tag);
}

function fireBumperImpulse(
  ballBody: RAPIER.RigidBody,
  center: TablePoint,
  impulse: number,
): void {
  const ballPosition = ballBody.translation();
  const direction = {
    x: ballPosition.x - center.x,
    y: ballPosition.y - center.y,
  };
  const magnitude = Math.hypot(direction.x, direction.y) || 1;

  ballBody.applyImpulse(
    {
      x: (direction.x / magnitude) * impulse,
      y: (direction.y / magnitude) * impulse,
    },
    true,
  );
}
