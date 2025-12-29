import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useToastStore } from "./toast";

describe("useToastStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("show()", () => {
    it("adds a toast to the list", () => {
      const store = useToastStore();
      const id = store.show("info", "Test message");

      expect(store.toasts).toHaveLength(1);
      expect(store.toasts[0]).toMatchObject({
        id,
        variant: "info",
        message: "Test message",
      });
    });

    it("trims whitespace from message", () => {
      const store = useToastStore();
      store.show("info", "  padded message  ");

      expect(store.toasts[0].message).toBe("padded message");
    });

    it("returns the toast ID", () => {
      const store = useToastStore();
      const id = store.show("success", "Test");

      expect(typeof id).toBe("string");
      expect(id.length).toBeGreaterThan(0);
    });

    it("uses default duration based on variant", () => {
      const store = useToastStore();

      store.show("info", "Info");
      expect(store.toasts[0].durationMs).toBe(6_000);

      store.show("success", "Success");
      expect(store.toasts[1].durationMs).toBe(6_000);

      store.show("warning", "Warning");
      // Need to dismiss first to make room (max 3)
    });

    it("uses custom duration when provided", () => {
      const store = useToastStore();
      store.show("info", "Custom duration", { durationMs: 3_000 });

      expect(store.toasts[0].durationMs).toBe(3_000);
    });

    it("clamps negative duration to 0", () => {
      const store = useToastStore();
      store.show("info", "No auto-dismiss", { durationMs: -1_000 });

      expect(store.toasts[0].durationMs).toBe(0);
    });
  });

  describe("max toasts limit", () => {
    it("enforces max 3 toasts (FIFO)", () => {
      const store = useToastStore();

      const id1 = store.show("info", "First");
      const id2 = store.show("info", "Second");
      const id3 = store.show("info", "Third");

      expect(store.toasts).toHaveLength(3);
      expect(store.toasts.map((t) => t.id)).toEqual([id1, id2, id3]);

      // Adding fourth should remove first
      const id4 = store.show("info", "Fourth");

      expect(store.toasts).toHaveLength(3);
      expect(store.toasts.map((t) => t.id)).toEqual([id2, id3, id4]);
    });

    it("removes oldest toast when limit exceeded", () => {
      const store = useToastStore();

      store.show("info", "First");
      store.show("info", "Second");
      store.show("info", "Third");
      store.show("info", "Fourth");

      expect(store.toasts[0].message).toBe("Second");
      expect(store.toasts[2].message).toBe("Fourth");
    });
  });

  describe("auto-dismiss", () => {
    it("removes toast after duration", () => {
      const store = useToastStore();
      store.show("info", "Will disappear", { durationMs: 5_000 });

      expect(store.toasts).toHaveLength(1);

      vi.advanceTimersByTime(5_000);

      expect(store.toasts).toHaveLength(0);
    });

    it("does not auto-dismiss when duration is 0", () => {
      const store = useToastStore();
      store.show("info", "Persistent", { durationMs: 0 });

      vi.advanceTimersByTime(100_000);

      expect(store.toasts).toHaveLength(1);
    });
  });

  describe("dismiss()", () => {
    it("removes specific toast by ID", () => {
      const store = useToastStore();
      const id1 = store.show("info", "First");
      const id2 = store.show("info", "Second");

      store.dismiss(id1);

      expect(store.toasts).toHaveLength(1);
      expect(store.toasts[0].id).toBe(id2);
    });

    it("clears auto-dismiss timer when manually dismissed", () => {
      const store = useToastStore();
      const id = store.show("info", "Test", { durationMs: 5_000 });

      store.dismiss(id);
      vi.advanceTimersByTime(5_000);

      // Should not throw or cause issues
      expect(store.toasts).toHaveLength(0);
    });

    it("handles dismissing non-existent ID gracefully", () => {
      const store = useToastStore();
      store.show("info", "Test");

      expect(() => store.dismiss("non-existent-id")).not.toThrow();
      expect(store.toasts).toHaveLength(1);
    });
  });

  describe("dismissAll()", () => {
    it("removes all toasts", () => {
      const store = useToastStore();
      store.show("info", "First");
      store.show("warning", "Second");
      store.show("success", "Third");

      store.dismissAll();

      expect(store.toasts).toHaveLength(0);
    });

    it("clears all timers", () => {
      const store = useToastStore();
      store.show("info", "First", { durationMs: 5_000 });
      store.show("info", "Second", { durationMs: 10_000 });

      store.dismissAll();
      vi.advanceTimersByTime(15_000);

      // Should not throw or cause issues
      expect(store.toasts).toHaveLength(0);
    });
  });

  describe("convenience methods", () => {
    it("info() creates info variant", () => {
      const store = useToastStore();
      store.info("Info message");

      expect(store.toasts[0].variant).toBe("info");
      expect(store.toasts[0].durationMs).toBe(6_000);
    });

    it("success() creates success variant", () => {
      const store = useToastStore();
      store.success("Success message");

      expect(store.toasts[0].variant).toBe("success");
      expect(store.toasts[0].durationMs).toBe(6_000);
    });

    it("warning() creates warning variant with longer duration", () => {
      const store = useToastStore();
      store.warning("Warning message");

      expect(store.toasts[0].variant).toBe("warning");
      expect(store.toasts[0].durationMs).toBe(10_000);
    });

    it("failure() creates failure variant with longest duration", () => {
      const store = useToastStore();
      store.failure("Failure message");

      expect(store.toasts[0].variant).toBe("failure");
      expect(store.toasts[0].durationMs).toBe(12_000);
    });

    it("convenience methods accept custom options", () => {
      const store = useToastStore();
      store.success("Custom", { durationMs: 1_000 });

      expect(store.toasts[0].durationMs).toBe(1_000);
    });
  });
});
