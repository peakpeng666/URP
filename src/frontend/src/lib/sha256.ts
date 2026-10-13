import { sha256 as nobleSha256 } from '@noble/hashes/sha2.js';
import { bytesToHex } from '@noble/hashes/utils.js';

/**
 * SHA-256 over raw bytes. Web Crypto is only available in secure contexts
 * (https or localhost); on a LAN address we fall back to @noble/hashes so hash
 * verification never silently disappears.
 */
export async function sha256Hex(data: ArrayBuffer | Uint8Array): Promise<string> {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
  const subtle = globalThis.crypto?.subtle;
  if (subtle) {
    const view = bytes.byteOffset === 0 && bytes.byteLength === bytes.buffer.byteLength
      ? bytes
      : bytes.slice();
    const digest = await subtle.digest('SHA-256', view as Uint8Array<ArrayBuffer>);
    return bytesToHex(new Uint8Array(digest));
  }
  return bytesToHex(nobleSha256(bytes));
}

export const hashEngineName = (): string => (globalThis.crypto?.subtle ? 'Web Crypto' : '@noble/hashes（非安全上下文回退）');

/** Crypto-like object for core/data-client.mjs when crypto.subtle is missing. */
export const cryptoShim = {
  subtle: {
    async digest(_algorithm: string, data: ArrayBuffer | ArrayBufferView): Promise<ArrayBuffer> {
      const bytes = data instanceof ArrayBuffer
        ? new Uint8Array(data)
        : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
      return nobleSha256(bytes).slice().buffer;
    },
  },
};

export function cryptoForClient(): { subtle: unknown } {
  return globalThis.crypto?.subtle ? globalThis.crypto : cryptoShim;
}

/** Canonical JSON of an integer list, identical to Python json.dumps(..., separators=(',',':')). */
export function canonicalIntList(values: ArrayLike<number>): string {
  let s = '[';
  for (let i = 0; i < values.length; i += 1) {
    if (i) s += ',';
    s += String(values[i]);
  }
  return `${s}]`;
}

export async function sha256OfText(text: string): Promise<string> {
  return sha256Hex(new TextEncoder().encode(text));
}
