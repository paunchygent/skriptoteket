/**
 * Donor-geometry compilation regressions for the Flunk-Out Frenzy table compiler.
 *
 * These tests keep the authored donor paths, solids, and launcher carriers
 * intact after compilation without forcing one oversized monolithic spec file.
 */

import { describe, expect, it } from "vitest";

import {
  compilePinballTable,
  degreesToRadians,
  expectCapsuleShape,
  expectRectShape,
  expectWireRolloverShape,
  PROTOTYPE_ALPHA_TABLE_SPEC,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES,
  scaleDonorPoint,
  VPW_APRON_1_POLYGON,
  VPW_APRON_2_POLYGON,
  VPW_GATE_SPECS,
  VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC,
  VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_3D_PATH,
  VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_DONOR_SOURCES,
  VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_ENTRY_ANCHOR_3D,
  VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_3D_PATH,
  VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_DONOR_SOURCES,
  VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH,
  VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_DONOR_SOURCES,
  VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_EXIT_ANCHOR_3D,
  VPW_LEFT_UPPER_INNER_METAL_PATH,
  VPW_METAL_RAIL_3D_SPECS,
  VPW_OUTER_BOUNDARY_MAIN_PATH,
  VPW_OUTER_BOUNDARY_RENDER_PATH,
  VPW_OUTER_BOUNDARY_RIGHT_DESCENT_PATH,
  VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH,
  VPW_PLUNGER_ROSE_3D_SPEC,
  VPW_RIGHT_RETURN_TRIGGER_SPEC,
  VPW_RIGHT_UPPER_INNER_METAL_PATH,
  VPW_SHOOTER_DIVIDER_POLYGON,
  VPW_SHOOTER_HANDOFF_LOWER_POLYGON,
  VPW_SHOOTER_HANDOFF_UPPER_POLYGON,
  VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS,
  VPW_SHOOTER_OUTER_INNER_EDGE,
  VPW_SHOOTER_OUTER_POLYGON,
  VPW_SHOOTER_PLUNGER_TRIGGER_SPEC,
} from "./compilePinballTable.spec-support";

