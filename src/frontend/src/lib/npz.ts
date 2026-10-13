import { unzipSync } from 'fflate';

/**
 * Minimal reader for NumPy .npy / .npz files (little-endian numeric dtypes),
 * used to decode original research bytes in the browser for verification.
 */
export type NumericArray = Int32Array | Float64Array | Float32Array | Uint8Array | Int16Array | Uint32Array;

export interface NpyArray {
  dtype: string;
  shape: number[];
  fortranOrder: boolean;
  /** int64 is converted to float64 after checking every value is a safe integer. */
  data: NumericArray;
}

export class NpyFormatError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NpyFormatError';
  }
}

const ITEMSIZE: Record<string, number> = {
  '<i4': 4,
  '<i8': 8,
  '<f8': 8,
  '<f4': 4,
  '|u1': 1,
  '<u1': 1,
  '|b1': 1,
  '<i2': 2,
  '<u4': 4,
};

export function parseNpy(bytes: Uint8Array, label = 'npy'): NpyArray {
  const magic = String.fromCharCode(...bytes.subarray(1, 6));
  if (bytes[0] !== 0x93 || magic !== 'NUMPY') throw new NpyFormatError(`${label}: not a .npy file`);
  const major = bytes[6];
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const headerLength = major === 1 ? view.getUint16(8, true) : view.getUint32(8, true);
  const offset = major === 1 ? 10 : 12;
  const header = new TextDecoder('utf-8').decode(bytes.subarray(offset, offset + headerLength));
  const descr = /'descr':\s*'([^']+)'/.exec(header)?.[1];
  const fortran = /'fortran_order':\s*(True|False)/.exec(header)?.[1];
  const shapeText = /'shape':\s*\(([^)]*)\)/.exec(header)?.[1];
  if (!descr || !fortran || shapeText === undefined) throw new NpyFormatError(`${label}: unreadable header`);
  const itemsize = ITEMSIZE[descr];
  if (!itemsize) throw new NpyFormatError(`${label}: unsupported dtype ${descr}`);
  const shape = shapeText.split(',').map((s) => s.trim()).filter(Boolean).map(Number);
  const count = shape.reduce((a, b) => a * b, 1);
  const start = offset + headerLength;
  const end = start + count * itemsize;
  if (end > bytes.length) throw new NpyFormatError(`${label}: truncated data (${bytes.length} < ${end})`);
  // slice() copies into a fresh, aligned buffer.
  const raw = bytes.slice(start, end).buffer;
  let data: NumericArray;
  switch (descr) {
    case '<i4':
      data = new Int32Array(raw);
      break;
    case '<i8': {
      const big = new BigInt64Array(raw);
      const out = new Float64Array(count);
      for (let i = 0; i < count; i += 1) {
        const v = big[i];
        if (v > BigInt(Number.MAX_SAFE_INTEGER) || v < BigInt(Number.MIN_SAFE_INTEGER)) {
          throw new NpyFormatError(`${label}: int64 value outside safe integer range at ${i}`);
        }
        out[i] = Number(v);
      }
      data = out;
      break;
    }
    case '<f8':
      data = new Float64Array(raw);
      break;
    case '<f4':
      data = new Float32Array(raw);
      break;
    case '<i2':
      data = new Int16Array(raw);
      break;
    case '<u4':
      data = new Uint32Array(raw);
      break;
    default:
      data = new Uint8Array(raw);
  }
  return { dtype: descr, shape, fortranOrder: fortran === 'True', data };
}

export function parseNpz(bytes: Uint8Array): Record<string, NpyArray> {
  let files: Record<string, Uint8Array>;
  try {
    files = unzipSync(bytes);
  } catch (error) {
    throw new NpyFormatError(`npz: cannot unzip (${(error as Error).message})`);
  }
  const out: Record<string, NpyArray> = {};
  for (const [name, content] of Object.entries(files)) {
    if (!name.endsWith('.npy')) continue;
    out[name.slice(0, -4)] = parseNpy(content, name);
  }
  return out;
}

/** First index where two numeric sequences differ, or -1 if identical. */
export function firstMismatch(a: ArrayLike<number>, b: ArrayLike<number>): number {
  if (a.length !== b.length) return Math.min(a.length, b.length);
  for (let i = 0; i < a.length; i += 1) if (a[i] !== b[i]) return i;
  return -1;
}
