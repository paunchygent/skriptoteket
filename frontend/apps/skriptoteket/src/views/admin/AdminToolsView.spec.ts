import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiGet } from "../../api/client";
import { SystemMessage } from "../../components/ui";
import AdminToolsView from "./AdminToolsView.vue";

vi.mock("../../api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  isApiError: () => false,
}));

vi.mock("../../composables/useToast", () => ({
  useToast: () => ({ success: vi.fn(), failure: vi.fn() }),
}));

vi.mock("vue-router", () => ({
  RouterLink: { template: "<a><slot /></a>" },
  useRouter: () => ({ push: vi.fn() }),
}));

describe("AdminToolsView failure feedback", () => {
  beforeEach(() => {
    vi.mocked(apiGet).mockReset();
  });

  it("announces model-only load errors and clears the model on one dismissal", async () => {
    vi.mocked(apiGet).mockRejectedValueOnce(new Error("Verktygen kunde inte hämtas"));
    const wrapper = mount(AdminToolsView, {
      global: { stubs: { CreateDraftToolModal: true } },
    });
    await flushPromises();

    const alert = wrapper.get('[role="alert"]');
    expect(alert.text()).toContain("Verktygen kunde inte hämtas");
    expect(alert.attributes("aria-live")).toBe("assertive");
    expect(alert.attributes("aria-atomic")).toBe("true");

    const message = wrapper.getComponent(SystemMessage);
    expect(message.props("tone")).toBe("failure");
    await alert.get('button[aria-label="Stäng"]').trigger("click");

    expect(message.emitted("update:modelValue")).toEqual([[null]]);
    expect(message.emitted("dismiss")).toEqual([[]]);
    expect(message.props("modelValue")).toBeNull();
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    wrapper.unmount();
  });
});
