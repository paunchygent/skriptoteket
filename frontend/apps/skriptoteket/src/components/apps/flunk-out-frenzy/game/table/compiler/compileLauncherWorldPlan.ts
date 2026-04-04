/**
 * Compiles launcher-world carrier geometry plans for Flunk-Out Frenzy.
 *
 * This module keeps launcher-world collider derivation in the compiler layer so
 * geometry builders can stay pure and runtime transport can continue to read
 * authored observation spines without silently inventing physical carrier data.
 */

import type {
  CompiledLauncherWorldAssemblyPlan,
  CompiledLauncherWorldCarrierRole,
  CompiledLauncherWorldOwnershipEntry,
  CompiledLauncherWorldPlan,
} from "../pinballTablePlanTypes";
import {
  VPW_METAL_RAIL_3D_SPECS,
} from "../prototypeAlphaVpwDonorMap";
import type {
  TableLauncherDefinition,
  TablePoint,
  TablePoint3D,
} from "../tableDefinitionTypes";

const MIN_HALF_HEIGHT = 0.5;
const MIN_BORDER_RADIUS = 0.35;

const OVERHEAD_SOURCE_CARRIER_TAGS = Object.freeze([
  "launcher/travel/overhead",
] as const);

const OVERHEAD_DONOR_SPANS = Object.freeze([
  {
    id: "shooter-vertical",
    roleSource: "entry",
    donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterVertical.donorSourceId,
    path: VPW_METAL_RAIL_3D_SPECS.shooterVertical.path,
    radius: VPW_METAL_RAIL_3D_SPECS.shooterVertical.radius,
  },
  {
    id: "shooter-mouth-connector",
    roleSource: "mid",
    donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.donorSourceId,
    path: VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.path,
    radius: VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.radius,
  },
  {
    id: "shooter-top-right",
    roleSource: "mid",
    donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterTopRight.donorSourceId,
    path: VPW_METAL_RAIL_3D_SPECS.shooterTopRight.path,
    radius: VPW_METAL_RAIL_3D_SPECS.shooterTopRight.radius,
  },
  {
    id: "shooter-top-arch",
    roleSource: "exit",
    donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.donorSourceId,
    path: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.path,
    radius: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.radius,
  },
] as const);

export function compileLauncherWorldPlan(
  launcher: TableLauncherDefinition,
  ballRestZ: number,
): CompiledLauncherWorldPlan {
  const assemblies = [
    ...compileAuthoredPhysicalCarrierAssemblies(launcher),
    ...compileOverheadDonorAssemblies(ballRestZ),
  ];

  assertValidLauncherWorldAssemblies(assemblies);

  return {
    assemblies,
    ownershipMatrix: buildOwnershipMatrix(assemblies),
  };
}

function compileAuthoredPhysicalCarrierAssemblies(
  launcher: TableLauncherDefinition,
): readonly CompiledLauncherWorldAssemblyPlan[] {
  const assemblies: CompiledLauncherWorldAssemblyPlan[] = [];

  for (const carrier of launcher.threeD.carriers) {
    if (carrier.compileRole !== "physical") {
      continue;
    }

    if (carrier.geometryKind === "extruded_polygon") {
      assemblies.push(
        {
          id: `${carrier.tag}:compiled`,
          primitiveKind: "prism_hull",
          role: carrier.kind,
          ownerWorld: carrier.ownerWorld,
          donorSourceIds: carrier.donorSourceIds,
          sourceCarrierTags: [carrier.tag],
          colliderIds: [`${carrier.tag}:compiled:hull`] as const,
          points: carrier.points,
          heightBottom: carrier.heightBottom,
          heightTop: carrier.heightTop,
        },
      );
      continue;
    }

    const centerZ = carrier.heightBottom + (carrier.heightTop - carrier.heightBottom) / 2;
    const halfHeight = Math.max(
      (carrier.heightTop - carrier.heightBottom) / 2,
      MIN_HALF_HEIGHT,
    );
    assemblies.push(
      {
        id: `${carrier.tag}:compiled`,
        primitiveKind: "cuboid_segment_path",
        role: carrier.kind,
        ownerWorld: carrier.ownerWorld,
        donorSourceIds: carrier.donorSourceIds,
        sourceCarrierTags: [carrier.tag],
        colliderIds: createSegmentColliderIds(`${carrier.tag}:compiled`, carrier.path.length),
        path: liftPlanarPathTo3D(carrier.path, centerZ),
        halfWidth: carrier.radius,
        halfHeight,
      },
    );
  }

  return assemblies;
}

