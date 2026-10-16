"""Optional Fields2Cover swath ordering + Dubins connectors, checked with Shapely.

Do not use Path.discretize(): it interpolates/smooths, which changes the route.
Retain native turn samples and densify only straight swaths.
"""
import hashlib
import importlib.util
import importlib.metadata
import json
import math
import time
from functools import lru_cache
from pathlib import Path

STEP = .02

@lru_cache(maxsize=1)
def available():
    spec = importlib.util.find_spec('fields2cover')
    if spec is None:
        return dict(available=False, version=None, reason='可选 Fields2Cover 绑定未安装；可使用平行往复基线')
    root = Path(spec.origin).parent
    binary = root / '_fields2cover_python.so'
    if not binary.is_file():
        return dict(available=False, version=None, reason='Fields2Cover 原生扩展缺失')
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    manifest_path=Path(__file__).resolve().parents[2]/'vendor/fields2cover-manifest.json'
    try:
        manifest=json.loads(manifest_path.read_text())
        if digest!=manifest['binary_sha256'] or importlib.metadata.version('fields2cover')!=manifest['version']:
            return dict(available=False,version=None,reason='Fields2Cover 版本/二进制指纹与已验收 wheel 不一致，请重新验收')
    except (OSError,ValueError,KeyError,importlib.metadata.PackageNotFoundError):
        return dict(available=False,version=None,reason='Fields2Cover 可复现清单缺失或损坏')
    return dict(available=True, version=manifest['version'], reason=None,binary_sha256=digest,wheel_sha256=manifest['wheel_sha256'])


def check_path(instance, points, swaths):
    """Independent geometry, coverage and sampled-curvature check of exported coordinates."""
    from shapely.geometry import Polygon, LineString
    from shapely.ops import unary_union
    area = Polygon(instance['field'], instance.get('obstacles', []))
    interior = area.buffer(-instance['headland_width'])
    errors = []
    if len(points) < 2 or not all(math.isfinite(v) for p in points for v in p):
        return dict(valid=False, errors=['没有有限的可执行路径']), {}
    line = LineString(points)
    # Chord sagitta bound for circular arcs at this sampling resolution.
    margin = STEP * STEP / (8 * instance['turn_radius']) + 1e-6
    if not area.covers(line.buffer(instance['robot_width']/2 + margin)):
        errors.append('路径段及机器人扫掠足迹越出田块或穿越障碍；增大地头或调整幅宽/转弯半径')
    curvatures = []
    for a, b, c in zip(points, points[1:], points[2:]):
        product = math.dist(a,b)*math.dist(b,c)*math.dist(a,c)
        if product > 1e-12:
            curvatures.append(2*abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/product)
    max_curvature = max(curvatures, default=0.)
    if max_curvature > (1/instance['turn_radius'])*(1+1e-3):
        errors.append('采样三点曲率超过最小转弯半径约束')
    swept = unary_union([LineString(s).buffer(instance['swath_width']/2, cap_style=2) for s in swaths])
    covered = swept.intersection(area).area
    metrics = dict(coverage_area_m2=covered, field_area_m2=area.area,
        coverage_fraction=covered/area.area, working_area_m2=interior.area,
        working_area_fraction=swept.intersection(interior).area/interior.area if interior.area else 0,
        turn_radius_enforced=not errors, max_sampled_curvature_per_m=max_curvature,
        min_turn_radius_m=instance['turn_radius'], curvature_relative_tolerance=1e-3,
        geometry_sampling_m=STEP, footprint_sampling_margin_m=margin,
        coverage_scope='仅内缩作业区；地头转弯不计作业面积；Dubins 曲线离散几何检查')
    return dict(valid=not errors, errors=errors, computed_cost=line.length,
        checker='urp_lab.solvers.f2c_coverage:check_path / Shapely footprint + three-point curvature',
        source='panel_baseline'), metrics


