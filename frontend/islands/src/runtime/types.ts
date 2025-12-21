export type RunStatus = "running" | "succeeded" | "failed" | "timed_out";

export type UiOutputNoticeLevel = "info" | "warning" | "error";

export type UiOutput =
  | { kind: "notice"; level: UiOutputNoticeLevel; message: string }
  | { kind: "markdown"; markdown: string }
  | {
      kind: "table";
      title: string | null;
      columns: Array<{ key: string; label: string }>;
      rows: Array<Record<string, unknown>>;
    }
  | { kind: "json"; title: string | null; value: unknown }
  | { kind: "html_sandboxed"; html: string }
  | { kind: "vega_lite"; spec: unknown };

export type UiActionField =
  | { kind: "string"; name: string; label: string }
  | { kind: "text"; name: string; label: string }
  | { kind: "integer"; name: string; label: string }
  | { kind: "number"; name: string; label: string }
  | { kind: "boolean"; name: string; label: string }
  | {
      kind: "enum";
      name: string;
      label: string;
      options: Array<{ value: string; label: string }>;
    }
  | {
      kind: "multi_enum";
      name: string;
      label: string;
      options: Array<{ value: string; label: string }>;
    };

export type UiFormAction = {
  action_id: string;
  label: string;
  kind: "form";
  fields: UiActionField[];
};

export type UiPayloadV2 = {
  contract_version: 2;
  outputs: UiOutput[];
  next_actions: UiFormAction[];
};

export type RunArtifact = {
  artifact_id: string;
  path: string;
  bytes: number;
  download_url: string;
};

export type GetRunResult = {
  run: {
    run_id: string;
    status: RunStatus;
    ui_payload: UiPayloadV2 | null;
    artifacts: RunArtifact[];
  };
};

export type GetSessionStateResult = {
  session_state: {
    tool_id: string;
    context: string;
    state: Record<string, unknown>;
    state_rev: number;
    latest_run_id: string | null;
  };
};

export type StartActionResult = {
  run_id: string;
  state_rev: number;
};

export type ApiErrorResponse = {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
  correlation_id?: string | null;
};
