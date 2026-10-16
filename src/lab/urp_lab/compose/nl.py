"""Parse a one-sentence Chinese (or simple English) task description into a structured task spec."""
from __future__ import annotations

import math
import re

CN_DIGITS = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
NUM = r'(\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百千]+)'

KINDS = {
    'sampling': ('采样', r'采样|取样|土壤|测土|样本'),
    'inspection': ('巡检', r'巡检|巡查|巡视|检查|监测|查看|拍照'),
    'spraying': ('植保', r'喷洒|喷药|打药|植保|施肥|灌溉'),
    'harvest': ('采收', r'采摘|收获|采收|摘果|收割'),
    'transport': ('运输', r'运输|搬运|转运|配送|投放|运送|送达'),
    'seeding': ('播种', r'播种|补苗|种植'),
}
OBSTACLES = {
    'pond': ('池塘', r'池塘|水塘|鱼塘|水池|湖|水坑'),
    'building': ('建筑', r'建筑|房屋|房子|厂房|库房|机房|泵房|仓房|平房|楼'),
    'greenhouse': ('温室', r'温室|大棚'),
    'tree': ('树木', r'大树|树木|树|电线杆|电杆|杆塔|立柱|柱子'),
    'ditch': ('沟渠', r'水渠|沟渠|水沟|沟|渠'),
    'rock': ('石块', r'石头|岩石|乱石|石块'),
}
DEPOT = {'西南': 'sw', '左下': 'sw', '东南': 'se', '右下': 'se', '西北': 'nw', '左上': 'nw', '东北': 'ne', '右上': 'ne',
         '中间': 'center', '中心': 'center', '正中': 'center', '中央': 'center', '北': 'n', '南': 's', '东': 'e', '西': 'w',
         '上': 'n', '下': 's', '左': 'w', '右': 'e'}


def cn_number(text: str) -> float | None:
    if re.fullmatch(r'\d+(?:\.\d+)?', text):
        return float(text)
    total, section, digit = 0, 0, None
    for ch in text:
        if ch in CN_DIGITS:
            digit = CN_DIGITS[ch]
        elif ch in '十百千':
            unit = {'十': 10, '百': 100, '千': 1000}[ch]
            section += (digit if digit is not None else 1) * unit
            digit = None
        else:
            return None
    total = section + (digit or 0)
    return float(total) if text else None


def _find(pattern: str, text: str):
    m = re.search(pattern, text, re.I)
    if not m:
        return None, None
    nums = [cn_number(g) for g in m.groups() if g is not None and cn_number(g) is not None]
    return nums, m.group(0)


