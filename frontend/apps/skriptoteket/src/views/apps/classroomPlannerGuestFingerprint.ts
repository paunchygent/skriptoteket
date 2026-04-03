/**
 * Klassrumskartan guest snapshot fingerprint helpers.
 *
 * This module creates deterministic fingerprints and content hashes for the
 * browser-owned guest workspace contract so later authenticated imports can
 * dedupe assets safely without relying on mutable local ids.
 */

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map((entry) => stableStringify(entry)).join(",")}]`;
  }

  const entries = Object.entries(value as Record<string, unknown>).sort(([left], [right]) => {
    return left.localeCompare(right);
  });
  const serializedEntries = entries.map(([key, entryValue]) => {
    return `${JSON.stringify(key)}:${stableStringify(entryValue)}`;
  });
  return `{${serializedEntries.join(",")}}`;
}

function rightRotate(value: number, bits: number): number {
  return (value >>> bits) | (value << (32 - bits));
}

function sha256Hex(value: string): string {
  const message = Array.from(new TextEncoder().encode(value));
  const messageBitLength = message.length * 8;
  const highBits = Math.floor(messageBitLength / 0x1_0000_0000);
  const lowBits = messageBitLength >>> 0;

  message.push(0x80);
  while ((message.length % 64) !== 56) {
    message.push(0);
  }

  for (const shift of [24, 16, 8, 0]) {
    message.push((highBits >>> shift) & 0xff);
  }
  for (const shift of [24, 16, 8, 0]) {
    message.push((lowBits >>> shift) & 0xff);
  }

  const roundConstants = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ];
  const hash = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ];
  const schedule = new Array<number>(64);

  for (let offset = 0; offset < message.length; offset += 64) {
    for (let index = 0; index < 16; index += 1) {
      const start = offset + index * 4;
      schedule[index] = (
        (message[start]! << 24)
        | (message[start + 1]! << 16)
        | (message[start + 2]! << 8)
        | message[start + 3]!
      ) >>> 0;
    }

    for (let index = 16; index < 64; index += 1) {
      const sigma0 = (
        rightRotate(schedule[index - 15]!, 7)
        ^ rightRotate(schedule[index - 15]!, 18)
        ^ (schedule[index - 15]! >>> 3)
      ) >>> 0;
      const sigma1 = (
        rightRotate(schedule[index - 2]!, 17)
        ^ rightRotate(schedule[index - 2]!, 19)
        ^ (schedule[index - 2]! >>> 10)
      ) >>> 0;
      schedule[index] = (
        schedule[index - 16]!
        + sigma0
        + schedule[index - 7]!
        + sigma1
      ) >>> 0;
    }

    let [a, b, c, d, e, f, g, h] = hash;

    for (let index = 0; index < 64; index += 1) {
      const sigma1 = (
        rightRotate(e, 6)
        ^ rightRotate(e, 11)
        ^ rightRotate(e, 25)
      ) >>> 0;
      const choose = ((e & f) ^ (~e & g)) >>> 0;
      const temp1 = (h + sigma1 + choose + roundConstants[index]! + schedule[index]!) >>> 0;
      const sigma0 = (
        rightRotate(a, 2)
        ^ rightRotate(a, 13)
        ^ rightRotate(a, 22)
      ) >>> 0;
      const majority = ((a & b) ^ (a & c) ^ (b & c)) >>> 0;
      const temp2 = (sigma0 + majority) >>> 0;

      h = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }

    hash[0] = (hash[0]! + a) >>> 0;
    hash[1] = (hash[1]! + b) >>> 0;
    hash[2] = (hash[2]! + c) >>> 0;
    hash[3] = (hash[3]! + d) >>> 0;
    hash[4] = (hash[4]! + e) >>> 0;
    hash[5] = (hash[5]! + f) >>> 0;
    hash[6] = (hash[6]! + g) >>> 0;
    hash[7] = (hash[7]! + h) >>> 0;
  }

  return hash.map((entry) => entry.toString(16).padStart(8, "0")).join("");
}

export function createClassroomPlannerGuestFingerprint(value: unknown): string {
  return `sha256:${sha256Hex(stableStringify(value))}`;
}

export function createClassroomPlannerGuestContentHash(value: unknown): string {
  return `sha256:${sha256Hex(stableStringify(value))}`;
}