def solve(instance, pattern):
    if instance['turn_radius']<=0:raise ValueError('Fields2Cover Dubins 需要大于 0 的最小转弯半径')
    import fields2cover as f2c
    from ..scenarios.maps import densify
    from shapely.geometry import Polygon
    area = Polygon(instance['field'], instance.get('obstacles', []))
    inside = area.buffer(-instance['headland_width'])
    if inside.is_empty or inside.geom_type != 'Polygon' or not inside.equals(inside.convex_hull):
        return [], dict(valid=False,errors=['当前适配器仅支持单个凸内缩作业区；凹田块、孔洞或分离区需先分解']), {}, None
    def ring(points):
        return f2c.LinearRing(f2c.VectorPoint([f2c.Point(*p) for p in points]))
    cell = f2c.Cell(ring(list(inside.exterior.coords)))
    angle = math.radians(instance.get('angle_deg') or 0)
    robot = f2c.Robot(instance['robot_width'], instance['swath_width'])
    robot.setMinTurningRadius(instance['turn_radius'])
    generated = f2c.SG_BruteForce().generateSwaths(angle, instance['swath_width'], cell)
    ordering = f2c.RP_Snake() if pattern == 'snake' else f2c.RP_Boustrophedon()
    ordered = ordering.genSortedSwaths(generated)
    swaths = [[[s.startPoint().getX(),s.startPoint().getY()], [s.endPoint().getX(),s.endPoint().getY()]]
              for s in [ordered.at(i) for i in range(ordered.size())]]
    turner = f2c.PP_DubinsCurves(); turner.setDiscretization(STEP)
    points, legs, raw_turns = [], [], []
    for i, (a,b) in enumerate(swaths):
        leg = [list(p) for p in densify([a,b], STEP)]
        if i+1 < len(swaths):
            c,d = swaths[i+1]
            turn = turner.createTurn(robot, f2c.Point(*b), math.atan2(b[1]-a[1],b[0]-a[0]),
                                    f2c.Point(*c), math.atan2(d[1]-c[1],d[0]-c[0]))
            if not turn.size():
                return [],dict(valid=False,errors=['Fields2Cover 没有返回转弯连接']),{},None
            samples = []
            for j in range(turn.size()):
                state = turn.getState(j)
                if state.dir != f2c.PathDirection_FORWARD:
                    raise ValueError('当前执行适配器不支持倒车曲线')
                p = [state.point.getX(),state.point.getY()]
                samples.append(dict(point=p, heading=state.angle, length=state.len, direction=state.dir))
                if math.dist(leg[-1],p)>1e-8:leg.append(p)
            if math.dist(leg[-1],c)>1e-5:raise ValueError('Fields2Cover 转弯端点不连续')
            raw_turns.append(samples)
        legs.append(leg)
        points.extend(leg if not points else leg[1:])
    check, metrics = check_path(instance, points, swaths)
    raw = dict(swaths=swaths, turn_states=raw_turns, generated_polyline=points,
               binding=available(), ordering=pattern, angle_deg=math.degrees(angle),
               implementation='Fields2Cover SG_BruteForce + RP ordering + PP_DubinsCurves.createTurn; no smoothing')
    routes = [dict(vehicle=0,nodes=None,sequence=[],services=[],polyline=points,
                   execution_legs=legs,cost=check.get('computed_cost'),load=0)] if check['valid'] else []
    return routes,check,metrics,raw


TURN_MODELS = {'dubins': 'PP_DubinsCurves', 'dubins_cc': 'PP_DubinsCurvesCC', 'reeds_shepp': 'PP_ReedsSheppCurves'}
SWATH_OBJECTIVES = {'n_swath': 'OBJ_NSwathModified', 'swath_length': 'OBJ_SwathLength', 'field_coverage': 'OBJ_FieldCoverage'}
DECOMPOSITIONS = {'boustrophedon': 'DECOMP_Boustrophedon', 'trapezoidal': 'DECOMP_TrapezoidalDecomp', 'none': None}
SECTION = {1: 'swath', 2: 'turn', 3: 'headland'}