def parse(text: str) -> dict:
    t = (text or '').strip()
    spec, found = {}, []

    def note(key, label, value, snippet):
        spec[key] = value
        found.append({'key': key, 'label': label, 'value': value, 'text': snippet})

    nums, s = _find(NUM + r'\s*(?:米|m)?\s*[×xX*＊乘]\s*' + NUM + r'\s*(?:米|m)', t)
    if nums and len(nums) == 2:
        note('size', '场地', [nums[0], nums[1]], s)
    else:
        nums, s = _find(r'长\s*' + NUM + r'\s*(?:米|m).{0,6}?宽\s*' + NUM + r'\s*(?:米|m)', t)
        if nums and len(nums) == 2:
            note('size', '场地', [nums[0], nums[1]], s)
    if 'size' not in spec:
        nums, s = _find(NUM + r'\s*(公顷|ha|hectares?)', t)
        if nums:
            note('area_m2', '面积', nums[0] * 10000, s)
        else:
            nums, s = _find(NUM + r'\s*亩', t)
            if nums:
                note('area_m2', '面积', nums[0] * 666.67, s)
    nums, s = _find(NUM + r'\s*(?:台|辆|部|架)', t)
    if not nums:
        nums, s = _find(NUM + r'\s*个?\s*(?:机器人|无人车|AGV|小车|robots?|vehicles?)', t)
    if nums:
        note('vehicles', '车辆', int(nums[0]), s)
    nums, s = _find(NUM + r'\s*(?:个|棵|株|颗|处)?\s*(?:采样点|取样点|任务点|点位|巡检点|采摘点|投放点|监测点|作业点|目标点|样点|植株|果树|站点|点|处|tasks?|points?)', t)
    if nums:
        note('tasks', '任务点', int(nums[0]), s)
    nums, s = _find(r'(?:载重|容量|载量|装载量)\s*(?:为|是|都是)?\s*' + NUM, t)
    if not nums:
        nums, s = _find(r'每(?:台|辆|个)?(?:车|机器人)?\s*(?:最多|最大)?\s*(?:能|可)?(?:装|载|带|采|运|服务)\s*' + NUM, t)
    if not nums:
        nums, s = _find(r'(?:capacity|load)\s*(?:of)?\s*' + NUM, t)
    if nums:
        note('capacity', '单车容量', int(nums[0]), s)
    nums, s = _find(r'每个?(?:点|任务点|采样点|样点)\s*(?:需求|重量|需要|装)?\s*' + NUM, t)
    if nums:
        note('demand', '单点需求', int(nums[0]), s)
    nums, s = _find(NUM + r'\s*(?:块|个|片)\s*(?:地块|田块|田|地|果园|菜地|区)', t)
    if not nums:
        nums, s = _find(r'分(?:成|为)\s*' + NUM + r'\s*(?:块|个|片|区)', t)
    if nums:
        note('plots', '地块', int(nums[0]), s)
    obstacles = {}
    for key, (label, words) in OBSTACLES.items():
        # "果树" is usually the work target, not an obstacle.
        scope = re.sub(r'果树', '', t) if key == 'tree' else t
        m = re.search(r'(' + NUM[1:-1] + r')?\s*(?:个|处|座|栋|片|棵|根|条|间|口)?\s*(?:' + words + r')', scope)
        if m and not (key == 'greenhouse' and not re.search(r'避开|绕开|绕过|躲开|障碍|不能进', t)):
            count = cn_number(m.group(1)) if m.group(1) else None
            obstacles[key] = int(count) if count else (6 if key == 'tree' else 1)
            found.append({'key': f'obstacle.{key}', 'label': label, 'value': obstacles[key], 'text': m.group(0)})
    if obstacles:
        spec['obstacles'] = obstacles
    elif re.search(r'没有障碍|无障碍|空旷', t):
        spec['obstacles'] = {}
        found.append({'key': 'obstacles', 'label': '障碍', 'value': 0, 'text': re.search(r'没有障碍|无障碍|空旷', t).group(0)})
    for key, (label, words) in KINDS.items():
        m = re.search(words, t)
        if m:
            note('kind', '作业类型', key, m.group(0))
            break
    m = re.search(r'聚集|成簇|扎堆|集中|几片|一簇|clustered', t)
    if m:
        note('distribution', '分布', 'clustered', m.group(0))
    else:
        m = re.search(r'成行|沿行|沿着?作物行|垄|行间|一排排|rows?', t)
        if m:
            note('distribution', '分布', 'rows', m.group(0))
        else:
            m = re.search(r'均匀|随机|分散|散布|uniform', t)
            if m:
                note('distribution', '分布', 'uniform', m.group(0))
    m = re.search(r'(西南|东南|西北|东北|左下|右下|左上|右上|中间|中心|正中|中央|北|南|东|西)(?:角|侧|边|部|面)?(?:的)?\s*(?:车库|仓库|充电站|基地|出发|机库|停车)', t) or \
        re.search(r'(?:车库|仓库|充电站|基地|机库)(?:在|位于|设在)\s*(西南|东南|西北|东北|左下|右下|左上|右上|中间|中心|正中|中央|北|南|东|西)', t)
    if m:
        note('depot', '车库', DEPOT[m.group(1)], m.group(0))
    m = re.search(r'均衡|平均分配|同时完成|尽快完成|最快完成|完成时间|时间最短|最早完成|最短时间|makespan|balanced', t)
    if m:
        note('objective', '优化目标', 'makespan', m.group(0))
    else:
        m = re.search(r'总路程|总里程|总距离|路程最短|里程最短|最省|最少里程|total distance', t)
        if m:
            note('objective', '优化目标', 'total_distance', m.group(0))
    nums, s = _find(r'(?:速度|车速)\s*(?:为|是)?\s*' + NUM + r'\s*(米/秒|m/s|米每秒|公里/小时|km/h|千米/小时)', t)
    if nums:
        unit = re.search(r'(米/秒|m/s|米每秒|公里/小时|km/h|千米/小时)', s).group(1)
        note('speed_mps', '车速', nums[0] / 3.6 if 'h' in unit or '小时' in unit else nums[0], s)
    m = re.search(r'不规则|多边形|L\s*形|异形|irregular', t)
    if m:
        note('shape', '边界形状', 'L' if 'L' in m.group(0).upper() else 'irregular', m.group(0))
    nums, s = _find(r'(?:种子|seed)\s*' + NUM, t)
    if nums:
        note('seed', '随机种子', int(nums[0]), s)
    nums, s = _find(r'(?:车宽|机器人宽|宽度)\s*' + NUM + r'\s*(?:米|m)', t)
    if nums:
        note('robot_width', '车宽', nums[0], s)
    return {'spec': spec, 'found': found, 'text': t}


def fill_defaults(spec: dict) -> tuple[dict, list[dict]]:
    """Complete a parsed spec with sensible agricultural defaults; returns (full spec, defaults used)."""
    out, used = dict(spec), []

    def default(key, label, value):
        if key not in out:
            out[key] = value
            used.append({'key': key, 'label': label, 'value': value})
    if 'size' not in out and 'area_m2' in out:
        side = math.sqrt(out['area_m2'])
        out['size'] = [round(side * 1.4, 1), round(side / 1.4, 1)]
    default('size', '场地', [160.0, 100.0])
    default('kind', '作业类型', 'sampling')
    default('vehicles', '车辆', 3)
    default('tasks', '任务点', 30)
    default('plots', '地块', 4)
    default('distribution', '分布', 'rows' if out['kind'] in ('spraying', 'harvest', 'seeding') else 'uniform')
    default('obstacles', '障碍', {'pond': 1, 'building': 1})
    default('depot', '车库', 'sw')
    default('objective', '优化目标', 'total_distance')
    default('speed_mps', '车速', 1.0)
    default('robot_width', '车宽', 1.0)
    default('shape', '边界形状', 'rect')
    return out, used
