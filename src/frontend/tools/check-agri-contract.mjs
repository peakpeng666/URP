/** Build real TS templates and pass them to the actual Python backend validator.
 * Run from anywhere: AGRI_PYTHON=src/lab/.venv/bin/python node src/frontend/tools/check-agri-contract.mjs [output.json]
 * Requires installed frontend TypeScript and lab dependencies; absence is an error, never a silent pass.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import ts from 'typescript';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const source = path.join(root, 'src/frontend/src/studio/agri');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'urp-agri-contract-'));
try {
  fs.writeFileSync(path.join(temp, 'package.json'), '{"type":"module"}');
  for (const rel of ['geometry.ts', 'patterns/runnable.ts', 'patterns/approx.ts', 'patterns/proposals.ts', 'patterns/index.ts']) {
    const code = ts.transpileModule(fs.readFileSync(path.join(source, rel), 'utf8'), {
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
    }).outputText.replace(/from ['"]([.][^'"]+)['"]/g, (_, p) => `from '${p}.js'`);
    const target = path.join(temp, rel.replace(/\.ts$/, '.js'));
    fs.mkdirSync(path.dirname(target), { recursive: true }); fs.writeFileSync(target, code);
  }
  const { AGRI_PATTERNS } = await import(pathToFileURL(path.join(temp, 'patterns/index.js')));
  const buildable = AGRI_PATTERNS.filter(p => p.runnable);
  if (buildable.length !== 22) throw new Error(`Expected 22 builders; got ${buildable.length}`);
  const records = [];
  for (const pattern of buildable) for (const seed of [42, 7, 2026]) {
    const values = Object.fromEntries(pattern.runnable.params.map(p => [p.key, p.default]));
    records.push({ pattern: pattern.id, seed, scenario: pattern.runnable.build(values, seed) });
  }
  if (process.argv[3]) fs.writeFileSync(process.argv[3], JSON.stringify(records, null, 2));
  const input = path.join(temp, 'instances.json');fs.writeFileSync(input, JSON.stringify(records));
  const python = process.env.AGRI_PYTHON || path.join(root, 'src/lab/.venv/bin/python');
  const result = spawnSync(python, [path.join(root, 'src/lab/tests/agri_contract_bridge.py'), input], {
    encoding: 'utf8', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' }, maxBuffer: 10 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  if (process.argv[2]) fs.writeFileSync(process.argv[2], result.stdout);
  process.stdout.write(result.stdout); process.stderr.write(result.stderr);
  if (result.status !== 0) process.exitCode = result.status ?? 1;
} finally { fs.rmSync(temp, { recursive: true, force: true }); }
