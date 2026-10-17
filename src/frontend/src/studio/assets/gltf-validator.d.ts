declare module 'gltf-validator' {
  export interface ValidationMessage { code: string; message: string; severity: number; pointer?: string }
  export interface ValidationReport {
    info?: { generator?: string; version?: string };
    issues?: { numErrors: number; numWarnings: number; numInfos: number; numHints: number; messages: ValidationMessage[] };
  }
  export function validateBytes(data: Uint8Array, options?: {
    uri?: string; format?: 'glb' | 'gltf'; maxIssues?: number;
    externalResourceFunction?: (uri: string) => Promise<Uint8Array>;
  }): Promise<ValidationReport>;
  export function version(): string;
}
