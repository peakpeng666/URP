// Execute the exact exported signature function, transpiled from its source.
// No browser state, application sources, or production records are modified.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../..');
const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== '--out' || !path.isAbsolute(args[1])) {
  throw new Error('Usage: node frontend_signature_probe.cjs --out /a/new/absolute/directory');
}
const out = args[1];
if (fs.existsSync(out)) throw new Error('Output directory must not exist; preserve original evidence');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.mkdirSync(out);
const ts = require(path.join(root, 'src/frontend/node_modules/typescript'));
const source = fs.readFileSync(path.join(root, 'src/frontend/src/studio/panels/PlanPanels.tsx'), 'utf8');
const start = source.indexOf('export function signature(');
const end = source.indexOf('\n}', start) + 2;
const fragment = source.slice(start, end);
if (start < 0 || end <= start) throw new Error('Cannot identify the observed function');
const compiled = ts.transpileModule(fragment, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const context = { exports: {} }; vm.runInNewContext(compiled, context);
const signature = context.exports.signature;
const base = JSON.parse(fs.readFileSync(path.join(__dirname, 'unload-rows.json'), 'utf8')).instance;
const changes = {
  service_time: d => { d.tasks[0].service_s += 30; },
  second_depot: d => { d.depots.push([55, 25]); },
  unload_point: d => { d.unload_points[0] = [35, 15]; },
  corridor: d => { d.corridors.push({id:'test', polygon:[[10,10],[20,10],[20,15],[10,15]]}); },
  fleet_class: d => { d.vehicles.fleet = [{count:1,capacity:16,speed_mps:.8,robot_radius:.5,min_turn_radius_m:0}]; },
};
const result = Object.entries(changes).map(([field, change]) => {
  const d = structuredClone(base); change(d);
  return { field, expected_signature_changed: true, actual_signature_changed: signature(d) !== signature(base) };
});
fs.writeFileSync(path.join(out, 'frontend-signature.json'), JSON.stringify({method:'unmodified source function transpiled in isolation',result}, null, 2)+'\n');
console.log(JSON.stringify(result));
