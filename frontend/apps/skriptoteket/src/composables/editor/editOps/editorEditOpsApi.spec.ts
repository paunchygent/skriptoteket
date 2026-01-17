import { describe, expect, it, vi } from "vitest";

import { apiFetch } from "../../../api/client";
import { applyEditOps, previewEditOps, requestEditOps } from "./editorEditOpsApi";

vi.mock("../../../api/client", () => ({
  apiFetch: vi.fn(),
}));

const virtualFiles = {
  "tool.py": "print('hi')\n",
  "entrypoint.txt": "run_tool\n",
  "settings_schema.json": "{}",
  "input_schema.json": "{}",
  "usage_instructions.md": "",
};

describe("editorEditOpsApi", () => {
  it("sends request edit ops with correlation header", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ enabled: false, ops: [] });

    await requestEditOps({
      toolId: "tool-1",
      message: "Update",
      allowRemoteFallback: false,
      activeFile: "tool.py",
      virtualFiles,
      selection: { from: 1, to: 2 },
      cursor: { pos: 2 },
      correlationId: "corr-1",
    });

    expect(apiFetch).toHaveBeenCalledWith("/api/v1/editor/edit-ops", {
      method: "POST",
      body: {
        tool_id: "tool-1",
        message: "Update",
        allow_remote_fallback: false,
        active_file: "tool.py",
        virtual_files: virtualFiles,
        selection: { from: 1, to: 2 },
        cursor: { pos: 2 },
      },
      headers: { "X-Correlation-ID": "corr-1" },
    });
  });

  it("sends preview requests with selection and cursor", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true });

    await previewEditOps({
      toolId: "tool-1",
      activeFile: "tool.py",
      virtualFiles,
      ops: [
        {
          op: "patch",
          target_file: "tool.py",
          patch_lines: ["@@ -0,0 +1 @@", "+print('hi')"],
        },
      ],
      selection: { from: 3, to: 4 },
      cursor: { pos: 4 },
      correlationId: "corr-1",
    });

    expect(apiFetch).toHaveBeenCalledWith("/api/v1/editor/edit-ops/preview", {
      method: "POST",
      body: {
        tool_id: "tool-1",
        active_file: "tool.py",
        virtual_files: virtualFiles,
        ops: [
          {
            op: "patch",
            target_file: "tool.py",
            patch_lines: ["@@ -0,0 +1 @@", "+print('hi')"],
          },
        ],
        selection: { from: 3, to: 4 },
        cursor: { pos: 4 },
      },
      headers: { "X-Correlation-ID": "corr-1" },
    });
  });

  it("sends apply requests with base hash and patch id", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true });

    await applyEditOps({
      toolId: "tool-1",
      activeFile: "tool.py",
      virtualFiles,
      ops: [
        {
          op: "patch",
          target_file: "tool.py",
          patch_lines: ["@@ -0,0 +1 @@", "+print('hi')"],
        },
      ],
      baseHash: "sha256:base",
      patchId: "sha256:patch",
      selection: null,
      cursor: null,
      correlationId: "corr-1",
    });

    expect(apiFetch).toHaveBeenCalledWith("/api/v1/editor/edit-ops/apply", {
      method: "POST",
      body: {
        tool_id: "tool-1",
        active_file: "tool.py",
        virtual_files: virtualFiles,
        ops: [
          {
            op: "patch",
            target_file: "tool.py",
            patch_lines: ["@@ -0,0 +1 @@", "+print('hi')"],
          },
        ],
        base_hash: "sha256:base",
        patch_id: "sha256:patch",
      },
      headers: { "X-Correlation-ID": "corr-1" },
    });
  });
});
