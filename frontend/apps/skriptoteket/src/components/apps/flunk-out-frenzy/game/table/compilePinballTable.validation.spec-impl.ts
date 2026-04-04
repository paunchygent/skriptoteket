/**
 * Validation and device-semantic regressions for the Flunk-Out Frenzy table compiler.
 *
 * These assertions keep compiler guardrails explicit after the donor-geometry
 * suite was split into smaller modules.
 */

import { describe, expect, it } from "vitest";

import {
  compilePinballTable,
  PROTOTYPE_ALPHA_TABLE_SPEC,
} from "./compilePinballTable.spec-support";

describe("compilePinballTable validation", () => {
  it("compiles capture/save device semantics into the collider plan", () => {
    const compiled = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);

    const captureSensor = compiled.physics.colliders.find((collider) => {
      return collider.id === "capture/scoop-study:sensor";
    });
    const saveSensor = compiled.physics.colliders.find((collider) => {
      return collider.id === "save/right-kickback:sensor";
    });

    expect(captureSensor).toMatchObject({
      id: "capture/scoop-study:sensor",
      semanticKind: "capture",
      tag: "capture/scoop-study",
      captureDeviceKind: "hole",
      holdMs: 560,
      cooldownMs: 900,
    });
    expect(saveSensor).toMatchObject({
      id: "save/right-kickback:sensor",
      semanticKind: "save",
      tag: "save/right-kickback",
      saveDeviceKind: "kickback",
      cooldownMs: 650,
    });
  });

  it("rejects launcher travel-route seams when chained endpoints are not donor-continuous", () => {
    expect(() => {
      compilePinballTable({
        ...PROTOTYPE_ALPHA_TABLE_SPEC,
        launcher: {
          ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher,
          threeD: {
            ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD,
            travelRoutes: (PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.travelRoutes ?? []).map((route) => {
              if (route.tag !== "launcher/travel/endpoint-bridge") {
                return route;
              }
              const [first, ...rest] = route.path;
              return { ...route, path: [{ ...first, x: first.x + 1.1 }, ...rest] };
            }),
          },
        },
      });
    }).toThrowError(
      'Launcher 3D travel route seam "launcher/travel/overhead" -> "launcher/travel/endpoint-bridge"',
    );
  });

  it("rejects endpoint-bridge seams when the descent-entry anchor is perturbed by more than 1px", () => {
    expect(() => {
      compilePinballTable({
        ...PROTOTYPE_ALPHA_TABLE_SPEC,
        launcher: {
          ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher,
          threeD: {
            ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD,
            travelRoutes: (PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.travelRoutes ?? []).map((route) => {
              if (route.tag !== "launcher/travel/endpoint-bridge") {
                return route;
              }
              const path = [...route.path];
              const lastIndex = path.length - 1;
              const last = path[lastIndex];
              if (!last) {
                return route;
              }
              path[lastIndex] = { ...last, x: last.x + 1.1 };
              return { ...route, path };
            }),
          },
        },
      });
    }).toThrowError(
      'Launcher 3D travel route seam "launcher/travel/endpoint-bridge" -> "launcher/travel/descent"',
    );
  });

  it("rejects chained launcher routes that declare terminal handoff velocity", () => {
    expect(() => {
      compilePinballTable({
        ...PROTOTYPE_ALPHA_TABLE_SPEC,
        launcher: {
          ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher,
          threeD: {
            ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD,
            travelRoutes: (PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.travelRoutes ?? []).map((route) => {
              if (route.tag !== "launcher/travel/endpoint-bridge") {
                return route;
              }
              return { ...route, handoffVelocity: { x: -140, y: 360 } } as unknown as typeof route;
            }),
          },
        },
      });
    }).toThrowError(
      'Launcher 3D travel route "launcher/travel/endpoint-bridge" must not declare handoff velocity when chaining.',
    );
  });

  it("rejects terminal launcher routes missing handoff velocity", () => {
    expect(() => {
      compilePinballTable({
        ...PROTOTYPE_ALPHA_TABLE_SPEC,
        launcher: {
          ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher,
          threeD: {
            ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD,
            travelRoutes: (PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.travelRoutes ?? []).map((route) => {
              if (route.tag !== "launcher/travel/descent") {
                return route;
              }
              return { ...route, handoffVelocity: undefined } as unknown as typeof route;
            }),
          },
        },
      });
    }).toThrowError(
      'Launcher 3D travel route "launcher/travel/descent" must declare a terminal handoff velocity.',
    );
  });

  it("rejects launcher definitions without exactly one feed and one exit sensor", () => {
    expect(() => {
      compilePinballTable({
        ...PROTOTYPE_ALPHA_TABLE_SPEC,
        launcher: {
          ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher,
          threeD: {
            ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD,
            sensors: [
              ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.sensors,
              {
                ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.sensors[0],
                tag: "launcher/feed-duplicate",
              },
            ],
          },
        },
      });
    }).toThrowError('Launcher "launcher/main" must declare exactly one feed sensor.');
  });

  it("rejects capture devices with zero eject impulse", () => {
    expect(() => {
      compilePinballTable({
        ...PROTOTYPE_ALPHA_TABLE_SPEC,
        captureDevices: PROTOTYPE_ALPHA_TABLE_SPEC.captureDevices.map((device) => {
          if (device.tag === "capture/scoop-study") {
            return { ...device, ejectImpulse: { x: 0, y: 0 } };
          }
          return device;
        }),
      });
    }).toThrowError('Capture device "capture/scoop-study" must have a non-zero eject impulse.');
  });
});
