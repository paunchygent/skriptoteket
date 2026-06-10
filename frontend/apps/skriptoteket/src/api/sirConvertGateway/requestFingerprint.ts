/**
 * Sir Convert Gateway request fingerprint helpers.
 *
 * Purpose:
 *   Provide deterministic JSON and upload hashing for authenticated Gateway
 *   idempotency keys across route-specific conversion clients.
 *
 * Relationships:
 *   - Used by DigiExam and transcript request-context builders.
 *   - Keeps transport clients free of hashing and canonical serialization
 *     details.
 */

export function stableJsonStringify(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableJsonStringify(item)).join(",")}]`;
  }
  const entries = Object.entries(value).sort(([left], [right]) => left.localeCompare(right));
  return `{${entries
    .map(([key, item]) => `${JSON.stringify(key)}:${stableJsonStringify(item)}`)
    .join(",")}}`;
}

async function sha256HexFromBytes(bytes: BufferSource): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export async function sha256HexFromText(value: string): Promise<string> {
  return await sha256HexFromBytes(new TextEncoder().encode(value));
}

async function blobBytes(blob: Blob): Promise<BufferSource> {
  const readableBlob = blob as Blob & {
    arrayBuffer?: () => Promise<ArrayBuffer>;
    text?: () => Promise<string>;
  };
  if (typeof readableBlob.arrayBuffer === "function") {
    return await readableBlob.arrayBuffer();
  }
  if (typeof readableBlob.text === "function") {
    return new TextEncoder().encode(await readableBlob.text());
  }
  return await new Promise<BufferSource>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (reader.result instanceof ArrayBuffer) {
        resolve(reader.result);
        return;
      }
      resolve(new TextEncoder().encode(String(reader.result ?? "")));
    };
    reader.onerror = () => reject(reader.error ?? new Error("Could not read upload bytes."));
    reader.readAsArrayBuffer(blob);
  });
}

export async function sha256HexFromBlob(blob: Blob): Promise<string> {
  return await sha256HexFromBytes(await blobBytes(blob));
}
