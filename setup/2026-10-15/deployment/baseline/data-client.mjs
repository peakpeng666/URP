import { ReplayEngine, ReplayComparison } from './replay.mjs';

export class DataLoadError extends Error {
  constructor(message, { code = 'LOAD_FAILED', url = null, cause } = {}) {
    super(message, cause ? { cause } : undefined);
    this.name = 'DataLoadError';
    this.code = code;
    this.url = url;
  }
}

export class StaleResponseError extends DataLoadError {
  constructor() {
    super('A newer request replaced this response', { code: 'STALE_RESPONSE' });
    this.name = 'StaleResponseError';
  }
}

const abortError = () => new DOMException('The request was cancelled', 'AbortError');

function descriptor(input) {
  const value = typeof input === 'string' ? { data_url: input } : input;
  if (!value || typeof value.data_url !== 'string' || !value.data_url) {
    throw new DataLoadError('A run URL or catalog run descriptor is required', { code: 'INVALID_DESCRIPTOR' });
  }
  if (value.sha256 != null && !/^[0-9a-f]{64}$/i.test(value.sha256)) {
    throw new DataLoadError('Invalid SHA256 in run descriptor', { code: 'INVALID_DESCRIPTOR', url: value.data_url });
  }
  return value;
}

/** Stateless byte-exact JSON loader, useful for meta/catalog/evidence as well. */
export async function fetchJSON(url, {
  fetchImpl = globalThis.fetch, signal, sha256 = null, cryptoImpl = globalThis.crypto,
} = {}) {
  if (typeof fetchImpl !== 'function') throw new DataLoadError('fetch is unavailable');
  if (signal?.aborted) throw abortError();
  let response;
  try { response = await fetchImpl(url, { signal, cache: 'no-cache' }); }
  catch (cause) {
    if (signal?.aborted || cause?.name === 'AbortError') throw abortError();
    throw new DataLoadError(`Cannot load ${url}`, { code: 'NETWORK_ERROR', url, cause });
  }
  if (!response.ok) throw new DataLoadError(`HTTP ${response.status} while loading ${url}`, { code: 'HTTP_ERROR', url });
  let bytes;
  try { bytes = await response.arrayBuffer(); }
  catch (cause) {
    if (signal?.aborted || cause?.name === 'AbortError') throw abortError();
    throw new DataLoadError(`Cannot read ${url}`, { code: 'BODY_ERROR', url, cause });
  }
  if (signal?.aborted) throw abortError();
  if (sha256 != null) {
    if (!/^[0-9a-f]{64}$/i.test(sha256)) throw new DataLoadError('Invalid expected SHA256', { code: 'INVALID_HASH', url });
    if (!cryptoImpl?.subtle) throw new DataLoadError('SHA256 verification requires Web Crypto (use localhost or HTTPS)', { code: 'HASH_UNAVAILABLE', url });
    const digest = await cryptoImpl.subtle.digest('SHA-256', bytes);
    const actual = Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, '0')).join('');
    if (actual !== sha256.toLowerCase()) throw new DataLoadError(`SHA256 mismatch for ${url}`, { code: 'HASH_MISMATCH', url });
  }
  if (signal?.aborted) throw abortError();
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
  catch (cause) { throw new DataLoadError(`Invalid JSON in ${url}`, { code: 'INVALID_JSON', url, cause }); }
}

/**
 * One client represents one changing replay panel. All loads on it replace the
 * preceding request, even if a transport ignores AbortSignal. No stale result
 * can become current. Independent panels should use independent clients.
 */
export class ReplayDataClient {
  #fetch;
  #crypto;
  #verifyHashes;
  #revision = 0;
  #controller = null;
  #current = null;
  #status = 'idle';
  #error = null;
  #sources = null;

  constructor({ fetchImpl = globalThis.fetch, cryptoImpl = globalThis.crypto, verifyHashes = true } = {}) {
    this.#fetch = fetchImpl;
    this.#crypto = cryptoImpl;
    this.#verifyHashes = verifyHashes;
  }

  get current() { return this.#current; }
  get status() { return this.#status; }
  get error() { return this.#error; }
  get sources() { return this.#sources == null ? null : structuredClone(this.#sources); }

  cancel() {
    this.#revision += 1;
    this.#controller?.abort();
    this.#controller = null;
    this.#current = null;
    this.#sources = null;
    this.#error = null;
    this.#status = 'idle';
  }

  async #load(inputs, { signal, processed = 0, checkpointInterval = 250 } = {}) {
    this.#controller?.abort();
    const revision = ++this.#revision;
    const controller = new AbortController();
    this.#controller = controller;
    this.#current = null;
    this.#sources = null;
    this.#error = null;
    this.#status = 'loading';
    const onAbort = () => controller.abort();
    signal?.addEventListener('abort', onAbort, { once: true });
    if (signal?.aborted) controller.abort();
    const assertCurrent = () => {
      if (revision !== this.#revision) throw new StaleResponseError();
      if (controller.signal.aborted) throw abortError();
    };
    try {
      const descriptors = inputs.map(descriptor);
      const runs = await Promise.all(descriptors.map(async (source) => {
        const run = await fetchJSON(source.data_url, {
          fetchImpl: this.#fetch, signal: controller.signal, cryptoImpl: this.#crypto,
          sha256: this.#verifyHashes ? source.sha256 ?? null : null,
        });
        assertCurrent();
        if (source.run_id != null && source.run_id !== run?.run_id) {
          throw new DataLoadError(`Run identity mismatch for ${source.data_url}`, { code: 'IDENTITY_MISMATCH', url: source.data_url });
        }
        if (source.policy != null && source.policy !== run?.policy) {
          throw new DataLoadError(`Policy mismatch for ${source.data_url}`, { code: 'IDENTITY_MISMATCH', url: source.data_url });
        }
        return run;
      }));
      assertCurrent();
      const engine = runs.length === 1
        ? new ReplayEngine(runs[0], { checkpointInterval })
        : new ReplayComparison(runs[0], runs[1], { checkpointInterval });
      engine.seek(processed);
      assertCurrent();
      this.#current = engine;
      this.#sources = descriptors.map((source, i) => ({
        runId: runs[i].run_id, dataUrl: source.data_url, sha256: source.sha256 ?? null,
        hashVerified: this.#verifyHashes && source.sha256 != null,
      }));
      this.#status = 'ready';
      return engine;
    } catch (error) {
      if (revision !== this.#revision) throw new StaleResponseError();
      controller.abort();
      this.#current = null;
      this.#sources = null;
      this.#error = error;
      this.#status = error?.name === 'AbortError' ? 'idle' : 'error';
      throw error;
    } finally {
      signal?.removeEventListener('abort', onAbort);
      if (revision === this.#revision) this.#controller = null;
    }
  }

  loadRun(source, options) { return this.#load([source], options); }
  loadComparison(left, right, options) { return this.#load([left, right], options); }
}
