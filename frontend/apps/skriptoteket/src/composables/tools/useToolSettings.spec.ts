import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref, type EffectScope } from "vue";

import { useToolSettings } from "./useToolSettings";

const clientMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
  isApiError: vi.fn(),
}));

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
  warning: vi.fn(),
  failure: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  apiFetch: clientMocks.apiFetch,
  apiGet: clientMocks.apiGet,
  isApiError: clientMocks.isApiError,
}));

vi.mock("../useToast", () => ({
  useToast: () => toastMocks,
}));

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

const settingsSchema = [
  { name: "enabled", kind: "boolean", label: "Enabled" },
  { name: "title", kind: "string", label: "Title" },
];

const settingsResponse = {
  settings_schema: settingsSchema,
  schema_version: "1",
  state_rev: 2,
  values: { enabled: true, title: "Hello" },
};

function createScope(toolId: ReturnType<typeof ref>) {
  let settings!: ReturnType<typeof useToolSettings>;
  const scope: EffectScope = effectScope();
  scope.run(() => {
    settings = useToolSettings({ toolId });
  });
  return { scope, settings };
}

beforeEach(() => {
  clientMocks.apiFetch.mockReset();
  clientMocks.apiGet.mockReset();
  clientMocks.isApiError.mockReset();
  toastMocks.success.mockReset();
  toastMocks.warning.mockReset();
  toastMocks.failure.mockReset();
});

describe("useToolSettings", () => {
  it("loads settings and builds form values", async () => {
    const toolId = ref("tool-1");
    clientMocks.apiGet.mockResolvedValueOnce(settingsResponse);

    const { scope, settings } = createScope(toolId);
    await flushPromises();

    expect(settings.settingsSchema.value).toEqual(settingsSchema);
    expect(settings.values.value).toEqual({ enabled: true, title: "Hello" });
    expect(settings.isLoading.value).toBe(false);

    scope.stop();
  });

  it("warns on optimistic lock conflicts when saving", async () => {
    const toolId = ref("tool-1");
    clientMocks.apiGet.mockResolvedValueOnce(settingsResponse);

    const { scope, settings } = createScope(toolId);
    await flushPromises();

    const conflictError = { status: 409, message: "Conflict" };
    clientMocks.apiFetch.mockRejectedValueOnce(conflictError);
    clientMocks.isApiError.mockReturnValue(true);

    await settings.saveSettings();

    expect(clientMocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/tools/tool-1/settings",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(toastMocks.warning).toHaveBeenCalledWith(
      "Inställningarna har ändrats i en annan flik. Ladda om sidan och försök igen.",
    );

    scope.stop();
  });
});
