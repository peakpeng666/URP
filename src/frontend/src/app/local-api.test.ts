import { describe, expect, it } from 'vitest';
import { allowedApiRequest, localApi } from '../../server/local-api';

describe('local API proxy boundary', () => {
  it('accepts same-origin browser and local command-line requests', () => {
    expect(allowedApiRequest({ host: '127.0.0.1:4173', origin: 'http://127.0.0.1:4173' }, 4173)).toBe(true);
    expect(allowedApiRequest({ host: 'localhost:5173' }, 5173)).toBe(true);
  });
  it('rejects forged hosts, remote/null origins, scheme and port mismatches', () => {
    for (const headers of [{}, { host: 'evil.test:4173' }, { host: '127.0.0.1:4180' },
      { host: '127.0.0.1:4173', origin: 'null' }, { host: '127.0.0.1:4173', origin: 'https://127.0.0.1:4173' },
      { host: '127.0.0.1:4173', origin: 'http://127.0.0.1:4174' },
      { host: '127.0.0.1:4173', origin: 'http://evil.test' }, { host: '127.0.0.1:4173', 'sec-fetch-site': 'cross-site' }]) {
      expect(allowedApiRequest(headers, 4173)).toBe(false);
    }
  });
  it('pins the upstream to loopback and refuses invalid ports', () => {
    expect(localApi(4180).proxy['/api/'].target).toBe('http://127.0.0.1:4180');
    for (const port of [0, -1, 1.2, 65536, NaN]) expect(() => localApi(port)).toThrow();
  });
});
