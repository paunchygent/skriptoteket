/**
 * Browser debug bridge for deterministic launch-to-drop proof artifacts.
 *
 * The live Playwright proof path calls this helper through the DEV debug seam
 * so the browser returns the same canonical artifact payload as focused tests,
 * without any Python-side phase insertion or cadence reinterpretation.
 */

import type { LaunchToDropTraceArtifactPayload } from "./launchTraceContract";

export async function buildLaunchToDropTraceArtifactForBrowserDebug(): Promise<LaunchToDropTraceArtifactPayload> {
  const [{ PhysicsWorld }, { PROTOTYPE_ALPHA_TABLE }, { runLaunchToDropTraceMatrix }] =
    await Promise.all([
      import("./PhysicsWorld"),
      import("../table/prototypeAlphaTable"),
      import("./launchTraceMatrix"),
    ]);

  return runLaunchToDropTraceMatrix({
    PhysicsWorld,
    gateTag: PROTOTYPE_ALPHA_TABLE.gates[0].tag,
  });
}
