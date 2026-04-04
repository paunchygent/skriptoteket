import { magnitude } from "../pinballTableMath";
import type { PinballTableSpec } from "../pinballTablePlanTypes";
import type {
  TableLauncherTravelRoute3DDefinition,
  TableRegionShapeDefinition,
  TableTriggerShapeDefinition,
} from "../tableDefinitionTypes";
import { resolveTriggerShapeDefinition } from "./compileSensors";

const LAUNCHER_ROUTE_SEAM_TOLERANCE = 1;

export function assertValidTableSpec(spec: PinballTableSpec): void {
  const seenIds = new Set<string>();
  const registerId = (id: string, kind: string) => {
    if (seenIds.has(id)) {
      throw new Error(`Duplicate ${kind} id "${id}".`);
    }
    seenIds.add(id);
  };

  registerId(spec.id, "table");
  for (const spawn of spec.spawns) registerId(spawn.id, "spawn");
  for (const rail of spec.rails) {
    registerId(rail.id, "rail");
    if (rail.path.length < 2) {
      throw new Error(`Rail "${rail.id}" must have at least two points.`);
    }
    if (rail.zPath && rail.zPath.length !== rail.path.length) {
      throw new Error(`Rail "${rail.id}" zPath length must match path length.`);
    }
    if ((rail.heightBottom === undefined) !== (rail.heightTop === undefined)) {
      throw new Error(
        `Rail "${rail.id}" must declare both heightBottom and heightTop when using elevation bounds.`,
      );
    }
    if (
      rail.heightBottom !== undefined &&
      rail.heightTop !== undefined &&
      rail.heightTop < rail.heightBottom
    ) {
      throw new Error(`Rail "${rail.id}" must not invert height bounds.`);
    }
  }
  for (const wall of spec.walls ?? []) {
    registerId(wall.id, "wall");
    if ((wall.heightBottom === undefined) !== (wall.heightTop === undefined)) {
      throw new Error(
        `Wall "${wall.id}" must declare both heightBottom and heightTop when using elevation bounds.`,
      );
    }
    if (
      wall.heightBottom !== undefined &&
      wall.heightTop !== undefined &&
      wall.heightTop < wall.heightBottom
    ) {
      throw new Error(`Wall "${wall.id}" must not invert height bounds.`);
    }
  }
  for (const post of spec.posts ?? []) registerId(post.id, "post");
  for (const solid of spec.solids ?? []) {
    registerId(solid.id, "solid");
    if (solid.points.length < 3) {
      throw new Error(`Solid "${solid.id}" must have at least three points.`);
    }
    if (
      (solid.heightBottom === undefined) !== (solid.heightTop === undefined)
    ) {
      throw new Error(
        `Solid "${solid.id}" must declare both heightBottom and heightTop when using elevation bounds.`,
      );
    }
    if (
      solid.heightBottom !== undefined &&
      solid.heightTop !== undefined &&
      solid.heightTop < solid.heightBottom
    ) {
      throw new Error(`Solid "${solid.id}" must not invert height bounds.`);
    }
  }
  for (const surface of spec.renderSurfaces ?? [])
    registerId(surface.id, "render surface");

  const seenSemanticTags = new Set<string>();
  const registerSemanticTag = (tag: string, kind: string) => {
    if (seenSemanticTags.has(tag)) {
      throw new Error(`Duplicate ${kind} tag "${tag}".`);
    }
    seenSemanticTags.add(tag);
  };

  for (const bumper of spec.bumpers) registerSemanticTag(bumper.tag, "bumper");
  for (const sling of spec.slings) registerSemanticTag(sling.tag, "sling");
  for (const rollover of spec.rollovers)
    registerSemanticTag(rollover.tag, "rollover");
  for (const tripwire of spec.tripwires)
    registerSemanticTag(tripwire.tag, "tripwire");
  for (const gate of spec.gates) registerSemanticTag(gate.tag, "gate");
  for (const target of spec.standupTargets)
    registerSemanticTag(target.tag, "standup target");
  for (const target of spec.popupTargets)
    registerSemanticTag(target.tag, "popup target");
  for (const capture of spec.captureDevices)
    registerSemanticTag(capture.tag, "capture device");
  for (const save of spec.saveDevices)
    registerSemanticTag(save.tag, "save device");
  registerSemanticTag(spec.drain.tag, "drain");

  if (spec.board.width <= 0 || spec.board.height <= 0) {
    throw new Error("Table board dimensions must be positive.");
  }

  if (spec.launcher.laneRegions.length === 0) {
    throw new Error(
      'Launcher "launcher/main" must declare at least one lane region.',
    );
  }

  if (spec.launcher.threeD.walls.length === 0) {
    throw new Error(
      'Launcher "launcher/main" must declare at least one 3D wall section.',
    );
  }

  if (spec.launcher.threeD.sensors.length === 0) {
    throw new Error(
      'Launcher "launcher/main" must declare at least one 3D launcher sensor.',
    );
  }

  if (spec.launcher.threeD.guideRails.length === 0) {
    throw new Error(
      'Launcher "launcher/main" must declare at least one 3D launcher guide rail.',
    );
  }

  for (const [index, region] of spec.launcher.laneRegions.entries()) {
    assertValidLauncherRegionDefinition(
      `${spec.launcher.tag}[${index}]`,
      region,
    );
  }

  for (const wall of spec.launcher.threeD.walls) {
    if (wall.points.length < 3) {
      throw new Error(
        `Launcher 3D wall "${wall.tag}" must have at least three points.`,
      );
    }
    if (wall.heightTop < wall.heightBottom) {
      throw new Error(
        `Launcher 3D wall "${wall.tag}" must not invert height bounds.`,
      );
    }
  }

  for (const rail of spec.launcher.threeD.guideRails) {
    if (rail.path.length < 2) {
      throw new Error(
        `Launcher 3D guide rail "${rail.tag}" must have at least two points.`,
      );
    }
    if (rail.radius <= 0) {
      throw new Error(
        `Launcher 3D guide rail "${rail.tag}" must have a positive radius.`,
      );
    }
    if (rail.heightTop < rail.heightBottom) {
      throw new Error(
        `Launcher 3D guide rail "${rail.tag}" must not invert height bounds.`,
      );
    }
  }

  for (const sensor of spec.launcher.threeD.sensors) {
    assertValidTriggerDefinition(sensor.tag, sensor.shape);
  }
  const feedSensors = spec.launcher.threeD.sensors.filter(
    (sensor) => sensor.semanticRole === "feed",
  );
  const exitSensors = spec.launcher.threeD.sensors.filter(
    (sensor) => sensor.semanticRole === "exit",
  );
  if (feedSensors.length !== 1) {
    throw new Error(
      'Launcher "launcher/main" must declare exactly one feed sensor.',
    );
  }
  if (exitSensors.length !== 1) {
    throw new Error(
      'Launcher "launcher/main" must declare exactly one exit sensor.',
    );
  }

  if (
    spec.launcher.threeD.plunger.width <= 0 ||
    spec.launcher.threeD.plunger.depth <= 0 ||
    spec.launcher.threeD.plunger.height <= 0 ||
    spec.launcher.threeD.plunger.stroke <= 0
  ) {
    throw new Error(
      "Launcher 3D plunger must declare positive width/depth/height/stroke.",
    );
  }
  assertValidLauncherTravelRoutes(spec.launcher.threeD.travelRoutes ?? []);

  for (const tripwire of spec.tripwires) {
    assertValidTriggerDefinition(
      tripwire.tag,
      resolveTriggerShapeDefinition(tripwire),
    );
  }

  for (const gate of spec.gates) {
    assertValidTriggerDefinition(
      gate.tag,
      resolveTriggerShapeDefinition(gate),
    );
  }

  for (const capture of spec.captureDevices) {
    if (capture.width <= 0 || capture.height <= 0) {
      throw new Error(`Capture device "${capture.tag}" must have positive bounds.`);
    }
    if (capture.holdMs < 0) {
      throw new Error(`Capture device "${capture.tag}" holdMs must be >= 0.`);
    }
    if (capture.cooldownMs < 0) {
      throw new Error(`Capture device "${capture.tag}" cooldownMs must be >= 0.`);
    }
    if (magnitude(capture.ejectImpulse) <= 0) {
      throw new Error(
        `Capture device "${capture.tag}" must have a non-zero eject impulse.`,
      );
    }
  }

  for (const save of spec.saveDevices) {
    if (save.width <= 0 || save.height <= 0) {
      throw new Error(`Save device "${save.tag}" must have positive bounds.`);
    }
    if (save.cooldownMs < 0) {
      throw new Error(`Save device "${save.tag}" cooldownMs must be >= 0.`);
    }
    if (magnitude(save.saveImpulse) <= 0) {
      throw new Error(
        `Save device "${save.tag}" must have a non-zero save impulse.`,
      );
    }
  }
}

