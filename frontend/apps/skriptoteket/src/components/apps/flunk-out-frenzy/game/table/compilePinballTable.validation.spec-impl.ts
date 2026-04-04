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
import type { TableLauncherCarrier3DDefinition } from "./tableDefinitionTypes";

function withLauncherCarriers(
  carriers: readonly TableLauncherCarrier3DDefinition[],
) {
  return {
    ...PROTOTYPE_ALPHA_TABLE_SPEC,
    launcher: {
      ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher,
      threeD: {
        ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD,
        carriers,
      },
    },
  };
}

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
      compilePinballTable(
        withLauncherCarriers(
          PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.carriers.map((carrier) => {
            if (carrier.tag !== "launcher/travel/endpoint-bridge") {
              return carrier;
            }
            const [first, ...rest] = carrier.path;
            return { ...carrier, path: [{ ...first, x: first.x + 1.1 }, ...rest] };
          }),
        ),
      );
    }).toThrowError(
      'Launcher 3D carrier seam "launcher/travel/overhead" -> "launcher/travel/endpoint-bridge"',
    );
  });

  it("rejects endpoint-bridge seams when the descent-entry anchor is perturbed by more than 1px", () => {
    expect(() => {
      compilePinballTable(
        withLauncherCarriers(
          PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.carriers.map((carrier) => {
            if (carrier.tag !== "launcher/travel/endpoint-bridge") {
              return carrier;
            }
            const path = [...carrier.path];
            const lastIndex = path.length - 1;
            const last = path[lastIndex];
            if (!last) {
              return carrier;
            }
            path[lastIndex] = { ...last, x: last.x + 1.1 };
            return { ...carrier, path };
          }),
        ),
      );
    }).toThrowError(
      'Launcher 3D carrier seam "launcher/travel/endpoint-bridge" -> "launcher/travel/descent"',
    );
  });

  it("rejects launcher graphs without exactly one terminal handoff seam", () => {
    expect(() => {
      compilePinballTable(
        withLauncherCarriers(
          PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.carriers.filter((carrier) => {
            return carrier.kind !== "handoff_seam";
          }),
        ),
      );
    }).toThrowError(
      'Launcher "launcher/main" must declare exactly one terminal handoff seam.',
    );
  });

  it("rejects terminal handoff seams missing handoff velocity", () => {
    expect(() => {
      compilePinballTable(
        withLauncherCarriers(
          PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.carriers.map((carrier) => {
            if (carrier.tag !== "launcher/seam/board-handoff") {
              return carrier;
            }
            return {
              ...carrier,
              handoffVelocity: { x: 0, y: 0 },
            };
          }),
        ),
      );
    }).toThrowError(
      'Launcher 3D handoff seam "launcher/seam/board-handoff" must declare a non-zero handoff velocity.',
    );
  });

  it("rejects duplicate donor-span ownership across worlds", () => {
    expect(() => {
      compilePinballTable(
        withLauncherCarriers([
          ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.carriers,
          {
            ...PROTOTYPE_ALPHA_TABLE_SPEC.launcher.threeD.carriers[0],
            tag: "launcher/wall95-board-shadow",
            ownerWorld: "board",
          } as unknown as TableLauncherCarrier3DDefinition,
        ]),
      );
    }).toThrowError(
      'Launcher 3D carrier donor span ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall95.json" must not be owned in multiple worlds.',
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
