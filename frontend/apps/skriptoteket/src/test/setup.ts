import { vi } from "vitest";

type InMemoryStorage = Storage & { _data: Map<string, string> };

function createInMemoryStorage(): InMemoryStorage {
  const data = new Map<string, string>();
  return {
    _data: data,
    get length() {
      return data.size;
    },
    clear() {
      data.clear();
    },
    getItem(key: string) {
      return data.has(key) ? (data.get(key) ?? null) : null;
    },
    key(index: number) {
      if (index < 0 || index >= data.size) return null;
      return Array.from(data.keys())[index] ?? null;
    },
    removeItem(key: string) {
      data.delete(key);
    },
    setItem(key: string, value: string) {
      data.set(key, String(value));
    },
  };
}

const inMemoryStorage = createInMemoryStorage();
Object.defineProperty(globalThis, "localStorage", {
  value: inMemoryStorage,
  configurable: true,
  enumerable: true,
  writable: true,
});

if (typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    value: (query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
    configurable: true,
  });
}

if (typeof Range !== "undefined") {
  if (!Range.prototype.getClientRects) {
    Range.prototype.getClientRects = () => [] as unknown as DOMRectList;
  }
  if (!Range.prototype.getBoundingClientRect) {
    Range.prototype.getBoundingClientRect = () =>
      ({
        x: 0,
        y: 0,
        width: 0,
        height: 0,
        top: 0,
        right: 0,
        bottom: 0,
        left: 0,
        toJSON: () => ({}),
      }) as DOMRect;
  }
}

// Mock fetch globally
globalThis.fetch = vi.fn();

// Reset mocks between tests
beforeEach(() => {
  vi.clearAllMocks();
});
