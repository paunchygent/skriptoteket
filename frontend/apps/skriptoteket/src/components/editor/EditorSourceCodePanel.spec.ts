import { createPinia, setActivePinia } from "pinia";
import { defineComponent } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../api/openapi";
import { useAuthStore } from "../../stores/auth";
import { createTestRouter, mountWithContext } from "../../test/utils";
import groupingPy from "../../../../../../src/skriptoteket/script_bank/scripts/gruppgenerator/grouping.py?raw";
import rosterPy from "../../../../../../src/skriptoteket/script_bank/scripts/gruppgenerator/roster.py?raw";
import {
  AI_APP_LIMIT_NOTE,
  AI_USER_LIMIT_NOTE,
  markAiDailyLimit,
  resetAiDailyLimitForTests,
} from "../../composables/aiDailyLimit";
import EditorSourceCodePanel from "./EditorSourceCodePanel.vue";

type ApiRole = components["schemas"]["Role"];

type GhostTextOptions = {
  ghostText?: { enabled: { value: boolean } };
};

const intelligence = vi.hoisted(() => ({ options: null as GhostTextOptions | null }));

vi.mock("../../composables/editor/useSkriptoteketIntelligenceExtensions", async () => {
  const { ref } = await import("vue");
  return {
    useSkriptoteketIntelligenceExtensions: (options: GhostTextOptions) => {
      intelligence.options = options;
      return { extensions: ref([]), isLoading: ref(false), error: ref(null) };
    },
  };
});

const CodeMirrorEditorStub = defineComponent({
  name: "CodeMirrorEditor",
  props: {
    modelValue: { type: String, default: "" },
    extensions: { type: Array, default: () => [] },
    readOnly: { type: Boolean, default: false },
    language: { type: [Object, Array], default: null },
  },
  emits: ["update:modelValue", "viewReady"],
  template: '<div data-test="codemirror-stub" :data-value="modelValue" />',
});

function mountPanel(bundleFiles: Record<string, string> = {}, role: ApiRole = "admin") {
  const pinia = createPinia();
  setActivePinia(pinia);
  useAuthStore(pinia).user = {
    id: "user-1",
    email: "teacher@example.com",
    role,
    auth_provider: "huleedu",
  };
  return mountWithContext(EditorSourceCodePanel, {
    props: {
      entrypoint: "tool.py",
      sourceCode: "print('entrypoint')\n",
      isReadOnly: false,
      bundleFiles,
    },
    global: {
      plugins: [pinia, createTestRouter()],
      stubs: { CodeMirrorEditor: CodeMirrorEditorStub },
    },
  });
}

describe("EditorSourceCodePanel bundle file tabs", () => {
  it("renders no file tab strip for a single-file tool", () => {
    const wrapper = mountPanel({});

    expect(wrapper.find('[role="tablist"]').exists()).toBe(false);
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(0);
    expect(wrapper.findAllComponents(CodeMirrorEditorStub)).toHaveLength(1);
  });

  it("shows tool.py first, then bundle files sorted, and edits the selected file only", async () => {
    const wrapper = mountPanel({ "roster.py": rosterPy, "grouping.py": groupingPy });

    const tabs = wrapper.findAll('[role="tab"]');
    expect(tabs.map((tab) => tab.text())).toEqual(["tool.py", "grouping.py", "roster.py"]);
    expect(tabs[0]!.attributes("aria-selected")).toBe("true");

    await tabs[2]!.trigger("click");

    expect(wrapper.findAll('[role="tab"]')[2]!.attributes("aria-selected")).toBe("true");

    const editors = wrapper.findAllComponents(CodeMirrorEditorStub);
    expect(editors).toHaveLength(2);
    expect(editors[1]!.props("modelValue")).toBe(rosterPy);

    editors[1]!.vm.$emit("update:modelValue", "print('edited roster')\n");
    await wrapper.vm.$nextTick();

    const bundleUpdates = wrapper.emitted("update:bundleFiles");
    expect(bundleUpdates).toHaveLength(1);
    expect(bundleUpdates![0]![0]).toEqual({
      "roster.py": "print('edited roster')\n",
      "grouping.py": groupingPy,
    });
    expect(wrapper.emitted("update:sourceCode")).toBeUndefined();
  });

  it("falls back to the entrypoint when the active bundle file disappears", async () => {
    const wrapper = mountPanel({ "roster.py": rosterPy });

    await wrapper.findAll('[role="tab"]')[1]!.trigger("click");
    expect(wrapper.findAllComponents(CodeMirrorEditorStub)).toHaveLength(2);

    await wrapper.setProps({ bundleFiles: {} });

    expect(wrapper.find('[role="tablist"]').exists()).toBe(false);
    expect(wrapper.findAllComponents(CodeMirrorEditorStub)).toHaveLength(1);
  });
});

describe("EditorSourceCodePanel AI access gate", () => {
  it.each([
    ["user", false],
    ["contributor", false],
    ["admin", true],
    ["superuser", true],
  ] as const)("gates inline completion for role %s", (role, expected) => {
    const wrapper = mountPanel({}, role);

    expect(intelligence.options?.ghostText?.enabled.value).toBe(expected);
    wrapper.unmount();
  });
});

describe("EditorSourceCodePanel daily limit note", () => {
  beforeEach(() => {
    resetAiDailyLimitForTests();
  });

  it("shows no note and keeps ghost text enabled while the door has refused nothing", () => {
    const wrapper = mountPanel();

    expect(wrapper.find('[data-test="editor-ai-limit-note"]').exists()).toBe(false);
    expect(intelligence.options?.ghostText?.enabled.value).toBe(true);
    wrapper.unmount();
  });

  it("shows the door note inline and turns ghost text off once a limit is refused", async () => {
    const wrapper = mountPanel();

    markAiDailyLimit("small", "user_share");
    await wrapper.vm.$nextTick();

    expect(wrapper.get('[data-test="editor-ai-limit-note"]').text()).toBe(AI_USER_LIMIT_NOTE);
    expect(intelligence.options?.ghostText?.enabled.value).toBe(false);
    wrapper.unmount();
  });

  it.each(["pool", "user_share"] as const)(
    "keeps ghost text enabled and the note hidden after a full-allowance %s refusal",
    async (limit) => {
      const wrapper = mountPanel();

      markAiDailyLimit("full", limit);
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-test="editor-ai-limit-note"]').exists()).toBe(false);
      expect(intelligence.options?.ghostText?.enabled.value).toBe(true);
      wrapper.unmount();
    },
  );

  it.each(["small", "full"] as const)(
    "turns ghost text off after a usd_ceiling refusal from the %s allowance",
    async (allowance) => {
      const wrapper = mountPanel();

      markAiDailyLimit(allowance, "usd_ceiling");
      await wrapper.vm.$nextTick();

      expect(wrapper.get('[data-test="editor-ai-limit-note"]').text()).toBe(AI_APP_LIMIT_NOTE);
      expect(intelligence.options?.ghostText?.enabled.value).toBe(false);
      wrapper.unmount();
    },
  );
});
