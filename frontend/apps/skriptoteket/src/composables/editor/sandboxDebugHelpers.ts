import type { components } from "../../api/openapi";

type EditorRunDetails = components["schemas"]["EditorRunDetails"];
type RunStatus = components["schemas"]["RunStatus"];

type Nullable<T> = T | null | undefined;

export type SandboxDebugBundle = {
  run_id: string;
  snapshot_id: string | null;
  version_id: string | null;
  status: RunStatus;
  started_at: string;
  finished_at: string | null;
  error_summary: string | null;
  stdout: string | null;
  stderr: string | null;
  stdout_bytes: number | null;
  stderr_bytes: number | null;
  stdout_max_bytes: number | null;
  stderr_max_bytes: number | null;
  stdout_truncated: boolean | null;
  stderr_truncated: boolean | null;
};

export type SandboxDebugState = {
  hasMissingDetails: boolean;
  hasNoOutput: boolean;
};

function normalizeNullable<T>(value: Nullable<T>): T | null {
  return value === undefined ? null : value;
}

function hasAnyDebugDetail(run: EditorRunDetails): boolean {
  const values = [
    run.stdout,
    run.stderr,
    run.stdout_bytes,
    run.stderr_bytes,
    run.stdout_max_bytes,
    run.stderr_max_bytes,
    run.stdout_truncated,
    run.stderr_truncated,
  ];
  return values.some((value) => value !== null && value !== undefined);
}

function formatScalar(value: string | number | boolean | null): string {
  return value === null ? "null" : String(value);
}

export function buildSandboxDebugBundle(run: EditorRunDetails): SandboxDebugBundle {
  return {
    run_id: run.run_id,
    snapshot_id: normalizeNullable(run.snapshot_id),
    version_id: normalizeNullable(run.version_id),
    status: run.status,
    started_at: run.started_at,
    finished_at: normalizeNullable(run.finished_at),
    error_summary: normalizeNullable(run.error_summary),
    stdout: normalizeNullable(run.stdout),
    stderr: normalizeNullable(run.stderr),
    stdout_bytes: normalizeNullable(run.stdout_bytes),
    stderr_bytes: normalizeNullable(run.stderr_bytes),
    stdout_max_bytes: normalizeNullable(run.stdout_max_bytes),
    stderr_max_bytes: normalizeNullable(run.stderr_max_bytes),
    stdout_truncated: normalizeNullable(run.stdout_truncated),
    stderr_truncated: normalizeNullable(run.stderr_truncated),
  };
}

export function getSandboxDebugState(run: EditorRunDetails): SandboxDebugState {
  const hasDetails = hasAnyDebugDetail(run);
  return {
    hasMissingDetails: !hasDetails,
    hasNoOutput: hasDetails && run.stdout === "" && run.stderr === "",
  };
}

export function buildSandboxDebugJson(run: EditorRunDetails): string {
  return JSON.stringify(buildSandboxDebugBundle(run), null, 2);
}

export function buildSandboxDebugText(run: EditorRunDetails): string {
  const bundle = buildSandboxDebugBundle(run);
  const lines = [
    `run_id: ${bundle.run_id}`,
    `snapshot_id: ${formatScalar(bundle.snapshot_id)}`,
    `version_id: ${formatScalar(bundle.version_id)}`,
    `status: ${bundle.status}`,
    `started_at: ${bundle.started_at}`,
    `finished_at: ${formatScalar(bundle.finished_at)}`,
    `error_summary: ${formatScalar(bundle.error_summary)}`,
    `stdout_bytes: ${formatScalar(bundle.stdout_bytes)}`,
    `stdout_max_bytes: ${formatScalar(bundle.stdout_max_bytes)}`,
    `stdout_truncated: ${formatScalar(bundle.stdout_truncated)}`,
    `stderr_bytes: ${formatScalar(bundle.stderr_bytes)}`,
    `stderr_max_bytes: ${formatScalar(bundle.stderr_max_bytes)}`,
    `stderr_truncated: ${formatScalar(bundle.stderr_truncated)}`,
    "stdout:",
    bundle.stdout ?? "null",
    "stderr:",
    bundle.stderr ?? "null",
  ];

  return lines.join("\n");
}
