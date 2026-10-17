import { describe, it, expect } from "vitest";
import { ref, nextTick } from "vue";

import type { components } from "../../api/openapi";
import { useToolInputs } from "./useToolInputs";

type ToolInputSchema = NonNullable<components["schemas"]["ToolMetadataResponse"]["input_schema"]>;

describe("useToolInputs", () => {
  it.each([
    ["integer", "1.5"], ["integer", "12junk"],
    ["number", "Infinity"], ["number", "-Infinity"], ["number", "1e309"],
    ["number", "12junk"], ["number", "1e"],
  ] as const)("rejects %s input %s in validation and serialization", (kind, raw) => {
    const schema = ref<ToolInputSchema>([{ name: "amount", kind, label: "Amount" }]);
    const { values, fieldErrors, buildApiValues } = useToolInputs({ schema });
    values.value.amount = raw;

    expect(fieldErrors.value.amount).toBeTruthy();
    expect(buildApiValues).toThrow();
  });

  it.each(["integer", "number"] as const)("preserves exponent notation for %s input", (kind) => {
    const schema = ref<ToolInputSchema>([{ name: "amount", kind, label: "Amount" }]);
    const { values, fieldErrors, buildApiValues } = useToolInputs({ schema });
    values.value.amount = "1e3";

    expect(fieldErrors.value).toEqual({});
    expect(buildApiValues()).toEqual({ amount: 1000 });
  });

  it("returns non-file fields", () => {
    const schema = ref<ToolInputSchema>([
      { name: "title", kind: "string", label: "Title" },
      { name: "files", kind: "file", label: "Files", accept: [], min: 1, max: 2 },
      { name: "count", kind: "integer", label: "Count" },
    ]);

    const { nonFileFields } = useToolInputs({ schema });

    expect(nonFileFields.value.map((field) => field.name)).toEqual(["title", "count"]);
  });

  it("builds file field specs", () => {
    const schema = ref<ToolInputSchema>([
      {
        name: "files",
        kind: "file",
        label: "Documents",
        accept: [".pdf"],
        min: 1,
        max: 3,
      },
    ]);

    const { fileFields, fileAcceptByField } = useToolInputs({ schema });

    expect(fileFields.value).toEqual([
      {
        name: "files",
        label: "Documents",
        min: 1,
        max: 3,
        accept: [".pdf"],
      },
    ]);
    expect(fileAcceptByField.value.files).toBe(".pdf");
  });

  it("tracks file selections and errors", async () => {
    const schema = ref<ToolInputSchema>([
      { name: "files", kind: "file", label: "Files", accept: [], min: 2, max: 3 },
    ]);

    const {
      fileSelections,
      fileErrors,
      setFileUploads,
      setFileRefs,
      setFileMode,
    } = useToolInputs({ schema });

    await nextTick();

    expect(fileSelections.value.files?.uploads.length ?? 0).toBe(0);
    expect(fileErrors.value.files).toBe("Välj minst 2 filer.");

    setFileUploads("files", [new File(["a"], "a.txt")]);
    expect(fileErrors.value.files).toBe("Välj minst 2 filer.");

    setFileUploads("files", [new File(["a"], "a.txt"), new File(["b"], "b.txt")]);
    expect(fileErrors.value.files).toBeNull();

    setFileMode("files", "refs");
    setFileRefs("files", ["session:a.txt"]);
    expect(fileErrors.value.files).toBe("Välj minst 2 filer.");
  });
});