describe("compilePinballTable donor geometry", () => {
  it("preserves the donor angle for the right-return tripwire sensor", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);
    const rightReturnShape = expectCapsuleShape(VPW_RIGHT_RETURN_TRIGGER_SPEC.shape);
    const sensor = compiled.physics.colliders.find((collider) => {
      return collider.id === "tripwire/right-orbit-return:sensor";
    });

    expect(sensor).toMatchObject({
      id: "tripwire/right-orbit-return:sensor",
      translation: rightReturnShape.center,
      rotationRad: degreesToRadians(VPW_GATE_SPECS.rightReturn.rotationDeg),
      shape: {
        kind: "thick-segment",
        halfLength: rightReturnShape.length / 2,
        radius: rightReturnShape.radius,
      },
      sensor: true,
      semanticKind: "tripwire",
      tag: "tripwire/right-orbit-return",
      trigger: {
        shape: VPW_RIGHT_RETURN_TRIGGER_SPEC.shape,
        phase: VPW_RIGHT_RETURN_TRIGGER_SPEC.triggerPhase,
      },
    });
  });

  it("maps the launch-exit gate to the donor sw16 wire-rollover semantics", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);
    const launchExitShape = expectWireRolloverShape(VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.shape);
    const sensor = compiled.physics.colliders.find((collider) => {
      return collider.id === "gate/launch-lane-exit:sensor";
    });

    expect(sensor).toMatchObject({
      id: "gate/launch-lane-exit:sensor",
      translation: launchExitShape.center,
      rotationRad: 0,
      shape: {
        kind: "thick-segment",
        halfLength: launchExitShape.wireLength / 2,
        radius: launchExitShape.wireRadius,
      },
      sensor: true,
      semanticKind: "gate",
      tag: "gate/launch-lane-exit",
      trigger: {
        shape: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.shape,
        phase: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.triggerPhase,
      },
    });
  });

  it("keeps swplunger as a separate donor anchor from the sw16 launch-exit trigger", () => {
    const plungerShape = expectRectShape(VPW_SHOOTER_PLUNGER_TRIGGER_SPEC.shape);
    const exitShape = expectWireRolloverShape(VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.shape);

    expect(VPW_SHOOTER_PLUNGER_TRIGGER_SPEC.donorSourceIds).toEqual([
      ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.swplunger.json",
    ]);
    expect(VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.donorSourceIds).toEqual([
      ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw16.json",
    ]);
    expect(PROTOTYPE_ALPHA_TABLE_SPEC.ball.spawn.x).toBe(plungerShape.center.x);
    expect(PROTOTYPE_ALPHA_TABLE_SPEC.ball.spawn.y).toBeGreaterThan(exitShape.center.y);
    expect(PROTOTYPE_ALPHA_TABLE_SPEC.launcher.laneRegions).toContainEqual({
      kind: "rect",
      center: plungerShape.center,
      width: plungerShape.width,
      height: plungerShape.height,
      angleDeg: plungerShape.angleDeg,
    });
    expect(PROTOTYPE_ALPHA_TABLE_SPEC.launcher.laneRegions).toContainEqual({
      kind: "donor-corridor",
      leftBoundary: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.wall010,
      rightBoundary: VPW_SHOOTER_OUTER_INNER_EDGE,
    });
    expect(PROTOTYPE_ALPHA_TABLE_SPEC.launcher.laneRegions).toContainEqual({
      kind: "donor-corridor",
      leftBoundary: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.apronToPlunger,
      rightBoundary: VPW_SHOOTER_OUTER_INNER_EDGE,
    });
  });

  it("carries the missing donor shooter corridor walls into the compiled solids plan", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);
    const upperHandoff = compiled.physics.colliders.find((collider) => {
      return collider.id === "shooter-handoff-upper:body";
    });
    const lowerHandoff = compiled.physics.colliders.find((collider) => {
      return collider.id === "shooter-handoff-lower:body";
    });

    expect(PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterHandoffUpper).toBe(
      ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall010.json",
    );
    expect(PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterHandoffLower).toBe(
      ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall011.json",
    );
    expect(upperHandoff).toMatchObject({
      id: "shooter-handoff-upper:body",
      shape: { kind: "convex-polygon", vertices: VPW_SHOOTER_HANDOFF_UPPER_POLYGON },
      sensor: false,
    });
    expect(lowerHandoff).toMatchObject({
      id: "shooter-handoff-lower:body",
      shape: { kind: "convex-polygon", vertices: VPW_SHOOTER_HANDOFF_LOWER_POLYGON },
      sensor: false,
    });
  });

  it("splits the Wall263 shooter-corridor slice into a thin physical rail", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);
    const mainBoundarySegments = compiled.physics.colliders.filter((collider) => {
      return collider.id.startsWith("outer-boundary-main:segment:");
    });
    const shooterCorridorSegments = compiled.physics.colliders.filter((collider) => {
      return collider.id.startsWith("outer-boundary-shooter-corridor:segment:");
    });

    expect(PROTOTYPE_ALPHA_TABLE_SPEC.rails).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: "outer-boundary-main", path: VPW_OUTER_BOUNDARY_MAIN_PATH, radius: 8 }),
        expect.objectContaining({
          id: "outer-boundary-shooter-corridor",
          path: VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH,
          radius: 2,
        }),
      ]),
    );
    expect(mainBoundarySegments.length).toBe(VPW_OUTER_BOUNDARY_MAIN_PATH.length - 1);
    expect(shooterCorridorSegments.length).toBe(VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH.length - 1);
    expect(
      compiled.physics.colliders.some((collider) => collider.id.startsWith("outer-boundary-wall263-render:")),
    ).toBe(false);
    expect(compiled.render.nodes.find((node) => node.id === "outer-boundary-main:render")).toBeUndefined();
    expect(
      compiled.render.nodes.find((node) => node.id === "outer-boundary-shooter-corridor:render"),
    ).toBeUndefined();
    expect(compiled.render.nodes).toContainEqual({
      kind: "polyline",
      id: "outer-boundary-wall263-render",
      layer: "walls",
      points: VPW_OUTER_BOUNDARY_RENDER_PATH,
      thickness: 16,
    });
    expect(shooterCorridorSegments).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          shape: expect.objectContaining({ kind: "thick-segment", radius: 2 }),
          sensor: false,
        }),
      ]),
    );
    expect(mainBoundarySegments).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          shape: expect.objectContaining({ kind: "thick-segment", radius: 8 }),
          sensor: false,
        }),
      ]),
    );
  });

  it("pins the retained Wall263 shoulder donor points and keeps removed tail ownership explicit", () => {
    expect(VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH).toEqual([
      scaleDonorPoint(951.4667, 956.0513),
      scaleDonorPoint(935.7408, 1034.7188),
      scaleDonorPoint(939.0524, 1035.5),
      scaleDonorPoint(947.7321, 1035.5),
      scaleDonorPoint(953.6216, 1035.5),
      scaleDonorPoint(995.4193, 1255.0),
      scaleDonorPoint(970.4193, 1265.0),
    ]);

    expect(PROTOTYPE_ALPHA_TABLE_SPEC.solids.map((solid) => solid.id)).toEqual(
      expect.arrayContaining(["shooter-handoff-upper", "shooter-handoff-lower", "apron-1", "apron-2"]),
    );
  });

  it("keeps the lower shooter corridor on donor walls including Wall34 as a physical carrier", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);

    expect(compiled.physics.colliders).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "shooter-outer-wall:body",
          shape: { kind: "convex-polygon", vertices: VPW_SHOOTER_OUTER_POLYGON },
          sensor: false,
        }),
        expect.objectContaining({
          id: "shooter-handoff-upper:body",
          shape: { kind: "convex-polygon", vertices: VPW_SHOOTER_HANDOFF_UPPER_POLYGON },
          sensor: false,
        }),
        expect.objectContaining({
          id: "shooter-handoff-lower:body",
          shape: { kind: "convex-polygon", vertices: VPW_SHOOTER_HANDOFF_LOWER_POLYGON },
          sensor: false,
        }),
        expect.objectContaining({
          id: "shooter-divider-wall34:body",
          shape: { kind: "convex-polygon", vertices: VPW_SHOOTER_DIVIDER_POLYGON },
          sensor: false,
        }),
        expect.objectContaining({
          id: "apron-1:body",
          shape: { kind: "convex-polygon", vertices: VPW_APRON_1_POLYGON },
          sensor: false,
        }),
        expect.objectContaining({
          id: "apron-2:body",
          shape: { kind: "convex-polygon", vertices: VPW_APRON_2_POLYGON },
          sensor: false,
        }),
      ]),
    );
    expect(compiled.render.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "shooter-divider-edge-render",
          kind: "polyline",
          points: VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS.divider,
        }),
      ]),
    );
  });

  it("keeps the donor Wall263 upper-right descent as a thin physical rail", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);
    const rightDescentSegments = compiled.physics.colliders.filter((collider) => {
      return collider.id.startsWith("outer-boundary-right-descent:segment:");
    });

    expect(PROTOTYPE_ALPHA_TABLE_SPEC.rails).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "outer-boundary-right-descent",
          path: VPW_OUTER_BOUNDARY_RIGHT_DESCENT_PATH,
          radius: 2,
        }),
      ]),
    );
    expect(rightDescentSegments.length).toBe(VPW_OUTER_BOUNDARY_RIGHT_DESCENT_PATH.length - 1);
    expect(rightDescentSegments).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          shape: expect.objectContaining({ kind: "thick-segment", radius: 2 }),
          sensor: false,
        }),
      ]),
    );
  });

  it("keeps elevated donor receive-mouth walls visible but out of playfield colliders", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);

    expect(
      compiled.physics.colliders.find((collider) => collider.id === "right-receive-mouth-outer:body"),
    ).toBeUndefined();
    expect(
      compiled.physics.colliders.find((collider) => collider.id === "right-receive-mouth-inner:body"),
    ).toBeUndefined();
    expect(compiled.render.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: "right-receive-mouth-outer:render", kind: "polygon" }),
        expect.objectContaining({ id: "right-receive-mouth-inner:render", kind: "polygon" }),
      ]),
    );
  });

  it("carries the donor 3D launcher-chain provenance in the compiled table", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);

    expect(compiled.launcher.threeD.plunger).toEqual(VPW_PLUNGER_ROSE_3D_SPEC);
    expect(compiled.launcher.threeD.walls).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          tag: "launcher/wall34",
          donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterLaneDivider,
        }),
        expect.objectContaining({
          tag: "launcher/wall95",
          donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterOuterWall,
        }),
      ]),
    );
    expect(compiled.launcher.threeD.guideRails).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          tag: "launcher/wall263-shoulder",
          donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.outerBoundary,
        }),
        expect.objectContaining({
          tag: "launcher/wall264",
          donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.rightUpperGuide,
        }),
      ]),
    );
    expect(compiled.launcher.threeD.sensors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          tag: "launcher/feed",
          donorSourceIds: VPW_SHOOTER_PLUNGER_TRIGGER_SPEC.donorSourceIds,
        }),
        expect.objectContaining({
          tag: "gate/launch-lane-exit",
          donorSourceIds: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.donorSourceIds,
        }),
      ]),
    );
    expect(compiled.launcher.threeD.travelRoutes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          tag: "launcher/travel/overhead",
          donorSourceIds: VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_DONOR_SOURCES,
          path: VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH,
          nextRouteTag: "launcher/travel/endpoint-bridge",
        }),
        expect.objectContaining({
          tag: "launcher/travel/endpoint-bridge",
          donorSourceIds: VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_DONOR_SOURCES,
          path: VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_3D_PATH,
          entryMode: "chain",
          nextRouteTag: "launcher/travel/descent",
        }),
        expect.objectContaining({
          tag: "launcher/travel/descent",
          donorSourceIds: VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_DONOR_SOURCES,
          path: VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_3D_PATH,
          entryMode: "chain",
        }),
      ]),
    );
    const endpointBridgeRoute = compiled.launcher.threeD.travelRoutes?.find((route) => {
      return route.tag === "launcher/travel/endpoint-bridge";
    });
    expect(endpointBridgeRoute?.path).toHaveLength(2);
    expect(endpointBridgeRoute?.path[0]).toEqual(VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_EXIT_ANCHOR_3D);
    expect(endpointBridgeRoute?.path[1]).toEqual(VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_ENTRY_ANCHOR_3D);
  });

  it("maps upper inner metal guides from donor Wall017/Wall002 as explicit carriers", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);
    const leftInnerSegments = compiled.physics.colliders.filter((collider) => {
      return collider.id.startsWith("upper-left-inner-metal-wall017:segment:");
    });
    const rightInnerSegments = compiled.physics.colliders.filter((collider) => {
      return collider.id.startsWith("upper-right-inner-metal-wall002:segment:");
    });

    expect(PROTOTYPE_ALPHA_TABLE_SPEC.rails).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "upper-left-inner-metal-wall017",
          donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.leftUpperInnerMetal,
          path: VPW_LEFT_UPPER_INNER_METAL_PATH,
        }),
        expect.objectContaining({
          id: "upper-right-inner-metal-wall002",
          donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.rightUpperInnerMetal,
          path: VPW_RIGHT_UPPER_INNER_METAL_PATH,
        }),
      ]),
    );
    expect(leftInnerSegments.length).toBe(VPW_LEFT_UPPER_INNER_METAL_PATH.length - 1);
    expect(rightInnerSegments.length).toBe(VPW_RIGHT_UPPER_INNER_METAL_PATH.length - 1);
  });

  it("keeps overhead donor wire rails as provenance-explicit elevated render carriers", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);
    const overheadRailIds = [
      "overhead-wire-shooter-vertical-ramps3",
      "overhead-wire-shooter-mouth-ramps001",
      "overhead-wire-shooter-top-right-ramps002",
      "overhead-wire-shooter-top-arch-ramps4",
    ];

    for (const railId of overheadRailIds) {
      const rail = PROTOTYPE_ALPHA_TABLE_SPEC.rails.find((item) => item.id === railId);
      expect(rail).toBeDefined();
      if (!rail || !("physics" in rail) || !("zPath" in rail)) {
        throw new Error(`Expected overhead donor rail "${railId}" to carry physics/zPath fields.`);
      }
      expect(rail.renderLayer).toBe("overhead-guides");
      expect(rail.physics).toBe(false);
      expect(rail.zPath?.length).toBe(rail.path.length);
      expect(
        compiled.physics.colliders.find((collider) => collider.id.startsWith(`${railId}:segment:`)),
      ).toBeUndefined();
      expect(compiled.render.nodes).toContainEqual(
        expect.objectContaining({
          id: `${railId}:render`,
          kind: "polyline",
          layer: "overhead-guides",
        }),
      );
    }

    expect(PROTOTYPE_ALPHA_TABLE_SPEC.rails).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "overhead-wire-shooter-vertical-ramps3",
          donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterVertical.donorSourceId,
          zPath: VPW_METAL_RAIL_3D_SPECS.shooterVertical.path.map((point) => point.z),
        }),
        expect.objectContaining({
          id: "overhead-wire-shooter-top-arch-ramps4",
          donorSourceId: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.donorSourceId,
          zPath: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.path.map((point) => point.z),
        }),
      ]),
    );
  });
});
