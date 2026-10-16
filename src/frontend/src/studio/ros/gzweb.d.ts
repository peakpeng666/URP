declare module 'gzweb' {
  export class SceneManager {
    constructor(config?: { elementId?: string; websocketUrl?: string; websocketKey?: string; enableLights?: boolean });
    resize(): void;
    destroy(): void;
    resetView(): void;
    follow(entityName: string): void;
    thirdPersonFollow(entityName: string): void;
    snapshot(): void;
    getConnectionStatus(): string;
  }
}