function assertValidTriggerDefinition(
  tag: string,
  shape: TableTriggerShapeDefinition,
): void {
  switch (shape.kind) {
    case "rect":
      if (shape.width <= 0 || shape.height <= 0) {
        throw new Error(`Trigger "${tag}" rect shape must have positive bounds.`);
      }
      return;
    case "circle":
      if (shape.radius <= 0) {
        throw new Error(`Trigger "${tag}" circle shape must have a positive radius.`);
      }
      return;
    case "polygon":
      if (shape.points.length < 3) {
        throw new Error(
          `Trigger "${tag}" polygon shape must have at least three points.`,
        );
      }
      return;
    case "capsule":
      if (shape.length <= 0 || shape.radius <= 0) {
        throw new Error(
          `Trigger "${tag}" capsule shape must have positive length and radius.`,
        );
      }
      return;
    case "donor-wire-rollover":
      if (shape.wireLength <= 0 || shape.wireRadius <= 0) {
        throw new Error(
          `Trigger "${tag}" donor wire-rollover shape must have positive wire length and radius.`,
        );
      }
      return;
  }
}

function assertValidLauncherRegionDefinition(
  label: string,
  shape: TableRegionShapeDefinition,
): void {
  switch (shape.kind) {
    case "rect":
      if (shape.width <= 0 || shape.height <= 0) {
        throw new Error(
          `Launcher region "${label}" rect shape must have positive bounds.`,
        );
      }
      return;
    case "circle":
      if (shape.radius <= 0) {
        throw new Error(
          `Launcher region "${label}" circle shape must have a positive radius.`,
        );
      }
      return;
    case "polygon":
      if (shape.points.length < 3) {
        throw new Error(
          `Launcher region "${label}" polygon shape must have at least three points.`,
        );
      }
      return;
    case "capsule":
      if (shape.length <= 0 || shape.radius <= 0) {
        throw new Error(
          `Launcher region "${label}" capsule shape must have positive length and radius.`,
        );
      }
      return;
    case "donor-corridor":
      if (shape.leftBoundary.length < 2 || shape.rightBoundary.length < 2) {
        throw new Error(
          `Launcher region "${label}" donor corridor must have at least two points per boundary.`,
        );
      }
      return;
  }
}

