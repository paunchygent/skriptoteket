import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref, type EffectScope } from "vue";

import { useToolVersionSettings } from "./useToolVersionSettings";

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

function createScope(versionId: ReturnType<typeof ref>) {
  let settings!: ReturnType<typeof useToolVersionSettings>;
  const scope: EffectScope = effectScope();
  scope.run(() => {
    settings = useToolVersionSettings({ versionId });
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

describe("useToolVersionSettings", () => {
  it("warns on optimistic lock conflicts when saving", async () => {
    const versionId = ref("ver-1");
    clientMocks.apiGet.mockResolvedValueOnce(settingsResponse);

    const { scope, settings } = createScope(versionId);
    await flushPromises();

    const conflictError = { status: 409, message: "Conflict" };
    clientMocks.apiFetch.mockRejectedValueOnce(conflictError);
    clientMocks.isApiError.mockReturnValue(true);

    await settings.saveSettings();

    expect(clientMocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/editor/tool-versions/ver-1/settings",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(toastMocks.warning).toHaveBeenCalledWith(
      "Inställningarna har ändrats i en annan flik. Ladda om sidan och försök igen.",
    );

    scope.stop();
  });
});
