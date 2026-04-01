/**
 * Target device construction for Flunk-Out Frenzy physics.
 *
 * Standup and popup targets are authored in the table definition and built as
 * static colliders plus semantic sensors so later rule slices can react to
 * target-bank progress without touching Rapier details directly.
 */

import RAPIER from "@dimforge/rapier2d-compat";

import type { ColliderMeta } from "./colliderMeta";
import type {
  TablePopupTargetDefinition,
  TableStandupTargetDefinition,
} from "../table/tableDefinitionTypes";

export interface CreateTargetDevicesArgs {
  world: RAPIER.World;
  colliderMetaByHandle: Map<number, ColliderMeta>;
  standupTargets: readonly TableStandupTargetDefinition[];
  popupTargets: readonly TablePopupTargetDefinition[];
}

export function createTargetDevices({
  world,
  colliderMetaByHandle,
  standupTargets,
  popupTargets,
}: CreateTargetDevicesArgs): void {
  for (const target of standupTargets) {
    const rotationRad = ((target.angleDeg ?? 0) * Math.PI) / 180;
    world.createCollider(
      RAPIER.ColliderDesc.cuboid(target.width / 2, target.height / 2)
        .setTranslation(target.x, target.y)
        .setRotation(rotationRad)
        .setRestitution(0.46)
        .setFriction(0.12),
    );

    const sensor = world.createCollider(
      RAPIER.ColliderDesc.cuboid(target.width / 2 + 2, target.height / 2 + 2)
        .setTranslation(target.x, target.y)
        .setRotation(rotationRad)
        .setSensor(true)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
    );
    colliderMetaByHandle.set(sensor.handle, {
      kind: "standup-target",
      tag: target.tag,
    });
  }

  for (const target of popupTargets) {
    world.createCollider(
      RAPIER.ColliderDesc.ball(target.radius)
        .setTranslation(target.x, target.y)
        .setRestitution(0.68)
        .setFriction(0.1),
    );

    const sensor = world.createCollider(
      RAPIER.ColliderDesc.ball(target.sensorRadius)
        .setTranslation(target.x, target.y)
        .setSensor(true)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
    );
    colliderMetaByHandle.set(sensor.handle, {
      kind: "popup-target",
      tag: target.tag,
    });
  }
}
