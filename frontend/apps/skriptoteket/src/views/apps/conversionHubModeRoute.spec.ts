/**
 * Legacy Conversion Hub route residue tests.
 *
 * Slice purpose:
 *   Prove stale `mode` query residue stays on the generic backend app route
 *   instead of selecting a canonical teacher-facing product identity.
 */

import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import { routes } from "../../router/routes";

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes,
  });
}

describe("legacy Conversion Hub route residue", () => {
  it("keeps transcript query residue on the generic backend app route", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/apps/documents.conversion_hub?mode=transcript");

    expect(resolved.name).toBe("app-detail");
    expect(resolved.params.appId).toBe("documents.conversion_hub");
    expect(resolved.query).toEqual({ mode: "transcript" });
  });

  it("keeps canonical Audio Transcription independent of legacy query residue", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/apps/audio-transcription");

    expect(resolved.name).toBe("audio-transcription-authenticated");
    expect(resolved.params).toEqual({});
    expect(resolved.query).toEqual({});
  });
});
