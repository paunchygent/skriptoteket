import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiGet, apiPost } from "../../api/client";
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
    vi.mocked(apiPost).mockReset();
  });

  afterEach(() => {
    document.body.replaceChildren();
  });

  it.each(["Avbryt", "Escape", "Skapa"] as const)(
    "returns focus to the actual create trigger after %s",
    async (action) => {
      vi.mocked(apiGet).mockResolvedValue({ tools: [] });
      vi.mocked(apiPost).mockResolvedValue({ tool: { id: "created-tool" } });
      const wrapper = mount(AdminToolsView, {
        attachTo: document.body,
        global: { stubs: { Teleport: true } },
      });
      try {
        await flushPromises();
        const trigger = wrapper.findAll("button").find((button) => button.text() === "Skapa nytt verktyg")!;
        expect(document.activeElement).not.toBe(trigger.element);
        await trigger.trigger("click");
        await flushPromises();

        const dialog = wrapper.get('[role="dialog"]');
        expect(dialog.attributes("aria-modal")).toBe("true");
        const heading = document.getElementById(dialog.attributes("aria-labelledby")!);
        expect(heading?.textContent).toContain("Skapa nytt verktyg");
        const title = dialog.get('input[type="text"]');
        expect(document.activeElement).toBe(title.element);
        await title.setValue("Nytt verktyg");

        if (action === "Escape") {
          await wrapper.get('[role="dialog"] input[type="text"]').trigger("keydown", { key: "Escape" });
        } else {
          await dialog.findAll("button").find((button) => button.text() === action)!.trigger("click");
        }
        await flushPromises();

        expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
        expect(document.activeElement).toBe(trigger.element);
        if (action === "Skapa") {
          expect(apiPost).toHaveBeenCalledExactlyOnceWith("/api/v1/admin/tools", {
            title: "Nytt verktyg",
            summary: null,
          });
        } else {
          expect(apiPost).not.toHaveBeenCalled();
        }
      } finally {
        wrapper.unmount();
      }
    },
  );

  it("keeps a failed creation open and returns focus only after dismissal", async () => {
    vi.mocked(apiGet).mockResolvedValue({ tools: [] });
    vi.mocked(apiPost).mockRejectedValue(new Error("Verktyget kunde inte skapas"));
    const wrapper = mount(AdminToolsView, {
      attachTo: document.body,
      global: { stubs: { Teleport: true } },
    });
    try {
      await flushPromises();
      const trigger = wrapper.findAll("button").find((button) => button.text() === "Skapa nytt verktyg")!;
      await trigger.trigger("click");
      await flushPromises();
      const title = wrapper.get<HTMLInputElement>('[role="dialog"] input[type="text"]');
      await title.setValue("Behåll mitt utkast");
      await wrapper.get('[role="dialog"]').findAll("button").find((button) => button.text() === "Skapa")!.trigger("click");
      await flushPromises();

      expect(wrapper.get('[role="alert"]').text()).toContain("Verktyget kunde inte skapas");
      expect(title.element.value).toBe("Behåll mitt utkast");
      expect(document.activeElement).not.toBe(trigger.element);
      await wrapper.get('[role="dialog"] input[type="text"]').trigger("keydown", { key: "ArrowLeft" });
      expect(wrapper.find('[role="dialog"]').exists()).toBe(true);
      await wrapper.get('[role="dialog"] input[type="text"]').trigger("keydown", { key: "Escape" });
      await flushPromises();
      expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
      expect(document.activeElement).toBe(trigger.element);
      expect(apiPost).toHaveBeenCalledTimes(1);
    } finally {
      wrapper.unmount();
    }
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
