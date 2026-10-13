"""Independent feasibility checks and descriptive lower-bound aggregation.

This module uses only the standard library. It does not call or import a
controller, packing policy, candidate, or oracle. An assignment is a list in
the original item order; all ``n`` preallocated bin IDs are legal, even before
smaller IDs have appeared. Feasibility alone does not certify an online policy.

The paper-facing excess uses the volume lower bound L1, not the stronger
diagnostic bound and not an assumed optimum. Empty microinputs are checkable,
but cannot contribute a zero denominator to benchmark aggregation.
"""

from fractions import Fraction


MAX_ITEMS = 10_000
RECORDS_PER_GROUP = 5


class ValidationError(ValueError):
    """An input, claimed packing, or aggregation group is invalid."""


def _integer(value, name, minimum, maximum=None):
    if type(value) is not int:
        raise ValidationError(f"{name} must be an exact int (not bool or float)")
    if value < minimum or (maximum is not None and value > maximum):
        upper = "" if maximum is None else f"..{maximum}"
        raise ValidationError(f"{name} is outside {minimum}{upper}")
    return value


def _list(value, name):
    if type(value) is not list:
        raise ValidationError(f"{name} must be a list")
    return value


def check_assignment(items, capacity, assignment, claimed_used_bins, residuals=None):
    """Check a packing against original items and return independently derived data.

    ``items`` and ``assignment`` must be lists of equal length, at most 10,000.
    Every item is an exact int in 1..capacity. Every bin ID is an exact int in
    0..n-1. ``claimed_used_bins`` counts nonempty bins, not the largest ID plus
    one. Optional ``residuals`` must give all n residual capacities, including
    empty and exactly full bins. None of the caller's lists are modified.

    The returned ``per_instance_excess`` is (used_bins - L1) / L1, or None for
    empty input. It is excess relative to a lower bound, not an optimality gap.
    All validation failures raise ValidationError.
    """
    _integer(capacity, "capacity", 1)
    _list(items, "items")
    n = len(items)
    _integer(n, "number of items", 0, MAX_ITEMS)
    _list(assignment, "assignment")
    if len(assignment) != n:
        raise ValidationError("assignment must have exactly one bin ID per item")
    _integer(claimed_used_bins, "claimed_used_bins", 0, n)
    if residuals is not None:
        _list(residuals, "residuals")
        if len(residuals) != n:
            raise ValidationError("residuals must contain all n preallocated bins")
        for index, residual in enumerate(residuals):
            _integer(residual, f"residuals[{index}]", 0, capacity)

    loads = [0] * n
    total_size = 0
    large_item_count = 0
    # The original sequence is zipped directly with its assignment: no sorting,
    # renumbering, filtering, or controller-provided loads enter this calculation.
    for index, (item, bin_id) in enumerate(zip(items, assignment)):
        _integer(item, f"items[{index}]", 1, capacity)
        _integer(bin_id, f"assignment[{index}]", 0, n - 1)
        loads[bin_id] += item
        if loads[bin_id] > capacity:
            raise ValidationError(f"bin {bin_id} exceeds capacity at item {index}")
        total_size += item
        large_item_count += 2 * item > capacity

    used_bins = sum(load > 0 for load in loads)
    if claimed_used_bins != used_bins:
        raise ValidationError("claimed_used_bins disagrees with nonempty-bin count")
    computed_residuals = [capacity - load for load in loads]
    if residuals is not None and residuals != computed_residuals:
        raise ValidationError("claimed residuals disagree with independent loads")

    l1 = (total_size + capacity - 1) // capacity
    excess_bins = used_bins - l1
    return {
        "n": n,
        "capacity": capacity,
        "used_bins": used_bins,
        "total_size": total_size,
        "L1": l1,
        "large_item_count": large_item_count,
        "diagnostic_lower_bound": max(l1, large_item_count),
        "excess_bins": excess_bins,
        "per_instance_excess": excess_bins / l1 if l1 else None,
        "loads": loads,
        "residuals": computed_residuals,
    }


def aggregate_records(records):
    """Aggregate checked-result dicts, each augmented with a ``method`` string.

    Group by (n, capacity, method), requiring exactly five records in EVERY
    group. Failed/missing instances must not be silently omitted or averaged
    over a smaller denominator. The caller supplies records from independent
    checks; summary fields are not a substitute for checking the raw packing.

    Primary excess is (sum(used_bins) - sum(L1)) / sum(L1). The separately
    reported mean per-instance excess is mean((used_bins - L1) / L1).
    Ratios are accumulated exactly before final conversion to JSON-friendly
    floats. Precomputed excess fields in records are intentionally ignored.
    Groups are returned in deterministic sorted order.
    """
    _list(records, "records")
    if not records:
        raise ValidationError("at least one five-record group is required")

    groups = {}
    required = ("n", "capacity", "method", "used_bins", "L1")
    for index, record in enumerate(records):
        if type(record) is not dict:
            raise ValidationError(f"records[{index}] must be a dict")
        missing = [key for key in required if key not in record]
        if missing:
            raise ValidationError(f"records[{index}] is missing {', '.join(missing)}")
        n = _integer(record["n"], f"records[{index}].n", 1, MAX_ITEMS)
        capacity = _integer(record["capacity"], f"records[{index}].capacity", 1)
        used = _integer(record["used_bins"], f"records[{index}].used_bins", 1, n)
        l1 = _integer(record["L1"], f"records[{index}].L1", 1, n)
        if used < l1:
            raise ValidationError(f"records[{index}].used_bins is below L1")
        method = record["method"]
        if type(method) is not str or not method.strip():
            raise ValidationError(f"records[{index}].method must be a nonempty string")
        groups.setdefault((n, capacity, method), []).append((used, l1))

    result = []
    for (n, capacity, method), values in sorted(groups.items()):
        if len(values) != RECORDS_PER_GROUP:
            raise ValidationError(
                f"group {(n, capacity, method)!r} must contain exactly "
                f"{RECORDS_PER_GROUP} records; got {len(values)}"
            )
        sum_used = sum(used for used, _ in values)
        sum_l1 = sum(l1 for _, l1 in values)
        mean_excess = sum((Fraction(used - l1, l1) for used, l1 in values), Fraction())
        result.append({
            "n": n,
            "capacity": capacity,
            "method": method,
            "record_count": len(values),
            "sum_used_bins": sum_used,
            "sum_L1": sum_l1,
            "mean_used_bins": sum_used / len(values),
            "mean_L1": sum_l1 / len(values),
            "primary_excess": float(Fraction(sum_used - sum_l1, sum_l1)),
            "mean_per_instance_excess": float(mean_excess / len(values)),
        })
    return result
