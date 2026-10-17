/** Session-history save completion and rejection contracts. */
import { describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { effectScope } from "vue";

import { useDocumentConverterSessionHistory } from "./useDocumentConverterSessionHistory";
import { useToastStore } from "../../../stores/toast";

type Deferred<T> = {
  promise: Promise<T>;
  reject: (reason?: unknown) => void;
  resolve: (value: T | PromiseLike<T>) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: Deferred<T>["resolve"];
  let reject!: Deferred<T>["reject"];
  const promise = new Promise<T>((innerResolve, innerReject) => {
    resolve = innerResolve;
    reject = innerReject;
  });
  return { promise, reject, resolve };
}

describe("Document Converter history save confirmation", () => {
  it.each(["entry", "artifact"] as const)("confirms only an awaited successful %s save", async (target) => {
    setActivePinia(createPinia());
    const scope = effectScope();
    const history = scope.run(() => useDocumentConverterSessionHistory())!;
    const success = vi.spyOn(useToastStore(), "success");
    const pending = deferred<void>();
    const save = vi.fn().mockReturnValueOnce(pending.promise);
    history.upsertEntry({
      id: "previous-result",
      filename: "lektion.pdf",
      resultTypeLabel: "PDF",
      sourceLabel: "lektion.html",
      status: "ready",
      ...(target === "entry" ? { save } : {
        artifacts: [{ id: "pdf", filename: "lektion.pdf", save }],
      }),
    });
    try {
      const saving = history.saveActiveEntry("min-lektion");
      expect(save).toHaveBeenCalledWith("min-lektion");
      expect(success).not.toHaveBeenCalled();
      pending.resolve();
      await saving;
      expect(success).toHaveBeenCalledTimes(1);
      expect(success.mock.calls[0]?.[0]).toMatch(/Mina filer/);
      expect(history.actionErrorMessage.value).toBeNull();

      save.mockRejectedValueOnce(new Error("network"));
      await history.saveActiveEntry("min-lektion");
      expect(success).toHaveBeenCalledTimes(1);
      expect(history.actionErrorMessage.value).toMatch(/spara/i);
    } finally {
      scope.stop();
    }
  });
});
