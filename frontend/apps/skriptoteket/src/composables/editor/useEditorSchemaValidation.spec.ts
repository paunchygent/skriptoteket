import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref, type EffectScope, type Ref } from "vue";

import { apiPost } from "../../api/client";
import { useEditorSchemaValidation } from "./useEditorSchemaValidation";

vi.mock("../../api/client", () => ({
  apiPost: vi.fn(),
  isApiError: (error: unknown) => error instanceof Error,
}));

async function flushMicrotasks(): Promise<void> {
  await new Promise<void>((resolve) => queueMicrotask(() => resolve()));
  await new Promise<void>((resolve) => queueMicrotask(() => resolve()));
}

function createScope(params: {
  toolId: Ref<string>;
  inputSchema: Ref<unknown>;
  settingsSchema: Ref<unknown | null>;
  inputSchemaError: Ref<string | null>;
  settingsSchemaError: Ref<string | null>;
  isReadOnly: Ref<boolean>;
  debounceMs: number;
}) {
  let validation!: ReturnType<typeof useEditorSchemaValidation>;
  const scope: EffectScope = effectScope();
  scope.run(() => {
    validation = useEditorSchemaValidation(params);
  });
  return { scope, validation };
}

describe("useEditorSchemaValidation", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  it("debounces background validation and groups issues by schema", async () => {
    vi.mocked(apiPost).mockResolvedValueOnce({
      valid: false,
      issues: [
        {
          schema: "input_schema",
          path: "/0/max",
          message: "Max är för högt.",
          details: null,
        },
        {
          schema: "settings_schema",
          path: null,
          message: "Okänt fält.",
          details: null,
        },
      ],
    });

    const toolId = ref("tool-1");
    const inputSchema = ref<unknown>([{ kind: "file", min: 0, max: 11 }]);
    const settingsSchema = ref<unknown | null>(null);
    const inputSchemaError = ref<string | null>(null);
    const settingsSchemaError = ref<string | null>(null);
    const isReadOnly = ref(false);

    const { scope, validation } = createScope({
      toolId,
      inputSchema,
      settingsSchema,
      inputSchemaError,
      settingsSchemaError,
      isReadOnly,
      debounceMs: 10,
    });

    expect(validation.hasBlockingIssues.value).toBe(false);

    vi.advanceTimersByTime(9);
    await flushMicrotasks();
    expect(apiPost).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    await flushMicrotasks();

    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(validation.issuesBySchema.value.input_schema).toHaveLength(1);
    expect(validation.issuesBySchema.value.settings_schema).toHaveLength(1);
    expect(validation.hasBlockingIssues.value).toBe(true);

    scope.stop();
  });

  it("skips backend validation when JSON parse errors exist", async () => {
    vi.mocked(apiPost).mockResolvedValueOnce({ valid: true, issues: [] });

    const toolId = ref("tool-1");
    const inputSchema = ref<unknown>([]);
    const settingsSchema = ref<unknown | null>(null);
    const inputSchemaError = ref<string | null>("Ogiltig JSON");
    const settingsSchemaError = ref<string | null>(null);
    const isReadOnly = ref(false);

    const { scope, validation } = createScope({
      toolId,
      inputSchema,
      settingsSchema,
      inputSchemaError,
      settingsSchemaError,
      isReadOnly,
      debounceMs: 10,
    });

    vi.advanceTimersByTime(50);
    await flushMicrotasks();

    expect(apiPost).not.toHaveBeenCalled();
    expect(await validation.validateNow()).toBe(false);
    expect(apiPost).not.toHaveBeenCalled();
    expect(validation.hasBlockingIssues.value).toBe(false);
    expect(validation.issuesBySchema.value.input_schema).toHaveLength(0);
    expect(validation.issuesBySchema.value.settings_schema).toHaveLength(0);

    scope.stop();
  });

  it("validateNow runs immediately and returns validity", async () => {
    vi.mocked(apiPost).mockResolvedValueOnce({ valid: true, issues: [] });

    const toolId = ref("tool-1");
    const inputSchema = ref<unknown>([]);
    const settingsSchema = ref<unknown | null>(null);
    const inputSchemaError = ref<string | null>(null);
    const settingsSchemaError = ref<string | null>(null);
    const isReadOnly = ref(false);

    const { scope, validation } = createScope({
      toolId,
      inputSchema,
      settingsSchema,
      inputSchemaError,
      settingsSchemaError,
      isReadOnly,
      debounceMs: 10_000,
    });

    const resultPromise = validation.validateNow();
    await flushMicrotasks();

    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(await resultPromise).toBe(true);

    scope.stop();
  });
});
