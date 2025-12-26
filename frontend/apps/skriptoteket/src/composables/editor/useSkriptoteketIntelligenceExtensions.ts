import type { Extension } from "@codemirror/state";
import { computed, onMounted, ref, shallowRef, type Ref } from "vue";

import type { SkriptoteketIntelligenceConfig } from "./skriptoteketIntelligence";

type IntelligenceModule = typeof import("./skriptoteketIntelligence");

type UseSkriptoteketIntelligenceExtensionsOptions = {
  entrypointName: Readonly<Ref<string>>;
};

export function useSkriptoteketIntelligenceExtensions({
  entrypointName,
}: UseSkriptoteketIntelligenceExtensionsOptions): {
  extensions: Readonly<Ref<Extension[]>>;
  isLoading: Readonly<Ref<boolean>>;
  error: Readonly<Ref<string | null>>;
} {
  const moduleRef = shallowRef<IntelligenceModule | null>(null);
  const isLoading = ref(true);
  const error = ref<string | null>(null);

  const resolvedEntrypointName = computed(() => {
    const raw = entrypointName.value.trim();
    return raw || "run_tool";
  });

  const extensions = computed<Extension[]>(() => {
    if (!moduleRef.value) return [];
    const config: SkriptoteketIntelligenceConfig = { entrypointName: resolvedEntrypointName.value };
    const result = moduleRef.value.skriptoteketIntelligence(config);
    return Array.isArray(result) ? [...result] : [result];
  });

  async function load(): Promise<void> {
    isLoading.value = true;
    error.value = null;
    try {
      moduleRef.value = await import("./skriptoteketIntelligence");
    } catch (err: unknown) {
      moduleRef.value = null;
      if (err instanceof Error) {
        error.value = err.message;
      } else {
        error.value = "Det gick inte att ladda editor-intelligens.";
      }
    } finally {
      isLoading.value = false;
    }
  }

  onMounted(() => {
    void load();
  });

  return { extensions, isLoading, error };
}
