/**
 * Exam workspace guest sign-in prompt.
 *
 * Expected behavior:
 *   The prompt shows the given message and a "Logga in" link into the shared
 *   auth ceremony that returns to the signed-in exam workspace.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceSignInPrompt from "./ExamWorkspaceSignInPrompt.vue";
import { GUEST_LIMIT_SIGN_IN } from "./examWorkspaceGuestCopy";

describe("ExamWorkspaceSignInPrompt", () => {
  it("renders the message and a login link returning to the signed-in workspace", () => {
    const wrapper = mount(ExamWorkspaceSignInPrompt, {
      props: { message: GUEST_LIMIT_SIGN_IN },
    });

    expect(wrapper.text()).toContain(GUEST_LIMIT_SIGN_IN);
    const login = wrapper.find("[data-test='exam-workspace-sign-in-prompt-login']");
    expect(login.exists()).toBe(true);
    expect(login.text()).toBe("Logga in");
    const href = login.attributes("href") ?? "";
    expect(href).toContain(`next=${encodeURIComponent("/apps/exam-workspace")}`);
  });
});
