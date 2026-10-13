import type { Meta } from '../../data/types';
import type { CheckScope, ProvenanceCheck, ProvenanceSource } from '../../app/store';

const FALLBACK = { path: '（未记录）', url: '#/evidence', bytes: 0, sha256: '' };

export function srcRef(meta: Meta, path: string, field?: string, note?: string): ProvenanceSource {
  const ref = meta.sources[path] ?? { ...FALLBACK, path };
  return { ref, field, note };
}

/**
 * Standard verification rows. "historical" = the in-package independent audit
 * (passed when the package was built). "project" = this console's own
 * re-verification. They are always kept distinct so a historical PASS is never
 * presented as this project's acceptance.
 */
export function metaChecks(meta: Meta, scopes: CheckScope[]): ProvenanceCheck[] {
  const out: ProvenanceCheck[] = [];
  const pv = meta.project_validation;
  for (const scope of scopes) {
    if (scope === 'historical') {
      out.push({
        scope,
        status: 'pass',
        label: '独立审计重算全部 768 运行、18 单元与 bootstrap 一致',
        detail: `结论 ${String(meta.historical_audit.scientific_result_status)}`,
      });
    } else if (scope === 'project') {
      out.push({
        scope,
        status: pv.status === 'PASS' ? 'pass' : pv.status === 'FAIL' ? 'fail' : 'pending',
        label:
          pv.status === 'PASS'
            ? '本项目在本机重算计数、哈希、轨迹与汇总一致'
            : pv.status === 'FAIL'
              ? '本项目核验发现不一致，详见证据页'
              : '本项目全量核验进行中',
        detail: pv.generatedAt ? `生成于 ${pv.generatedAt.slice(0, 19).replace('T', ' ')} UTC` : undefined,
      });
    } else {
      out.push({ scope, status: 'none', label: '可在证据页用本浏览器即时重算对照' });
    }
  }
  return out;
}