function assertValidLauncherTravelRoutes(
  routes: readonly TableLauncherTravelRoute3DDefinition[],
): void {
  const routeByTag = new Map<string, TableLauncherTravelRoute3DDefinition>();

  for (const route of routes) {
    if (routeByTag.has(route.tag)) {
      throw new Error(
        `Launcher 3D travel route tag "${route.tag}" must be unique.`,
      );
    }
    routeByTag.set(route.tag, route);
    if (route.path.length < 2) {
      throw new Error(
        `Launcher 3D travel route "${route.tag}" must have at least two points.`,
      );
    }
    if (route.minChargeRatio < 0 || route.minChargeRatio > 1) {
      throw new Error(
        `Launcher 3D travel route "${route.tag}" minChargeRatio must be in [0, 1].`,
      );
    }
    if (!route.nextRouteTag && !route.handoffVelocity) {
      throw new Error(
        `Launcher 3D travel route "${route.tag}" must declare a terminal handoff velocity.`,
      );
    }
    const hasMidChainHandoff =
      route.nextRouteTag &&
      (route as { handoffVelocity?: unknown }).handoffVelocity !== undefined;
    if (hasMidChainHandoff) {
      throw new Error(
        `Launcher 3D travel route "${route.tag}" must not declare handoff velocity when chaining.`,
      );
    }
  }

  for (const route of routes) {
    if (!route.nextRouteTag) {
      continue;
    }
    const nextRoute = routeByTag.get(route.nextRouteTag);
    if (!nextRoute) {
      throw new Error(
        `Launcher 3D travel route "${route.tag}" references unknown nextRouteTag "${route.nextRouteTag}".`,
      );
    }
    const nextEntryMode = nextRoute.entryMode ?? "release";
    if (nextEntryMode !== "chain") {
      throw new Error(
        `Launcher 3D travel route "${route.nextRouteTag}" must declare entryMode "chain".`,
      );
    }

    const routeEnd = route.path[route.path.length - 1];
    const nextStart = nextRoute.path[0];
    const xyDelta = Math.hypot(
      routeEnd.x - nextStart.x,
      routeEnd.y - nextStart.y,
    );
    const zDelta = Math.abs(routeEnd.z - nextStart.z);
    if (
      xyDelta > LAUNCHER_ROUTE_SEAM_TOLERANCE ||
      zDelta > LAUNCHER_ROUTE_SEAM_TOLERANCE
    ) {
      throw new Error(
        `Launcher 3D travel route seam "${route.tag}" -> "${nextRoute.tag}" must be continuous ` +
          `(xy<=${LAUNCHER_ROUTE_SEAM_TOLERANCE}, z<=${LAUNCHER_ROUTE_SEAM_TOLERANCE}).`,
      );
    }
  }

  const visiting = new Set<string>();
  const visited = new Set<string>();
  const visit = (tag: string) => {
    if (visited.has(tag)) {
      return;
    }
    if (visiting.has(tag)) {
      throw new Error(
        `Launcher 3D travel routes must not form cycles (detected at "${tag}").`,
      );
    }

    visiting.add(tag);
    const route = routeByTag.get(tag);
    if (route?.nextRouteTag) {
      visit(route.nextRouteTag);
    }
    visiting.delete(tag);
    visited.add(tag);
  };

  for (const route of routes) {
    visit(route.tag);
  }
}
