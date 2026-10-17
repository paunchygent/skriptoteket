import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiGet } from "../../api/client";
import type { FileRefInfo } from "./fileRefHelpers";
import { useToolFileRefs } from "./useToolFileRefs";

vi.mock("../../api/client", () => ({ apiGet: vi.fn() }));
vi.mock("../../stores/auth", () => ({
  useAuthStore: () => ({ bootstrapped: true, isAuthenticated: true }),
}));

type FileRefsResponse = { tool_id: string; context: string; files: FileRefInfo[] };

function deferredResponse() {
  let resolve!: (response: FileRefsResponse) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<FileRefsResponse>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

const oldFiles = [{ ref: "session:old.pdf", name: "old.pdf", bytes: 1 }];
const newFiles = [{ ref: "session:new.pdf", name: "new.pdf", bytes: 2 }];

describe("useToolFileRefs request ownership", () => {
  beforeEach(() => vi.clearAllMocks());

  it.each(["resolve", "reject"] as const)("ignores an older request that settles by %s after the next tool", async (settle) => {
    const oldResponse = deferredResponse();
    const newResponse = deferredResponse();
    vi.mocked(apiGet).mockReturnValueOnce(oldResponse.promise).mockReturnValueOnce(newResponse.promise);
    const { fileRefs, fetchFileRefs } = useToolFileRefs();

    const oldRequest = fetchFileRefs("old-tool");
    const newRequest = fetchFileRefs("new-tool");
    newResponse.resolve({ tool_id: "new-tool", context: "default", files: newFiles });
    await newRequest;
    expect(fileRefs.value).toEqual(newFiles);

    if (settle === "resolve") {
      oldResponse.resolve({ tool_id: "old-tool", context: "default", files: oldFiles });
    } else {
      oldResponse.reject(new Error("Old request failed"));
    }
    await oldRequest;
    expect(fileRefs.value).toEqual(newFiles);
  });

  it("does not restore references from an in-flight request after reset", async () => {
    const response = deferredResponse();
    vi.mocked(apiGet).mockReturnValueOnce(response.promise);
    const { fileRefs, fetchFileRefs, reset } = useToolFileRefs();
    const request = fetchFileRefs("old-tool");

    reset();
    response.resolve({ tool_id: "old-tool", context: "default", files: oldFiles });
    await request;
    expect(fileRefs.value).toEqual([]);
  });
});
