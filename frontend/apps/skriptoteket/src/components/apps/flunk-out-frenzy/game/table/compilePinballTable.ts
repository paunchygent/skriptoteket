/**
 * Compiler from authored pinball table specs to explicit runtime plans.
 *
 * The compiled table keeps semantic device metadata alongside physics collider
 * plans and render nodes so runtime, rules, and presentation stay synchronized.
 */

import { degreesToRadians, v } from "./pinballTableMath";
import type {
  CompiledPinballTable,
  PinballTableSpec,
  TableBodyPlan,
  TableColliderPlan,
  TableRenderNodePlan,
  TableSurfaceSpec,
  TriggerSemanticKind,
} from "./pinballTablePlanTypes";
import { DEFAULT_TABLE_SURFACES } from "./pinballTablePlanTypes";

// Specialized compilers
import { assertValidTableSpec } from "./compiler/assertValidTableSpec";
import {
  compileRails,
  compileWalls,
  compilePosts,
  compileSolids,
} from "./compiler/compileWalls";
import { compileBumpers, compileSlings } from "./compiler/compileBumpers";
import {
  compileRollovers,
  compileTripwires,
  compileGates,
  compileDrain,
} from "./compiler/compileSensors";
import {
  compileStandupTargets,
  compilePopupTargets,
  compileCaptureDevices,
  compileSaveDevices,
  compileRenderSurfaces,
} from "./compiler/compileCaptureDevices";
import type { CompilerContext, CompilerOutput } from "./compiler/compilerTypes";

export function compilePinballTable(
  spec: PinballTableSpec,
): CompiledPinballTable {
  assertValidTableSpec(spec);

  const surfaces = mergeSurfaceIndex(spec.surfaces);
  const staticBodyId = `${spec.id}:static`;
  const flipperBodyIds = {
    left: `${spec.id}:flipper-left`,
    right: `${spec.id}:flipper-right`,
  } as const;

  const bodies: TableBodyPlan[] = [
    {
      id: staticBodyId,
      type: "fixed",
      translation: v(0, 0),
      rotationRad: 0,
    },
    {
      id: flipperBodyIds.left,
      type: "kinematic-position",
      translation: spec.flippers.left.pivot,
      rotationRad: degreesToRadians(spec.flippers.left.restAngleDeg),
    },
    {
      id: flipperBodyIds.right,
      type: "kinematic-position",
      translation: spec.flippers.right.pivot,
      rotationRad: degreesToRadians(spec.flippers.right.restAngleDeg),
    },
  ];

  const context: CompilerContext = {
    staticBodyId,
    ballRestZ: spec.launcher.threeD.ballRestZ,
  };

  const colliders: TableColliderPlan[] = [];
  const renderNodes: TableRenderNodePlan[] = [];

  const addOutput = (output: CompilerOutput) => {
    colliders.push(...output.colliders);
    renderNodes.push(...output.renderNodes);
    if (output.bodies) {
      bodies.push(...output.bodies);
    }
  };

  // Compile all elements
  addOutput(compileRails(spec.rails, context));
  addOutput(compileWalls(spec.walls, context));
  addOutput(compilePosts(spec.posts, context));
  addOutput(compileSolids(spec.solids, context));
  addOutput(compileBumpers(spec.bumpers, context));
  addOutput(compileSlings(spec.slings, context));
  addOutput(compileRollovers(spec.rollovers, context));
  addOutput(compileTripwires(spec.tripwires, context));
  addOutput(compileGates(spec.gates, context));
  addOutput(compileStandupTargets(spec.standupTargets, context));
  addOutput(compilePopupTargets(spec.popupTargets, context));
  addOutput(compileCaptureDevices(spec.captureDevices, context));
  addOutput(compileSaveDevices(spec.saveDevices, context));
  addOutput(compileDrain(spec.drain, context));
  addOutput(compileRenderSurfaces(spec.renderSurfaces));

  // Add flipper colliders
  colliders.push(
    compileFlipperCollider(spec.flippers.left, flipperBodyIds.left),
    compileFlipperCollider(spec.flippers.right, flipperBodyIds.right),
  );

  const result: CompiledPinballTable = {
    id: spec.id,
    name: spec.name,
    version: spec.version,
    board: spec.board,
    ballsPerGame: spec.ballsPerGame,
    gravity: spec.gravity,
    ball: spec.ball,
    launcher: spec.launcher,
    flippers: spec.flippers,
    bumpers: spec.bumpers,
    slings: spec.slings,
    rollovers: spec.rollovers,
    tripwires: spec.tripwires,
    gates: spec.gates,
    standupTargets: spec.standupTargets,
    popupTargets: spec.popupTargets,
    captureDevices: spec.captureDevices,
    saveDevices: spec.saveDevices,
    drain: spec.drain,
    surfaces,
    physics: {
      bodies,
      colliders,
      spawns: spec.spawns,
    },
    render: {
      nodes: renderNodes,
    },
    refs: {
      staticBodyId,
      flipperBodyIds,
    },
  };

  assertCompleteTable(result);
  return result;
}

function compileFlipperCollider(
  flipper: PinballTableSpec["flippers"]["left"],
  bodyId: string,
): TableColliderPlan {
  const halfLength = flipper.length / 2;
  const xOffset = flipper.side === "left" ? halfLength : -halfLength;

  return {
    id: `${bodyId}:collider`,
    bodyId,
    translation: v(xOffset, 0),
    rotationRad: 0,
    shape: { kind: "cuboid", halfExtents: v(halfLength, flipper.thickness / 2) },
    sensor: false,
    surfaceId: "flipper",
  };
}

function mergeSurfaceIndex(
  userSurfaces: readonly TableSurfaceSpec[] | undefined,
): Readonly<Record<string, TableSurfaceSpec>> {
  const out: Record<string, TableSurfaceSpec> = { ...DEFAULT_TABLE_SURFACES };
  for (const surface of userSurfaces ?? []) {
    out[surface.id] = surface;
  }
  return out;
}

function assertCompleteTable(table: CompiledPinballTable): void {
  // Check for critical elements presence in compiled plan
  const criticalKinds: readonly TriggerSemanticKind[] = ["drain"];
  const presentKinds = new Set(
    table.physics.colliders
      .map((c) => c.semanticKind)
      .filter((k): k is TriggerSemanticKind => k !== undefined),
  );

  for (const kind of criticalKinds) {
    if (!presentKinds.has(kind)) {
      throw new Error(`Compiled table is missing critical element kind: ${kind}`);
    }
  }
}