function compileOverheadDonorAssemblies(
  ballRestZ: number,
): readonly CompiledLauncherWorldAssemblyPlan[] {
  const supportAssemblies = OVERHEAD_DONOR_SPANS.map((span) => {
    const supportHalfHeight = Math.max(span.radius * 0.75, MIN_HALF_HEIGHT);
    const supportBorderRadius = Math.max(span.radius * 0.35, MIN_BORDER_RADIUS);
    return {
      id: `launcher/compiled/overhead/${span.id}/support`,
      primitiveKind: "round_cuboid_segment_path" as const,
      role: "support" as const,
      ownerWorld: "launcher" as const,
      donorSourceIds: [span.donorSourceId],
      sourceCarrierTags: OVERHEAD_SOURCE_CARRIER_TAGS,
      colliderIds: createSegmentColliderIds(
        `launcher/compiled/overhead/${span.id}/support`,
        span.path.length,
      ),
      path: offsetPath3D(span.path, {
        lateralOffset: 0,
        verticalOffset: -(ballRestZ + supportHalfHeight),
      }),
      halfWidth: Math.max(span.radius * 1.35, 1.5),
      halfHeight: supportHalfHeight,
      borderRadius: supportBorderRadius,
    };
  });

  const guardAssemblies = OVERHEAD_DONOR_SPANS.flatMap((span) => {
    const lateralOffset = ballRestZ + span.radius * 1.1;
    const radius = Math.max(span.radius * 0.85, 1.1);
    return ([
      {
        id: `launcher/compiled/overhead/${span.id}/guard-left`,
        primitiveKind: "capsule_segment_path" as const,
        role: "guard" as const,
        ownerWorld: "launcher" as const,
        donorSourceIds: [span.donorSourceId],
        sourceCarrierTags: OVERHEAD_SOURCE_CARRIER_TAGS,
        colliderIds: createSegmentColliderIds(
          `launcher/compiled/overhead/${span.id}/guard-left`,
          span.path.length,
        ),
        path: offsetPath3D(span.path, {
          lateralOffset: -lateralOffset,
          verticalOffset: -(ballRestZ * 0.15),
        }),
        radius,
      },
      {
        id: `launcher/compiled/overhead/${span.id}/guard-right`,
        primitiveKind: "capsule_segment_path" as const,
        role: "guard" as const,
        ownerWorld: "launcher" as const,
        donorSourceIds: [span.donorSourceId],
        sourceCarrierTags: OVERHEAD_SOURCE_CARRIER_TAGS,
        colliderIds: createSegmentColliderIds(
          `launcher/compiled/overhead/${span.id}/guard-right`,
          span.path.length,
        ),
        path: offsetPath3D(span.path, {
          lateralOffset,
          verticalOffset: -(ballRestZ * 0.15),
        }),
        radius,
      },
    ] as const);
  });

  const receiverAssemblies = OVERHEAD_DONOR_SPANS.flatMap((span) => {
    if (span.roleSource === "mid") {
      return [];
    }

    const receiverId = `launcher/compiled/overhead/${span.id}/receiver`;
    const hullPoints = buildReceiverHullPoints(
      span.roleSource === "entry"
        ? [span.path[0], span.path[1]]
        : [span.path[span.path.length - 2], span.path[span.path.length - 1]],
      ballRestZ,
      span.radius,
    );

    return [
      {
        id: receiverId,
        primitiveKind: "round_convex_hull" as const,
        role: "receiver" as const,
        ownerWorld: "launcher" as const,
        donorSourceIds: [span.donorSourceId],
        sourceCarrierTags: OVERHEAD_SOURCE_CARRIER_TAGS,
        colliderIds: [`${receiverId}:hull`] as const,
        points: hullPoints,
        borderRadius: Math.max(span.radius * 0.45, MIN_BORDER_RADIUS),
      },
    ];
  });

  return [...supportAssemblies, ...guardAssemblies, ...receiverAssemblies];
}

function buildOwnershipMatrix(
  assemblies: readonly CompiledLauncherWorldAssemblyPlan[],
): readonly CompiledLauncherWorldOwnershipEntry[] {
  const matrixByKey = new Map<
    string,
    {
      donorSourceId: string;
      role: CompiledLauncherWorldCarrierRole;
      ownerWorld: "launcher";
      colliderIds: string[];
      assemblyIds: string[];
    }
  >();

  for (const assembly of assemblies) {
    for (const donorSourceId of assembly.donorSourceIds) {
      const key = `${donorSourceId}::${assembly.role}::${assembly.ownerWorld}`;
      const existing = matrixByKey.get(key);
      if (existing) {
        existing.colliderIds.push(...assembly.colliderIds);
        existing.assemblyIds.push(assembly.id);
        continue;
      }
      matrixByKey.set(key, {
        donorSourceId,
        role: assembly.role,
        ownerWorld: assembly.ownerWorld,
        colliderIds: [...assembly.colliderIds],
        assemblyIds: [assembly.id],
      });
    }
  }

  return [...matrixByKey.values()].map((entry) => {
    return {
      donorSourceId: entry.donorSourceId,
      role: entry.role,
      ownerWorld: entry.ownerWorld,
      colliderIds: [...new Set(entry.colliderIds)],
      assemblyIds: [...new Set(entry.assemblyIds)],
    };
  });
}

