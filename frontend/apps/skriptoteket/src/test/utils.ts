import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { createRouter, createWebHistory } from "vue-router";
import type { Component } from "vue";
import { vi } from "vitest";

// Minimal router for component tests
export function createTestRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [{ path: "/", component: { template: "<div />" } }],
  });
}

// Standard mount wrapper with Pinia + Router
export function mountWithContext(
  component: Component,
  options: Parameters<typeof mount>[1] = {}
) {
  return mount(component, {
    global: {
      plugins: [createTestingPinia({ createSpy: vi.fn }), createTestRouter()],
      ...options.global,
    },
    ...options,
  });
}

// API mock helper
export function mockFetch(response: unknown, status = 200) {
  return vi.mocked(fetch).mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(response),
    text: () => Promise.resolve(JSON.stringify(response)),
  } as Response);
}

// Mock fetch error (network failure)
export function mockFetchNetworkError(message = "Network error") {
  return vi.mocked(fetch).mockRejectedValueOnce(new Error(message));
}

// Mock fetch with headers
export function mockFetchWithHeaders(
  response: unknown,
  headers: Record<string, string>,
  status = 200
) {
  return vi.mocked(fetch).mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    json: () => Promise.resolve(response),
    text: () => Promise.resolve(JSON.stringify(response)),
  } as Response);
}
