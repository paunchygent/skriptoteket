import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref, type EffectScope } from "vue";

import { useSandboxSettings } from "./useSandboxSettings";

const clientMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  isApiError: vi.fn(),
}));

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
  warning: vi.fn(),
  failure: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  apiFetch: clientMocks.apiFetch,
  isApiError: clientMocks.isApiError,
}));

vi.mock("../useToast", () => ({
  useToast: () => toastMocks,
}));

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

const settingsSchema = [{ name: "enabled", kind: "boolean", label: "Enabled" }];

const settingsResponse = {
  settings_schema: settingsSchema,
  schema_version: "1",
  state_rev: 2,
  values: { enabled: true },
};

function createScope(
  versionId: ReturnType<typeof ref>,
  schemaRef: ReturnType<typeof ref>,
) {
  let settings!: ReturnType<typeof useSandboxSettings>;
  const scope: EffectScope = effectScope();
  scope.run(() => {
    settings = useSandboxSettings({
      versionId: versionId as never,
      settingsSchema: schemaRef as never,
    });
  });
  return { scope, settings };
}

beforeEach(() => {
  clientMocks.apiFetch.mockReset();
  clientMocks.isApiError.mockReset();
  toastMocks.success.mockReset();
  toastMocks.warning.mockReset();
  toastMocks.failure.mockReset();
});

describe("useSandboxSettings", () => {
  it("resets when schema is missing", async () => {
    const versionId = ref("ver-1");
    const schemaRef = ref(null);

    const { scope, settings } = createScope(versionId, schemaRef);
    await flushPromises();

    expect(settings.hasSchema.value).toBe(false);
    expect(settings.schemaVersion.value).toBeNull();
    expect(clientMocks.apiFetch).not.toHaveBeenCalled();

    scope.stop();
  });

  it("resolves settings and warns on conflicts when saving", async () => {
    const versionId = ref("ver-1");
    const schemaRef = ref(settingsSchema);

    clientMocks.apiFetch.mockResolvedValueOnce(settingsResponse);

    const { scope, settings } = createScope(versionId, schemaRef);
    await flushPromises();

    const conflictError = { status: 409, message: "Conflict" };
    clientMocks.apiFetch.mockRejectedValueOnce(conflictError);
    clientMocks.isApiError.mockReturnValue(true);

    await settings.saveSettings();

    expect(clientMocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/editor/tool-versions/ver-1/sandbox-settings",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(toastMocks.warning).toHaveBeenCalledWith(
      "Inställningarna har ändrats i en annan flik. Ladda om sidan och försök igen.",
    );

    scope.stop();
  });
});
