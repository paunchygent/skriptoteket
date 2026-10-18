import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ExamWorkspaceTeacherHost from "./ExamWorkspaceTeacherHost.vue";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";

// The host's whole job is choosing the store, so the view is stubbed and its props read.
vi.mock("./ExamWorkspaceView.vue", () => ({
  default: { name: "ExamWorkspaceViewStub", props: ["store"], template: "<div />" },
}));

describe("ExamWorkspaceTeacherHost", () => {
  it("mounts the workspace on the signed-in server store", () => {
    const wrapper = mount(ExamWorkspaceTeacherHost);

    const view = wrapper.findComponent({ name: "ExamWorkspaceViewStub" });
    expect(view.exists()).toBe(true);
    expect(view.props("store")).toBe(serverExamWorkspaceStore);
  });
});
