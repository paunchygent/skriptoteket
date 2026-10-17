import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import DocumentConverterResultActions from "./DocumentConverterResultActions.vue";

const props = {
  actionErrorMessage: null, canDownload: false, canRetry: false, canSave: false,
  feedbackIsError: false, feedbackMessage: null, filenameExtension: null,
  filenameStem: "", isDownloading: false, isRetryDisabled: false, isSaving: false,
  resultStateLabel: "Klar",
};

describe("Document Converter error announcements", () => {
  it("announces rejected format assertively but does not turn normal feedback into an alert", async () => {
    const wrapper = mount(DocumentConverterResultActions, { props });
    try {
      expect(wrapper.find('[role="alert"]').exists()).toBe(false);
      await wrapper.setProps({ feedbackIsError: true, feedbackMessage: "Filformatet stöds inte för den här konverteringen." });
      const alert = wrapper.get('[role="alert"]');
      expect(alert.text()).toContain("Filformatet");
      expect(alert.attributes("aria-live")).toBe("assertive");
      expect(alert.attributes("aria-atomic")).toBe("true");
      await wrapper.setProps({ feedbackIsError: false, feedbackMessage: "Konverteringen är klar." });
      expect(wrapper.find('[role="alert"]').exists()).toBe(false);
      const status = wrapper.get('[role="status"]');
      expect(status.text()).toBe("Konverteringen är klar.");
      expect(status.attributes("aria-live")).toBe("polite");
      expect(status.attributes("aria-atomic")).toBe("true");
    } finally { wrapper.unmount(); }
  });

  it.each(["Det gick inte att spara resultatet.", "Det gick inte att ladda ned resultatet."])("announces action failure %s", async (message) => {
    const wrapper = mount(DocumentConverterResultActions, { props });
    try {
      await wrapper.setProps({ actionErrorMessage: message });
      expect(wrapper.get('[role="alert"]').text()).toBe(message);
      expect(wrapper.get('[role="alert"]').attributes("aria-live")).toBe("assertive");
      expect(wrapper.get('[role="alert"]').attributes("aria-atomic")).toBe("true");
      await wrapper.setProps({ actionErrorMessage: null });
      expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    } finally { wrapper.unmount(); }
  });
});