function assertValidLauncherWorldAssemblies(
  assemblies: readonly CompiledLauncherWorldAssemblyPlan[],
): void {
  const seenAssemblyIds = new Set<string>();
  const seenColliderIds = new Set<string>();

  for (const assembly of assemblies) {
    if (seenAssemblyIds.has(assembly.id)) {
      throw new Error(`Compiled launcher-world assembly "${assembly.id}" must be unique.`);
    }
    seenAssemblyIds.add(assembly.id);

    if (assembly.donorSourceIds.length === 0) {
      throw new Error(
        `Compiled launcher-world assembly "${assembly.id}" must declare donor provenance.`,
      );
    }
    if (assembly.colliderIds.length === 0) {
      throw new Error(
        `Compiled launcher-world assembly "${assembly.id}" must emit at least one collider id.`,
      );
    }
    for (const colliderId of assembly.colliderIds) {
      if (seenColliderIds.has(colliderId)) {
        throw new Error(`Compiled launcher-world collider "${colliderId}" must be unique.`);
      }
      seenColliderIds.add(colliderId);
    }
    if ("path" in assembly && assembly.path.length < 2) {
      throw new Error(
        `Compiled launcher-world assembly "${assembly.id}" path geometry must have at least two points.`,
      );
    }
    if ("points" in assembly && assembly.points.length < 3) {
      throw new Error(
        `Compiled launcher-world assembly "${assembly.id}" hull geometry must have at least three points.`,
      );
    }
  }
}

function liftPlanarPathTo3D(
  path: readonly TablePoint[],
  z: number,
): readonly TablePoint3D[] {
  return path.map((point) => ({
    x: point.x,
    y: point.y,
    z,
  }));
}

function createSegmentColliderIds(prefix: string, pointCount: number): readonly string[] {
  return Array.from({ length: Math.max(pointCount - 1, 0) }, (_, index) => {
    return `${prefix}:segment:${index}`;
  });
}

function offsetPath3D(
  path: readonly TablePoint3D[],
  offsets: Readonly<{ lateralOffset: number; verticalOffset: number }>,
): readonly TablePoint3D[] {
  return path.map((point, index) => {
    const tangent = resolvePlanarTangent(path, index);
    const normal = {
      x: -tangent.y,
      y: tangent.x,
    };
    return {
      x: point.x + normal.x * offsets.lateralOffset,
      y: point.y + normal.y * offsets.lateralOffset,
      z: point.z + offsets.verticalOffset,
    };
  });
}

function resolvePlanarTangent(
  path: readonly TablePoint3D[],
  index: number,
): Readonly<{ x: number; y: number }> {
  const previous = path[Math.max(index - 1, 0)];
  const next = path[Math.min(index + 1, path.length - 1)];
  const dx = next.x - previous.x;
  const dy = next.y - previous.y;
  const magnitude = Math.hypot(dx, dy);
  if (magnitude <= 1e-6) {
    return { x: 0, y: 1 };
  }
  return {
    x: dx / magnitude,
    y: dy / magnitude,
  };
}

function buildReceiverHullPoints(
  segment: readonly [TablePoint3D, TablePoint3D],
  ballRestZ: number,
  donorRadius: number,
): readonly TablePoint3D[] {
  const [start, end] = segment;
  const tangent = normalizePlanarVector(end.x - start.x, end.y - start.y);
  const normal = {
    x: -tangent.y,
    y: tangent.x,
  };
  const alongInset = Math.max(donorRadius * 1.2, ballRestZ * 0.65);
  const halfWidth = Math.max(ballRestZ * 1.8, donorRadius * 2.1);
  const topZ = Math.min(start.z, end.z) - ballRestZ * 0.8;
  const bottomZ = topZ - Math.max(ballRestZ * 0.9, donorRadius * 1.4);

  const insetStart = {
    x: start.x + tangent.x * alongInset,
    y: start.y + tangent.y * alongInset,
  };
  const insetEnd = {
    x: end.x - tangent.x * alongInset,
    y: end.y - tangent.y * alongInset,
  };

  return [
    point3D(insetStart, normal, halfWidth, bottomZ, 1),
    point3D(insetStart, normal, halfWidth, bottomZ, -1),
    point3D(insetEnd, normal, halfWidth, bottomZ, -1),
    point3D(insetEnd, normal, halfWidth, bottomZ, 1),
    point3D(insetStart, normal, halfWidth, topZ, 1),
    point3D(insetStart, normal, halfWidth, topZ, -1),
    point3D(insetEnd, normal, halfWidth, topZ, -1),
    point3D(insetEnd, normal, halfWidth, topZ, 1),
  ];
}

function point3D(
  center: Readonly<{ x: number; y: number }>,
  normal: Readonly<{ x: number; y: number }>,
  halfWidth: number,
  z: number,
  direction: 1 | -1,
): TablePoint3D {
  return {
    x: center.x + normal.x * halfWidth * direction,
    y: center.y + normal.y * halfWidth * direction,
    z,
  };
}

function normalizePlanarVector(
  dx: number,
  dy: number,
): Readonly<{ x: number; y: number }> {
  const magnitude = Math.hypot(dx, dy);
  if (magnitude <= 1e-6) {
    return { x: 0, y: 1 };
  }
  return {
    x: dx / magnitude,
    y: dy / magnitude,
  };
}
