"""Solve queue: every algorithm run is an isolated `python -m urp_lab.worker` subprocess with a wall budget."""
from __future__ import annotations

import hashlib
import copy
import importlib.metadata
import json
import logging
import math
import os
import queue
import secrets
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import paths
from .events import EventBus, utc_now
from .store import Store

log = logging.getLogger('urp_lab.jobs')

GRACE_S = 2.0
DEFAULT_TIME_LIMIT_S = 60.0
LOG_TAIL_BYTES = 4096
FINAL = ('done', 'error', 'timeout', 'canceled')
_RESULT_KEYS = ('status', 'objective', 'routes', 'check', 'map_check', 'raw_result')


def new_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{secrets.token_hex(3)}"


def instance_sha256(instance: dict) -> str:
    canonical = json.dumps(instance, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


def default_concurrency() -> int:
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 4)
    return max(1, min(6, cpus // 4))


def resolve_params(algorithm: dict, given: dict | None) -> dict:
    """Catalog defaults + caller values; rejects unknown names and out-of-range numbers (ValueError, 中文)."""
    given = dict(given or {})
    spec = {p['name']: p for p in algorithm.get('params') or []}
    unknown = sorted(set(given) - set(spec))
    if unknown:
        raise ValueError(f"算法 {algorithm['id']} 没有参数：{', '.join(unknown)}")
    out = {}
    for name, p in spec.items():
        value = given.get(name, p.get('default'))
        kind = p.get('type')
        if value is None:
            out[name] = None
            continue
        if kind in ('number', 'integer'):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    raise ValueError(f"参数 {name} 应为数值") from None
            if kind == 'integer':
                if not math.isfinite(float(value)):
                    raise ValueError(f'参数 {name} 必须为有限数值')
                if float(value) != int(value):
                    raise ValueError(f"参数 {name} 应为整数")
                value = int(value)
            if not math.isfinite(float(value)):
                raise ValueError(f'参数 {name} 必须为有限数值')
            if p.get('min') is not None and value < p['min'] or p.get('max') is not None and value > p['max']:
                raise ValueError(f"参数 {name}={value} 超出范围 [{p.get('min')}, {p.get('max')}]")
        elif kind == 'boolean' and not isinstance(value, bool):
            raise ValueError(f"参数 {name} 应为布尔值")
        elif kind == 'select' and p.get('options') and value not in [o['value'] for o in p['options']]:
            raise ValueError(f"参数 {name} 取值 {value!r} 不在可选项中")
        out[name] = value
    return out


def wall_budget(params: dict, algorithm: dict, grace_s: float) -> float:
    limit = params.get('time_limit_s')
    if limit is None:
        limit = next((p.get('default') for p in algorithm.get('params') or [] if p['name'] == 'time_limit_s'), None)
    return float(limit if limit is not None else DEFAULT_TIME_LIMIT_S) + grace_s


def skeleton(job_id: str, scenario: dict, instance: dict, algorithm: dict, params: dict, label: str | None) -> dict:
    from .recommend import recommend
    advice=recommend(scenario,instance)
    frame = scenario.get('frame') or {}
    cost_unit = scenario.get('cost_unit')
    return {
        'run_id': new_id('run'), 'job_id': job_id, 'scenario_id': scenario['id'],
        'problem_class': scenario['problem_class'], 'instance_sha256': instance_sha256(instance),
        'frame': copy.deepcopy(frame), 'cost_unit': cost_unit, 'instance': copy.deepcopy(instance), 'scenario_snapshot': copy.deepcopy(scenario),
        'reproducibility': {
            'python': sys.version, 'packages': {name: importlib.metadata.version(name) for name in ('pyvrp','ortools','numpy','scipy','shapely')},
            'source_sha256': {paths.rel(p): hashlib.sha256(p.read_bytes()).hexdigest() for folder in (paths.LAB/'urp_lab',paths.RESEARCH_SRC/'urp_research/turn_modes') for p in folder.rglob('*.py')},
            'stopping_rule': '墙钟上限；固定种子不保证不同硬件/负载下得到逐位相同的元启发式结果',
            'seed_usage': 'PyVRP 使用 seed；精确 DP/Oracle 与覆盖排序无随机性；当前 OR-Tools GLS 无随机种子设置',
        },
        'algorithm': {'id': algorithm['id'], 'name': algorithm.get('name'), 'source': algorithm.get('source'),
                      'origin': algorithm.get('origin'), 'version': algorithm.get('version')},
        'params': params, 'state': 'queued', 'status': None,
        'recommendation_at_submission':dict(advice=advice,submitted_algorithm=algorithm['id'],
            budget_matches_learned_profile=advice['policy']!='knn-crc-local-v1' or params.get('time_limit_s')==.25,
            note='提交时的建议快照；实际算法选择与预算以 algorithm / params 为准，不据此推断用户接受了建议'),
        'objective': {'value': None, 'unit': cost_unit, 'lower_bound': None},
        'routes': [], 'check': None, 'map_check': None,
        'metrics': {'cost': None, 'length': None, 'length_unit': 'm' if frame.get('kind') == 'map' else 'unitless',
                    'n_routes': None, 'n_tasks': None, 'turns': None, 'turn_penalty_total': None,
                    'forbidden_turn_violations': None, 'wall_s': None, 'cpu_s': None},
        'log': None, 'error': None, 'created_utc': utc_now(), 'finished_utc': None, 'label': label,
    }


def _tail(data: bytes, limit: int = LOG_TAIL_BYTES) -> str:
    if len(data) > limit:
        data = data[-limit:]
        data = data[data.find(b'\n') + 1:] if b'\n' in data else data
    return data.decode('utf-8', 'replace')


def parse_worker_output(stdout: bytes) -> dict | None:
    text = stdout.decode('utf-8', 'replace').strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):  # tolerate library chatter before the JSON line
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def kill_group(proc: subprocess.Popen, term_wait: float = 2.0):
    for sig, wait in ((signal.SIGTERM, term_wait), (signal.SIGKILL, 5.0)):
        if proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(wait)
        except subprocess.TimeoutExpired:
            pass


def worker_env() -> dict:
    env = dict(os.environ)
    threads = {k: '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}
    extra = [str(paths.LAB), str(paths.RESEARCH_SRC)]
    if env.get('PYTHONPATH'):
        extra.append(env['PYTHONPATH'])
    env.update(threads, PYTHONPATH=os.pathsep.join(extra), PYTHONUNBUFFERED='1')
    return env


def worker_command() -> list[str]:
    python = paths.LAB / '.venv' / 'bin' / 'python'
    return [str(python if python.exists() else Path(sys.executable)), '-m', 'urp_lab.worker']


class JobManager:
    def __init__(self, store: Store, bus: EventBus | None = None, *, concurrency: int | None = None,
                 grace_s: float = GRACE_S, command: list[str] | None = None, recover: bool = True):
        self.store, self.bus = store, bus
        self.grace_s = grace_s
        self.command = command or worker_command()
        self.concurrency = concurrency or default_concurrency()
        self._queue: queue.Queue = queue.Queue()
        self._procs: dict[str, subprocess.Popen] = {}
        self._pending: dict[str, tuple[dict, dict]] = {}
        self._canceled: set[str] = set()
        self._lock = threading.Lock()
        self._stopping = False
        self._threads: list[threading.Thread] = []
        if recover:
            self._recover()

    def _recover(self):
        for sol in self.store.active_runs():
            sol.update(state='error', finished_utc=utc_now(),
                       error='网关在此运行结束前退出（上一次网关进程），没有产生结果；请重新求解。')
            self.store.put_run(sol)

    def start(self):
        for i in range(self.concurrency):
            t = threading.Thread(target=self._loop, name=f'urp-job-{i}', daemon=True)
            t.start()
            self._threads.append(t)

    def _emit(self, sol: dict):
        if self.bus:
            self.bus.publish('job', {'job_id': sol['job_id'], 'run_id': sol['run_id'], 'state': sol['state']})
            if sol['state'] in FINAL:
                self.bus.publish('run', sol)

    def _save(self, sol: dict):
        self.store.put_run(sol)
        self._emit(sol)

    def submit(self, scenario: dict, instance: dict, algorithms: list[tuple[dict, dict]],
               label: str | None = None) -> tuple[str, list[str]]:
        """algorithms: [(catalog entry, resolved params)]. Returns (job_id, run_ids)."""
        if self._stopping:
            raise RuntimeError('网关正在退出，不再接受求解任务')
        job_id = new_id('job')
        run_ids = []
        for algorithm, params in algorithms:
            sol = skeleton(job_id, scenario, instance, algorithm, params, label)
            request = {'run_id': sol['run_id'], 'scenario': scenario, 'instance': instance,
                       'algorithm_id': algorithm['id'], 'params': params}
            self._save(sol)
            with self._lock:
                self._pending[sol['run_id']] = (sol, request)
            self._queue.put((sol, request, wall_budget(params, algorithm, self.grace_s)))
            run_ids.append(sol['run_id'])
        log.info('job %s: %s', job_id, ', '.join(a['id'] for a, _ in algorithms))
        return job_id, run_ids

    def _loop(self):
        while True:
            item = self._queue.get()
            if item is None:
                return
            sol, request, budget = item
            with self._lock:
                self._pending.pop(sol['run_id'], None)
                skip = sol['run_id'] in self._canceled or self._stopping
            if skip:
                continue
            try:
                self.execute(sol, request, budget)
            except Exception as exc:  # never lose a run silently
                log.exception('run %s failed in gateway', sol['run_id'])
                sol.update(state='error', error=f'网关执行异常：{exc}', finished_utc=utc_now())
                self._save(sol)

    def execute(self, sol: dict, request: dict, budget: float) -> dict:
        sol['state'] = 'running'
        self._save(sol)
        t0 = time.monotonic()
        try:
            proc = subprocess.Popen(self.command, cwd=paths.LAB, env=worker_env(), stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        except OSError as exc:
            sol.update(state='error', error=f'无法启动求解工作进程：{exc}', finished_utc=utc_now())
            self._save(sol)
            return sol
        with self._lock:
            self._procs[sol['run_id']] = proc
            canceled_before_spawn = sol['run_id'] in self._canceled or self._stopping
        if canceled_before_spawn:
            kill_group(proc, term_wait=1.0)
        timed_out = False
        try:
            out, err = proc.communicate(json.dumps(request, ensure_ascii=False).encode(), timeout=budget)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_group(proc)
            out, err = proc.communicate()
        finally:
            with self._lock:
                self._procs.pop(sol['run_id'], None)
        wall = round(time.monotonic() - t0, 3)
        evidence = self.store.path.parent / 'runs' / sol['run_id']
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / 'request.json').write_text(json.dumps(request, ensure_ascii=False, indent=2))
        (evidence / 'stdout.json').write_bytes(out)
        (evidence / 'stderr.log').write_bytes(err)
        sol['process'] = {'returncode': proc.returncode, 'budget_s': budget, 'evidence': str(evidence)}
        self._finish(sol, proc.returncode, out, err, wall, budget, timed_out)
        self._save(sol)
        return sol

    def _finish(self, sol, returncode, out, err, wall, budget, timed_out):
        notes = []
        sol['finished_utc'] = utc_now()
        sol['metrics']['process_wall_s'] = wall
        with self._lock:
            canceled = sol['run_id'] in self._canceled
        result = None if (timed_out or canceled) else parse_worker_output(out)
        if canceled:
            sol.update(state='canceled', error='已取消（求解进程组已终止）' if not self._stopping else '网关退出时中止')
        elif timed_out:
            sol.update(state='timeout', error=f'超过墙钟预算 {budget:g} s（时间上限 + {self.grace_s:g} s 余量），已终止进程组')
        elif result is None:
            sol.update(state='error', error=f'工作进程未返回 JSON 结果（返回码 {returncode}）')
        elif result.get('error'):
            sol.update(state='timeout' if result.get('error_kind')=='timeout' else 'error', error=str(result['error']))
        elif returncode != 0:
            sol.update(state='error', error=f'工作进程返回码 {returncode}，即使输出了 JSON 也不能判成功')
        else:
            sol['state'] = 'done'
        if result:
            for key in _RESULT_KEYS:
                if key in result:
                    sol[key] = result[key]
            if isinstance(result.get('metrics'), dict):
                sol['metrics'].update(result['metrics'])
                sol['metrics']['process_wall_s'] = wall
            if isinstance(result.get('algorithm'), dict):
                sol['algorithm'].update({k: v for k, v in result['algorithm'].items() if v is not None})
            if sol.get('routes') is None:
                sol['routes'] = []
            if sol.get('status') in ('infeasible', 'no_solution') and sol['routes']:
                notes.append(f"[网关] 状态为 {sol['status']}，按契约不保留 {len(sol['routes'])} 条路线")
                sol['routes'] = []
            if sol.get('status') in ('infeasible', 'no_solution') and isinstance(sol.get('objective'), dict):
                sol['objective']['value'] = None
        if sol['state'] != 'done':
            sol['routes'] = []
        if sol['metrics'].get('wall_s') is None and sol['state'] == 'done':
            sol['metrics']['wall_s'] = wall
        text = _tail(err or b'')
        if notes:
            text = (text + '\n' if text else '') + '\n'.join(notes)
        sol['log'] = text or None

    def cancel(self, run_id: str) -> dict | None:
        sol = self.store.get_run(run_id)
        if sol is None or sol['state'] in FINAL:
            return sol
        with self._lock:
            self._canceled.add(run_id)
            proc = self._procs.get(run_id)
            pending = self._pending.pop(run_id, None)
        if proc is not None:
            kill_group(proc, term_wait=1.0)  # execute() records the canceled state
            return self.store.get_run(run_id)
        if pending:
            sol = pending[0]
            sol.update(state='canceled', error='已在排队时取消', finished_utc=utc_now())
            self._save(sol)
        return sol

    def active(self) -> dict:
        with self._lock:
            return {'running': len(self._procs), 'queued': len(self._pending), 'concurrency': self.concurrency}

    def shutdown(self):
        self._stopping = True
        with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
            procs = dict(self._procs)
            self._canceled.update(procs)
        for sol, _ in pending:
            sol.update(state='canceled', error='网关退出，排队中的运行未执行', finished_utc=utc_now())
            self._save(sol)
        for proc in procs.values():
            kill_group(proc, term_wait=1.0)
        for _ in self._threads:
            self._queue.put(None)
        for t in self._threads:
            t.join(timeout=10)
