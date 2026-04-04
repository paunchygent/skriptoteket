// @vitest-environment node

/**
 * Launcher proof-matrix regressions for Flunk-Out Frenzy physics world.
 *
 * These tests preserve the PR-0206 and PR-0209 artifact contracts separately
 * from the interactive launcher behavior assertions.
 */

import { beforeAll, describe, expect, it } from "vitest";

import type { PrototypeAlphaTable } from "../../table/prototypeAlphaTable";
import type { PhysicsWorld as PhysicsWorldType } from "../PhysicsWorld";
import {
  buildLaunchToDropTraceArtifactPayload,
  PR0206_OBSERVATION_STEPS,
  PR0206_PROOF_MATRIX_CASES,
  writeLaunchToDropTraceArtifact,
  type LaunchToDropTraceCaseRecord,
} from "../test-support/physicsTestTelemetry";
import { runLaunchProofCase, runLaunchToDropTraceCase } from "./PhysicsWorld.launcher.spec-support";

let PhysicsWorld: typeof PhysicsWorldType;
let PROTOTYPE_ALPHA_TABLE: PrototypeAlphaTable;

describe("PhysicsWorld Launcher proof", () => {
  beforeAll(async () => {
    const performanceLike = globalThis.performance ?? { now: () => Date.now() };
    Object.defineProperty(globalThis, "performance", {
      value: performanceLike,
      configurable: true,
      enumerable: true,
      writable: true,
    });
    Object.defineProperty(globalThis, "self", {
      value: globalThis,
      configurable: true,
      enumerable: true,
      writable: true,
    });

    ({ PhysicsWorld } = await import("../PhysicsWorld"));
    ({ PROTOTYPE_ALPHA_TABLE } = await import("../../table/prototypeAlphaTable"));
  });

  it("runs the unchanged PR-0206 matrix and records proof-only root-cause telemetry contracts", async () => {
    const gateTag = PROTOTYPE_ALPHA_TABLE.gates[0].tag;
    const records = [];

    for (const proofCase of PR0206_PROOF_MATRIX_CASES) {
      records.push(
        await runLaunchProofCase({ PhysicsWorld, PROTOTYPE_ALPHA_TABLE }, proofCase, gateTag),
      );
    }

    expect(records).toHaveLength(PR0206_PROOF_MATRIX_CASES.length);
  });

  it("records the PR-0209 launch-to-drop trace matrix artifact with deterministic phase contracts", async () => {
    const gateTag = PROTOTYPE_ALPHA_TABLE.gates[0].tag;
    const records: LaunchToDropTraceCaseRecord[] = [];

    for (const proofCase of PR0206_PROOF_MATRIX_CASES) {
      records.push(
        await runLaunchToDropTraceCase({ PhysicsWorld, PROTOTYPE_ALPHA_TABLE }, proofCase, gateTag),
      );
    }

    const payload = buildLaunchToDropTraceArtifactPayload(records);
    await writeLaunchToDropTraceArtifact(payload);

    expect(records).toHaveLength(PR0206_PROOF_MATRIX_CASES.length);
    expect(records.map((record) => record.observation_steps)).toEqual(
      Array.from({ length: records.length }, () => PR0206_OBSERVATION_STEPS),
    );
  });
});
