"""Frozen, opt-in execution clocks. No ROS dependency; cleanup uses wall time.

This policy covers approach plus every route leg, never startup or shutdown.
Simulation mode must name its finite wall watchdog; no RTF is assumed.
"""
from __future__ import annotations

import copy
import math

MAX_BUDGET_S = 1800.0
MAX_WALL_WATCHDOG_S = 7200.0
FINALIZE_WALL_S = 90.0  # cancel ack/result, fallback cancellation, settle, independent check
REQUIRED_STREAMS = ('clock', 'scan', 'odom', 'ground_truth')


def bounded_seconds(value, name, maximum):
    if type(value) not in (int, float) or not 0 < value <= maximum or not math.isfinite(value):
        raise ValueError(f'{name} must be finite and in (0, {maximum:g}] seconds')
    return float(value)


def resolve_budget_policy(planner_budget_s, *, budget_s=None, time_basis=None, wall_watchdog_s=None):
    """Reject invalid requests instead of silently changing their meaning."""
    planned = bounded_seconds(planner_budget_s, 'planner budget_s', MAX_BUDGET_S)
    basis = 'wall' if time_basis is None else time_basis
    if basis not in ('wall', 'simulation'):
        raise ValueError('time_basis must be wall or simulation')
    budget = planned if budget_s is None else bounded_seconds(budget_s, 'budget_s', MAX_BUDGET_S)
    if basis == 'simulation':
        watchdog = bounded_seconds(wall_watchdog_s, 'simulation wall_watchdog_s', MAX_WALL_WATCHDOG_S)
    else:
        if wall_watchdog_s is not None and bounded_seconds(wall_watchdog_s, 'wall_watchdog_s', MAX_WALL_WATCHDOG_S) != budget:
            raise ValueError('wall time_basis uses budget_s as its wall watchdog; do not specify a different watchdog')
        watchdog = budget
    return {
        'policy': 'execution_budget_v1',
        'planner_budget_s': planned,
        'planner_formula': 'path_length_over_0.10mps_plus_60s_clamped_90_1800_v1',
        'requested': {'budget_s': budget_s, 'time_basis': time_basis, 'wall_watchdog_s': wall_watchdog_s},
        'effective': {'budget_s': budget, 'time_basis': basis, 'wall_watchdog_s': watchdog,
                      'clock_no_progress_wall_s': 30.0, 'telemetry_stale_wall_s': 3.0,
                      'scope': 'shared_approach_and_all_legs',
                      'navigate_wall_cap_s': 90.0 if basis == 'wall' else None,
                      'required_streams': list(REQUIRED_STREAMS)},
        'budget_provenance': 'planner' if budget_s is None else 'explicit',
    }


def freeze_plan_budget(plan, **requested):
    result = copy.deepcopy(plan)
    policy = resolve_budget_policy(plan['budget_s'], **requested)
    result.update(budget_policy=policy, **{k: policy['effective'][k]
                                         for k in ('budget_s', 'time_basis', 'wall_watchdog_s')})
    return result


def validate_plan_budget(plan):
    """Revalidate frozen gateway metadata at the session boundary; support legacy plans."""
    policy = plan.get('budget_policy')
    if policy is None:
        return freeze_plan_budget(plan, time_basis=plan.get('time_basis'), wall_watchdog_s=plan.get('wall_watchdog_s'))
    if not isinstance(policy, dict) or not isinstance(policy.get('requested'), dict):
        raise ValueError('invalid frozen budget_policy')
    expected = resolve_budget_policy(policy.get('planner_budget_s'), **policy['requested'])
    if policy != expected or any(plan.get(k) != expected['effective'][k]
                                 for k in ('budget_s', 'time_basis', 'wall_watchdog_s')):
        raise ValueError('frozen budget_policy does not match execution request')
    return copy.deepcopy(plan)


def budget_metadata(plan):
    return copy.deepcopy({k: plan[k] for k in ('budget_s', 'time_basis', 'wall_watchdog_s', 'budget_policy')})


def execution_poll_wall_s(run):
    """Polling is a wall envelope, never a reinterpretation of simulated seconds."""
    policy = run.get('budget_policy')
    if not isinstance(policy, dict):
        raise ValueError('execution response is missing frozen budget_policy')
    effective = policy.get('effective', {})
    watchdog = bounded_seconds(effective.get('wall_watchdog_s'), 'wall_watchdog_s', MAX_WALL_WATCHDOG_S)
    return watchdog + FINALIZE_WALL_S


