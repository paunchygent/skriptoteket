import { describe, expect, it } from "vitest";

import type { components } from "../../api/openapi";
import { buildSandboxDebugJson, getSandboxDebugState } from "./sandboxDebugHelpers";

type EditorRunDetails = components["schemas"]["EditorRunDetails"];

describe("sandboxDebugHelpers", () => {
  const baseRun: EditorRunDetails = {
    run_id: "run-1",
    snapshot_id: "snapshot-1",
    version_id: "version-1",
    status: "failed",
    started_at: "2026-01-02T12:00:00Z",
    finished_at: "2026-01-02T12:01:00Z",
    error_summary: "Boom",
    stdout: null,
    stderr: null,
    stdout_bytes: null,
    stderr_bytes: null,
    stdout_max_bytes: null,
    stderr_max_bytes: null,
    stdout_truncated: null,
    stderr_truncated: null,
    artifacts: [],
    ui_payload: null,
  };

  it("marks missing details when stdout/stderr metadata are absent", () => {
    const state = getSandboxDebugState(baseRun);
    expect(state.hasMissingDetails).toBe(true);
    expect(state.hasNoOutput).toBe(false);
  });

  it("marks no output when stdout and stderr are empty strings", () => {
    const run: EditorRunDetails = {
      ...baseRun,
      stdout: "",
      stderr: "",
      stdout_bytes: 0,
      stderr_bytes: 0,
      stdout_max_bytes: 200000,
      stderr_max_bytes: 200000,
      stdout_truncated: false,
      stderr_truncated: false,
    };

    const state = getSandboxDebugState(run);
    expect(state.hasMissingDetails).toBe(false);
    expect(state.hasNoOutput).toBe(true);
  });

  it("marks available output when stdout or stderr has content", () => {
    const run: EditorRunDetails = {
      ...baseRun,
      stdout: "Hello",
      stderr: "Warn",
      stdout_bytes: 5,
      stderr_bytes: 4,
    };

    const state = getSandboxDebugState(run);
    expect(state.hasMissingDetails).toBe(false);
    expect(state.hasNoOutput).toBe(false);
  });

  it("builds JSON bundles with all required fields", () => {
    const json = buildSandboxDebugJson(baseRun);
    const parsed = JSON.parse(json) as Record<string, unknown>;

    expect(Object.keys(parsed).sort()).toEqual(
      [
        "run_id",
        "snapshot_id",
        "version_id",
        "status",
        "started_at",
        "finished_at",
        "error_summary",
        "stdout",
        "stderr",
        "stdout_bytes",
        "stderr_bytes",
        "stdout_max_bytes",
        "stderr_max_bytes",
        "stdout_truncated",
        "stderr_truncated",
      ].sort(),
    );
  });
});