def solve_full(instance, params):
    """Fields2Cover 2.x end-to-end pipeline for arbitrary (non-convex) fields:
    constant headlands → cell decomposition → best-angle swaths per cell → route across cells via the
    headland ring → path planning with the chosen turn model. Section types split working vs non-working distance."""
    import fields2cover as f2c
    from shapely.geometry import Polygon, LineString
    from shapely.ops import unary_union
    if instance['turn_radius'] <= 0:
        raise ValueError('需要大于 0 的最小转弯半径')
    t0 = time.perf_counter()

    def ring(points):
        pts = list(points) + [points[0]]
        return f2c.LinearRing(f2c.VectorPoint([f2c.Point(float(x), float(y)) for x, y in pts]))
    cell = f2c.Cell(ring(instance['field']))
    for hole in instance.get('obstacles') or []:
        cell.addRing(ring(hole))
    cells = f2c.Cells(cell)
    robot = f2c.Robot(instance['robot_width'], instance['swath_width'])
    robot.setMinTurningRadius(instance['turn_radius'])
    hl = f2c.HG_Const_gen()
    width = instance['headland_width']
    mid_hl = hl.generateHeadlands(cells, width / 2)
    inner = hl.generateHeadlands(cells, width)
    decomposition = params.get('decomposition', 'boustrophedon')
    if DECOMPOSITIONS.get(decomposition):
        decomp = getattr(f2c, DECOMPOSITIONS[decomposition])()
        decomp.setSplitAngle(0.5 * math.pi)
        inner = decomp.decompose(inner)
    objective = getattr(f2c, SWATH_OBJECTIVES[params.get('swath_objective', 'n_swath')])()
    generator = f2c.SG_BruteForce()
    if instance.get('angle_deg') is not None:
        swaths = f2c.SwathsByCells()
        for i in range(inner.size()):
            swaths.push_back(generator.generateSwaths(math.radians(instance['angle_deg']), robot.getCovWidth(), inner.getGeometry(i)))
    else:
        swaths = generator.generateBestSwaths(objective, robot.getCovWidth(), inner)
    route = f2c.RP_RoutePlannerBase().genRoute(mid_hl, swaths)
    turner = getattr(f2c, TURN_MODELS[params.get('turn_model', 'dubins')])()
    path = f2c.PP_PathPlanning().planPath(robot, route, turner)
    elapsed = time.perf_counter() - t0
    if path.size() < 2:
        return [], dict(valid=False, errors=['Fields2Cover 没有生成路径']), {}, None
    states = [path.getState(i) for i in range(path.size())]
    full = [[s.point.getX(), s.point.getY()] for s in states]
    kinds = [SECTION.get(int(s.type), 'other') for s in states]
    # A state's type labels the section that starts at it (a swath is a single state followed by its end point).
    lengths = {'swath': 0.0, 'turn': 0.0, 'headland': 0.0, 'other': 0.0}
    swath_lines = []
    for a, b, k in zip(full, full[1:], kinds):
        lengths[k] += math.dist(a, b)
        if k == 'swath' and math.dist(a, b) > 1e-6:
            swath_lines.append(LineString([a, b]))
    reverse = sum(1 for s in states if s.dir == f2c.PathDirection_BACKWARD)
    field = Polygon(instance['field'], instance.get('obstacles') or [])
    covered = unary_union([s.buffer(instance['swath_width'] / 2, cap_style=2) for s in swath_lines]).intersection(field).area if swath_lines else 0.0
    outside = LineString(full).buffer(instance['robot_width'] / 2).difference(field).area
    step = max(1, len(full) // 6000)
    pts = full[::step] + ([full[-1]] if (len(full) - 1) % step else [])
    total = sum(lengths.values())
    errors = [] if outside < 0.01 * field.area else ['机器人足迹有明显部分越出田块边界']
    check = dict(valid=not errors, errors=errors, computed_cost=total, source='panel_baseline',
                 checker='urp_lab.solvers.f2c_coverage.solve_full · Shapely 足迹与覆盖复算')
    metrics = dict(coverage_area_m2=covered, field_area_m2=field.area, coverage_fraction=covered / field.area if field.area else None,
                   working_length_m=lengths['swath'], turning_length_m=lengths['turn'], headland_length_m=lengths['headland'],
                   non_working_length_m=lengths['turn'] + lengths['headland'] + lengths['other'],
                   efficiency=lengths['swath'] / total if total else None, n_swaths=len(swath_lines), n_cells=inner.size(),
                   reverse_states=reverse, footprint_outside_m2=outside, planning_s=elapsed,
                   coverage_scope='作业行覆盖面积 / 全田块；转弯与地头行驶计为非作业距离')
    raw = dict(implementation='Fields2Cover HG_Const_gen → ' + (DECOMPOSITIONS.get(decomposition) or '不分解') +
               f" → SG_BruteForce({SWATH_OBJECTIVES[params.get('swath_objective', 'n_swath')]}) → RP_RoutePlannerBase → PP_PathPlanning({TURN_MODELS[params.get('turn_model', 'dubins')]})",
               states=len(full), decimation=step, binding=available())
    route_out = dict(vehicle=0, nodes=None, sequence=[], services=[], polyline=pts, cost=total, load=0,
                     sections=[[i // step, k] for i, k in enumerate(kinds) if i == 0 or k != kinds[i - 1]])
    return [route_out], check, metrics, raw

