/**
 * Launcher carrier-graph validation for the Flunk-Out Frenzy table compiler.
 *
 * This module owns the carrier-schema invariants introduced for PR-0217 so the
 * top-level table validator can stay focused on broad table integrity while
 * launcher-specific ownership, seam, and observation-spine rules remain
 * isolated and testable.
 */

import type {
  TableLauncherCarrier3DDefinition,
  TableLauncherDefinition,
  TableLauncherHandoffSeam3DDefinition,
  TableLauncherObservationSpine3DDefinition,
  TableLauncherPhysicalCarrier3DDefinition,
  TablePoint3D,
} from "../tableDefinitionTypes";

const LAUNCHER_CARRIER_SEAM_TOLERANCE = 1;

export function assertValidLauncherCarrierGraph(
  launcher: TableLauncherDefinition,
): void {
  const carriers = launcher.threeD.carriers;
  if (carriers.length === 0) {
    throw new Error(
      `Launcher "${launcher.tag}" must declare at least one 3D launcher carrier.`,
    );
  }

  const seenTags = new Set<string>();
  const donorSpanOwnerWorlds = new Map<string, string>();
  const observationSpines = new Map<
    string,
    TableLauncherObservationSpine3DDefinition
  >();
  const handoffSeams: TableLauncherHandoffSeam3DDefinition[] = [];
  let physicalCarrierCount = 0;

  for (const carrier of carriers) {
    if (seenTags.has(carrier.tag)) {
      throw new Error(`Launcher 3D carrier tag "${carrier.tag}" must be unique.`);
    }
    seenTags.add(carrier.tag);

    if (carrier.donorSourceIds.length === 0) {
      throw new Error(
        `Launcher 3D carrier "${carrier.tag}" must declare donor provenance.`,
      );
    }

    for (const ownedDonorSpanId of resolveOwnedDonorSpanIds(carrier)) {
      const existingOwnerWorld = donorSpanOwnerWorlds.get(ownedDonorSpanId);
      if (existingOwnerWorld && existingOwnerWorld !== carrier.ownerWorld) {
        throw new Error(
          `Launcher 3D carrier donor span "${ownedDonorSpanId}" must not be owned in multiple worlds.`,
        );
      }
      donorSpanOwnerWorlds.set(ownedDonorSpanId, carrier.ownerWorld);
    }

    switch (carrier.kind) {
      case "support":
      case "guard":
      case "receiver":
        physicalCarrierCount += 1;
        assertValidPhysicalCarrier(carrier);
        break;
      case "observation_spine":
        assertValidObservationSpine(carrier);
        observationSpines.set(carrier.tag, carrier);
        break;
      case "handoff_seam":
        assertValidHandoffSeam(carrier);
        handoffSeams.push(carrier);
        break;
    }
  }

  if (physicalCarrierCount === 0) {
    throw new Error(
      `Launcher "${launcher.tag}" must declare at least one physical carrier.`,
    );
  }

  if (observationSpines.size === 0) {
    throw new Error(
      `Launcher "${launcher.tag}" must declare at least one observation spine.`,
    );
  }

  if (handoffSeams.length !== 1) {
    throw new Error(
      `Launcher "${launcher.tag}" must declare exactly one terminal handoff seam.`,
    );
  }

  const handoffSeam = handoffSeams[0];
  const releaseEntrySpines = [...observationSpines.values()].filter((carrier) => {
    const entryMode = carrier.entryMode ?? "release";
    return entryMode === "release";
  });
  if (releaseEntrySpines.length === 0) {
    throw new Error(
      `Launcher "${launcher.tag}" must declare at least one release-entry observation spine.`,
    );
  }

  for (const spine of observationSpines.values()) {
    const nextCarrier = resolveNextCarrier(
      spine,
      observationSpines,
      handoffSeam,
    );
    if (nextCarrier.kind === "observation_spine") {
      const nextEntryMode = nextCarrier.entryMode ?? "release";
      if (nextEntryMode !== "chain") {
        throw new Error(
          `Launcher 3D observation spine "${nextCarrier.tag}" must declare entryMode "chain".`,
        );
      }
      assertContinuousLauncherSeam(
        spine.tag,
        nextCarrier.tag,
        spine.path[spine.path.length - 1],
        nextCarrier.path[0],
      );
      continue;
    }

    assertContinuousLauncherSeam(
      spine.tag,
      nextCarrier.tag,
      spine.path[spine.path.length - 1],
      nextCarrier.anchor,
    );
  }

  const visiting = new Set<string>();
  const visited = new Set<string>();
  const visit = (tag: string) => {
    if (visited.has(tag)) {
      return;
    }
    if (visiting.has(tag)) {
      throw new Error(
        `Launcher 3D observation spines must not form cycles (detected at "${tag}").`,
      );
    }

    visiting.add(tag);
    const spine = observationSpines.get(tag);
    if (!spine) {
      throw new Error(`Launcher 3D observation spine "${tag}" is not defined.`);
    }
    const nextCarrier = resolveNextCarrier(
      spine,
      observationSpines,
      handoffSeam,
    );
    if (nextCarrier.kind === "observation_spine") {
      visit(nextCarrier.tag);
    } else {
      visited.add(nextCarrier.tag);
    }
    visiting.delete(tag);
    visited.add(tag);
  };

  for (const releaseEntrySpine of releaseEntrySpines) {
    visit(releaseEntrySpine.tag);
  }

  if (!visited.has(handoffSeam.tag)) {
    throw new Error(
      `Launcher 3D handoff seam "${handoffSeam.tag}" must be reachable from the observation-spine graph.`,
    );
  }

  const expectedReachableCount = observationSpines.size + 1;
  if (visited.size !== expectedReachableCount) {
    throw new Error(
      `Launcher "${launcher.tag}" observation spines must form one connected graph ending at "${handoffSeam.tag}".`,
    );
  }
}