class ExecutionTiming:
    """One immutable policy and origin shared by approach and all actions.

    observe() reports a pending-action trigger. Result processing does not invent
    a timeout retrospectively. check() gates the next action before submission.
    """
    def __init__(self, policy, wall, sim):
        self.policy = copy.deepcopy(policy)
        self.effective = self.policy['effective']
        self.start_wall = wall
        self.start_sim = self.safe_sim(sim)
        self.last_sim = self.start_sim
        self.last_progress_wall = wall
        self.data = {'policy': self.policy['policy'], 'start_wall_monotonic_s': wall,
                     'start_sim_s': self.start_sim, 'samples': 0, 'trigger': None,
                     'max_stream_gap_wall_s': {key: 0.0 for key in REQUIRED_STREAMS},
                     'max_no_progress_wall_s': 0.0}

    @staticmethod
    def safe_sim(value):
        try:
            return float(value) if type(value) in (int, float) and math.isfinite(value) else None
        except OverflowError:
            return None

    def elapsed_sim(self, sim):
        sim = self.safe_sim(sim)
        elapsed = sim - self.start_sim if sim is not None and self.start_sim is not None else None
        return self.safe_sim(elapsed)

    def observe(self, wall, sim, at, *, deadlines=True):
        if self.data['trigger'] is not None:
            return self.data['trigger']
        sim = self.safe_sim(sim)
        self.data.update(last_wall_monotonic_s=wall, last_sim_s=sim,
                         elapsed_wall_s=wall-self.start_wall, elapsed_sim_s=self.elapsed_sim(sim))
        self.data['samples'] += 1
        # Keep the established wall-default behavior: clock integrity is an
        # explicit simulation-mode requirement, not an implicit mode switch.
        if self.effective['time_basis'] == 'simulation':
            if 'clock' not in at:
                return 'clock_missing'
            if sim is None or self.start_sim is None or self.elapsed_sim(sim) is None:
                return 'clock_invalid'
            if sim < self.last_sim:
                return 'clock_backwards'
            if sim > self.last_sim:
                self.last_progress_wall = wall
            self.last_sim = sim
            idle = wall-self.last_progress_wall
            self.data['max_no_progress_wall_s'] = max(self.data['max_no_progress_wall_s'], idle)
            if idle >= self.effective['clock_no_progress_wall_s']:
                return 'clock_no_progress'
        for key in REQUIRED_STREAMS:
            arrived = at.get(key)
            if type(arrived) not in (int, float) or not math.isfinite(arrived):
                return 'stream_missing:'+key
            gap = wall-arrived
            if gap < 0:
                return 'stream_timestamp_invalid:'+key
            self.data['max_stream_gap_wall_s'][key] = max(self.data['max_stream_gap_wall_s'][key], gap)
            if gap > self.effective['telemetry_stale_wall_s']:
                return 'stream_stale:'+key
        if not deadlines:
            return None
        if self.effective['time_basis'] == 'simulation':
            if sim-self.start_sim >= self.effective['budget_s']:
                return 'simulation_budget'
            if wall-self.start_wall >= self.effective['wall_watchdog_s']:
                return 'wall_watchdog'
        elif wall-self.start_wall >= self.effective['budget_s']:
            return 'budget'
        return None

    def trigger(self, reason, wall, sim):
        if self.data['trigger'] is None:
            self.data.update(trigger=reason, trigger_wall_monotonic_s=wall,
                             trigger_sim_s=self.safe_sim(sim), trigger_elapsed_wall_s=wall-self.start_wall,
                             trigger_elapsed_sim_s=self.elapsed_sim(sim))

    def check(self, wall, sim, at):
        reason = self.observe(wall, sim, at)
        if reason is not None:
            self.trigger(reason, wall, sim)
            raise TimeoutError('execution timing guard: '+reason)

    def finish(self, wall, sim, state):
        self.data.update(finished_wall_monotonic_s=wall, finished_sim_s=self.safe_sim(sim),
                         total_elapsed_wall_s=wall-self.start_wall, total_elapsed_sim_s=self.elapsed_sim(sim),
                         terminal_state=state)
