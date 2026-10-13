declare module '*.module.css' {
  const classes: Record<string, string>;
  export default classes;
}

/**
 * Type surface for Codex's framework-agnostic kernel (core/replay.mjs and
 * core/data-client.mjs). Kept deliberately loose: the kernel is the source of
 * truth for behaviour; these signatures only let the frontend call it typed.
 */
declare module '@core/replay.mjs' {
  export class ReplayDataError extends Error {
    details: Record<string, unknown>;
  }
  export class ReplayEngine {
    constructor(data: unknown, options?: { checkpointInterval?: number });
    readonly processed: number;
    readonly totalItems: number;
    readonly metadata: Record<string, unknown>;
    seek(processed: number): unknown;
    step(delta?: number): unknown;
    reset(): unknown;
    getState(options?: { retrospective?: boolean }): Record<string, unknown>;
    getBin(bin: number, options?: { includeItems?: boolean }): Record<string, unknown>;
    getBins(options?: {
      offset?: number;
      limit?: number;
      usedOnly?: boolean;
      includeItems?: boolean;
    }): { bins: Record<string, unknown>[]; offset: number; limit: number; total: number };
    getItems(options?: { start?: number; limit?: number; retrospective?: boolean }): Record<string, unknown>[];
    getCurve(options?: { retrospective?: boolean }): { processed: number; usedBins: number; totalVolume: number }[];
    getDecision(options?: { retrospective?: boolean }): Record<string, unknown>;
    getFinalResult(options?: { retrospective?: boolean }): Record<string, unknown> | null;
    hasSameStream(other: ReplayEngine): boolean;
  }
  export class ReplayComparison {
    constructor(left: unknown, right: unknown, options?: { checkpointInterval?: number });
    readonly processed: number;
    readonly totalItems: number;
    seek(processed: number): unknown;
    step(delta?: number): unknown;
    reset(): unknown;
    getState(options?: { retrospective?: boolean }): Record<string, unknown>;
    getBin(side: 'left' | 'right', bin: number, options?: { includeItems?: boolean }): Record<string, unknown>;
    getBins(
      side: 'left' | 'right',
      options?: { offset?: number; limit?: number; usedOnly?: boolean; includeItems?: boolean },
    ): { bins: Record<string, unknown>[]; offset: number; limit: number; total: number };
    getItems(options?: { start?: number; limit?: number; retrospective?: boolean }): Record<string, unknown>[];
    getCurve(side: 'left' | 'right', options?: { retrospective?: boolean }): { processed: number; usedBins: number; totalVolume: number }[];
    getDecision(side: 'left' | 'right', options?: { retrospective?: boolean }): Record<string, unknown>;
    getFinalResult(side: 'left' | 'right', options?: { retrospective?: boolean }): Record<string, unknown> | null;
  }
}

declare module '@core/data-client.mjs' {
  export class DataLoadError extends Error {
    code: string;
    url: string | null;
  }
  export class StaleResponseError extends DataLoadError {}
  export function fetchJSON(
    url: string,
    options?: {
      fetchImpl?: typeof fetch;
      signal?: AbortSignal;
      sha256?: string | null;
      cryptoImpl?: unknown;
    },
  ): Promise<unknown>;
  export class ReplayDataClient {
    constructor(options?: { fetchImpl?: typeof fetch; cryptoImpl?: unknown; verifyHashes?: boolean });
    readonly current: unknown;
    readonly status: string;
    readonly error: Error | null;
    readonly sources: unknown;
    cancel(): void;
    loadRun(source: unknown, options?: Record<string, unknown>): Promise<unknown>;
    loadComparison(left: unknown, right: unknown, options?: Record<string, unknown>): Promise<unknown>;
  }
}
