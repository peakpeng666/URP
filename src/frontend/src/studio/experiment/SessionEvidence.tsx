import { fmt } from '../../lab/api';
import type { SimResult } from './replay';
import s from '../panels/panels.module.css';

const evidenceState = (valid: boolean | undefined) => valid === true ? '通过' : valid === false ? '失败' : '未知';

export function SessionEvidence({ result }: { result: SimResult }) {
  const dynamics = result.check?.dynamics;
  const vehicles = dynamics?.vehicles ?? [];
  const gaps = vehicles.map((item) => item.max_truth_gap_s).filter((value): value is number => typeof value === 'number');
  const finalDrift = vehicles.map((item) => item.odom_position_final_m).filter((value): value is number => typeof value === 'number');
  const maxDrift = vehicles.map((item) => item.odom_position_max_m).filter((value): value is number => typeof value === 'number');
  const runtimeLibraries = (result.physics_runtime?.loaded_library_sha256 ?? {}) as Record<string, string>;
  return (
    <section className={s.sessionEvidence} aria-label="逐会话物理证据">
      <div className={s.kv}>
        <span>物理模型</span><b>{result.physics?.schema ?? '历史记录未提供'}</b>
        <span>配置 / 运行核验</span><b>{evidenceState(result.physics_audit?.valid)} / {evidenceState(result.physics_runtime?.valid)}</b>
        <span>源时间</span><b>{result.truth_timing?.scope ?? '历史记录未提供源时间证据'}</b>
        <span>采样质量</span><b>{gaps.length ? `最大真值间隔 ${fmt.num(Math.max(...gaps), 3)} s；动力学检查 ${evidenceState(dynamics?.valid)}` : '未知（不能按连续时间安全证明处理）'}</b>
        <span>轮式里程计漂移</span><b>{finalDrift.length ? `末端最大 ${fmt.num(Math.max(...finalDrift), 3)} m${maxDrift.length ? ` · 全轨迹最大 ${fmt.num(Math.max(...maxDrift), 3)} m` : ''}；只在首个共同姿态对齐` : '历史记录未提供'}</b>
      </div>
      <p className={s.hint}>平地刚体、轮胎接触、理想关节速度伺服与真值定位；不代表真实土壤 / 轮胎校准。B4：后端 valid 不扩大为未知遥测区间的连续时间物理安全证明。</p>
      {result.energy && <p className={s.hint}><strong className={s.warn}>B5：</strong>energy 仅为后验纵向运动学代理，停车尾段可改变估值；不用于能效排行榜。</p>}
      <details>
        <summary>详细物理证据、假设与关闭报告</summary>
        <div className={s.kv}>
          <span>physics_audit</span><b>{result.physics_audit?.errors?.join('；') || result.physics_audit?.scope || '未记录'}</b>
          <span>physics_runtime</span><b>{result.physics_runtime?.errors?.join('；') || result.physics_runtime?.scope || '未记录'} · {Object.keys(runtimeLibraries).length} 个已映射库带哈希</b>
          <span>关闭报告</span><b>整体 {result.session_report?.status ?? '未记录'} · 清理 {result.session_report?.cleanup_status ?? '未记录'} · 执行 {result.session_report?.execution_state ?? result.state}</b>
        </div>
        {result.physics?.assumptions && <ul>{Object.entries(result.physics.assumptions).map(([key, value]) => <li key={key} className={s.hint}><b>{key}</b>：{value}</li>)}</ul>}
      </details>
    </section>
  );
}
