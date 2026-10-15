import { cpSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

/** Historical exports are restored separately; missing exports are not build inputs. */
export function copyPublicAssets(source, destination) {
  mkdirSync(destination, { recursive: true });
  for (const name of readdirSync(source)) {
    const path = join(source, name);
    if (name === 'data' && !existsSync(path)) continue;
    cpSync(path, join(destination, name), { recursive: true, dereference: true });
  }
}
