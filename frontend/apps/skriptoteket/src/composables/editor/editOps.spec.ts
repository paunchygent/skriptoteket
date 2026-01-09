import { describe, expect, it } from "vitest";

import type { components } from "../../api/openapi";
import { applyEditOpsToVirtualFiles } from "./editOps";
import type { VirtualFileTextMap } from "./virtualFiles";

type EditorEditOpsOp = components["schemas"]["EditorEditOpsOp"];

const baseFiles: VirtualFileTextMap = {
  "tool.py": "print('hej')\n",
  "entrypoint.txt": "run_tool\n",
  "settings_schema.json": "[]",
  "input_schema.json": "[]",
  "usage_instructions.md": "Instruktioner\n",
};

describe("applyEditOpsToVirtualFiles", () => {
  it("applies an insert at cursor in the active file", () => {
    const ops: EditorEditOpsOp[] = [
      {
        op: "insert",
        target_file: "tool.py",
        target: { kind: "cursor" },
        content: "# TODO\n",
      },
    ];

    const result = applyEditOpsToVirtualFiles({
      virtualFiles: baseFiles,
      ops,
      selection: null,
      cursor: { pos: 0 },
      activeFile: "tool.py",
    });

    expect(result.errors).toEqual([]);
    expect(result.nextFiles["tool.py"]).toBe("# TODO\nprint('hej')\n");
  });

  it("replaces a selection in the active file", () => {
    const ops: EditorEditOpsOp[] = [
      {
        op: "replace",
        target_file: "tool.py",
        target: { kind: "selection" },
        content: "return 1\n",
      },
    ];

    const result = applyEditOpsToVirtualFiles({
      virtualFiles: baseFiles,
      ops,
      selection: { from: 0, to: 13 },
      cursor: null,
      activeFile: "tool.py",
    });

    expect(result.errors).toEqual([]);
    expect(result.nextFiles["tool.py"]).toBe("return 1\n");
  });

  it("rejects selection targets when no selection is available", () => {
    const ops: EditorEditOpsOp[] = [
      {
        op: "replace",
        target_file: "tool.py",
        target: { kind: "selection" },
        content: "return 1\n",
      },
    ];

    const result = applyEditOpsToVirtualFiles({
      virtualFiles: baseFiles,
      ops,
      selection: null,
      cursor: { pos: 0 },
      activeFile: "tool.py",
    });

    expect(result.errors.length).toBeGreaterThan(0);
    expect(result.nextFiles["tool.py"]).toBe(baseFiles["tool.py"]);
  });

  it("rejects cursor targets in non-active files", () => {
    const ops: EditorEditOpsOp[] = [
      {
        op: "insert",
        target_file: "usage_instructions.md",
        target: { kind: "cursor" },
        content: "Extra\n",
      },
    ];

    const result = applyEditOpsToVirtualFiles({
      virtualFiles: baseFiles,
      ops,
      selection: null,
      cursor: { pos: 0 },
      activeFile: "tool.py",
    });

    expect(result.errors.length).toBeGreaterThan(0);
    expect(result.nextFiles["usage_instructions.md"]).toBe(baseFiles["usage_instructions.md"]);
  });
});
