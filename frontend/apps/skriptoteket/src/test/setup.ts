import { vi } from "vitest";

// Mock fetch globally
globalThis.fetch = vi.fn();

// Reset mocks between tests
beforeEach(() => {
  vi.clearAllMocks();
});
