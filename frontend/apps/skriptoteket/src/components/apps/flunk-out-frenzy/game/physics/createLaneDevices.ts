/**
 * Lane and pass-through device construction for Flunk-Out Frenzy physics.
 *
 * These helpers build semantic sensor zones for authored rollovers, tripwires,
 * and simple gate lanes so `PhysicsWorld` can stay focused on orchestration.
 */

import RAPIER from "@dimforge/rapier2d-compat";

import type { ColliderMeta } from "./colliderMeta";
import type {
  TableGateDefinition,
  TableRolloverDefinition,
  TableTripwireDefinition,
} from "../table/tableDefinitionTypes";

export interface CreateLaneDevicesArgs {
  world: RAPIER.World;
  colliderMetaByHandle: Map<number, ColliderMeta>;
  rollovers: readonly TableRolloverDefinition[];
  tripwires: readonly TableTripwireDefinition[];
  gates: readonly TableGateDefinition[];
}

export function createLaneDevices({
  world,
  colliderMetaByHandle,
  rollovers,
  tripwires,
  gates,
}: CreateLaneDevicesArgs): void {
  for (const rollover of rollovers) {
    const sensor = world.createCollider(
      RAPIER.ColliderDesc.cuboid(rollover.width / 2, rollover.height / 2)
        .setTranslation(rollover.x, rollover.y)
        .setSensor(true)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
    );
    colliderMetaByHandle.set(sensor.handle, {
      kind: "rollover",
      tag: rollover.tag,
    });
  }

  for (const tripwire of tripwires) {
    const sensor = world.createCollider(
      RAPIER.ColliderDesc.cuboid(tripwire.width / 2, tripwire.height / 2)
        .setTranslation(tripwire.x, tripwire.y)
        .setSensor(true)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
    );
    colliderMetaByHandle.set(sensor.handle, {
      kind: "tripwire",
      tag: tripwire.tag,
    });
  }

  for (const gate of gates) {
    const sensor = world.createCollider(
      RAPIER.ColliderDesc.cuboid(gate.width / 2, gate.height / 2)
        .setTranslation(gate.x, gate.y)
        .setSensor(true)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
    );
    colliderMetaByHandle.set(sensor.handle, {
      kind: "gate",
      tag: gate.tag,
    });
  }
}