function assertValidPhysicalCarrier(
  carrier: TableLauncherPhysicalCarrier3DDefinition,
): void {
  if (carrier.compileRole !== "physical") {
    throw new Error(
      `Launcher 3D carrier "${carrier.tag}" kind "${carrier.kind}" must use compileRole "physical".`,
    );
  }
  if (carrier.ownerWorld !== "launcher") {
    throw new Error(
      `Launcher 3D carrier "${carrier.tag}" must stay in the launcher world before the terminal handoff seam.`,
    );
  }
  if (carrier.ownedDonorSpanIds.length === 0) {
    throw new Error(
      `Launcher 3D carrier "${carrier.tag}" must declare ownedDonorSpanIds.`,
    );
  }
  if (carrier.heightTop < carrier.heightBottom) {
    throw new Error(
      `Launcher 3D carrier "${carrier.tag}" must not invert height bounds.`,
    );
  }
  if (carrier.geometryKind === "extruded_polygon") {
    if (carrier.points.length < 3) {
      throw new Error(
        `Launcher 3D carrier "${carrier.tag}" polygon geometry must have at least three points.`,
      );
    }
    return;
  }

  if (carrier.path.length < 2) {
    throw new Error(
      `Launcher 3D carrier "${carrier.tag}" path geometry must have at least two points.`,
    );
  }
  if (carrier.radius <= 0) {
    throw new Error(
      `Launcher 3D carrier "${carrier.tag}" path geometry must have a positive radius.`,
    );
  }
}

function assertValidObservationSpine(
  carrier: TableLauncherObservationSpine3DDefinition,
): void {
  if (carrier.compileRole !== "observation") {
    throw new Error(
      `Launcher 3D carrier "${carrier.tag}" kind "observation_spine" must use compileRole "observation".`,
    );
  }
  if (carrier.ownerWorld !== "launcher") {
    throw new Error(
      `Launcher 3D observation spine "${carrier.tag}" must stay in the launcher world.`,
    );
  }
  if (carrier.path.length < 2) {
    throw new Error(
      `Launcher 3D observation spine "${carrier.tag}" must have at least two points.`,
    );
  }
  if (carrier.minChargeRatio < 0 || carrier.minChargeRatio > 1) {
    throw new Error(
      `Launcher 3D observation spine "${carrier.tag}" minChargeRatio must be in [0, 1].`,
    );
  }
}

function assertValidHandoffSeam(
  carrier: TableLauncherHandoffSeam3DDefinition,
): void {
  if (carrier.compileRole !== "terminal_seam") {
    throw new Error(
      `Launcher 3D carrier "${carrier.tag}" kind "handoff_seam" must use compileRole "terminal_seam".`,
    );
  }
  if (carrier.ownerWorld !== "launcher") {
    throw new Error(
      `Launcher 3D handoff seam "${carrier.tag}" must belong to the launcher world.`,
    );
  }
  if (carrier.targetWorld !== "board") {
    throw new Error(
      `Launcher 3D handoff seam "${carrier.tag}" must target the board world.`,
    );
  }
  if (
    carrier.handoffVelocity.x === 0 &&
    carrier.handoffVelocity.y === 0
  ) {
    throw new Error(
      `Launcher 3D handoff seam "${carrier.tag}" must declare a non-zero handoff velocity.`,
    );
  }
}

function resolveOwnedDonorSpanIds(
  carrier: TableLauncherCarrier3DDefinition,
): readonly string[] {
  if ("ownedDonorSpanIds" in carrier) {
    return carrier.ownedDonorSpanIds;
  }
  return [];
}

function resolveNextCarrier(
  carrier: TableLauncherObservationSpine3DDefinition,
  observationSpines: ReadonlyMap<string, TableLauncherObservationSpine3DDefinition>,
  handoffSeam: TableLauncherHandoffSeam3DDefinition,
): TableLauncherObservationSpine3DDefinition | TableLauncherHandoffSeam3DDefinition {
  const nextObservationSpine = observationSpines.get(carrier.nextCarrierTag);
  if (nextObservationSpine) {
    return nextObservationSpine;
  }
  if (carrier.nextCarrierTag === handoffSeam.tag) {
    return handoffSeam;
  }
  throw new Error(
    `Launcher 3D observation spine "${carrier.tag}" references unknown nextCarrierTag "${carrier.nextCarrierTag}".`,
  );
}

function assertContinuousLauncherSeam(
  fromTag: string,
  toTag: string,
  fromPoint: TablePoint3D,
  toPoint: TablePoint3D,
): void {
  const xyDelta = Math.hypot(fromPoint.x - toPoint.x, fromPoint.y - toPoint.y);
  const zDelta = Math.abs(fromPoint.z - toPoint.z);
  if (
    xyDelta > LAUNCHER_CARRIER_SEAM_TOLERANCE ||
    zDelta > LAUNCHER_CARRIER_SEAM_TOLERANCE
  ) {
    throw new Error(
      `Launcher 3D carrier seam "${fromTag}" -> "${toTag}" must be continuous ` +
        `(xy<=${LAUNCHER_CARRIER_SEAM_TOLERANCE}, z<=${LAUNCHER_CARRIER_SEAM_TOLERANCE}).`,
    );
  }
}
