import type { Branch, Family, OraclePreference, Order, Policy, Split } from './types';

export const FAMILY_ORDER: Family[] = [
  'weibull_3_45',
  'uniform_1_100',
  'small_beta_2_5',
  'large_beta_5_2',
  'normal_50_15',
  'bimodal_20_30_70_80',
];

export const ORDER_ORDER: Order[] = ['random', 'ascending', 'descending'];
export const SPLIT_ORDER: Split[] = ['train', 'confirmation', 'risk'];

export const FAMILY_LABEL: Record<Family, string> = {
  weibull_3_45: 'Weibull',
  uniform_1_100: '均匀整数',
  small_beta_2_5: '偏小 Beta',
  large_beta_5_2: '偏大 Beta',
  normal_50_15: '裁剪正态',
  bimodal_20_30_70_80: '双峰',
};

export const FAMILY_DETAIL: Record<Family, string> = {
  weibull_3_45: 'Weibull（形状 3，尺度 45）',
  uniform_1_100: '1–100 均匀整数',
  small_beta_2_5: '100 × Beta(2, 5)，物品偏小',
  large_beta_5_2: '100 × Beta(5, 2)，物品偏大',
  normal_50_15: 'Normal(50, 15) 裁剪到 [1, 100]',
  bimodal_20_30_70_80: '20–30 与 70–80 等概率双峰整数',
};

export const ORDER_LABEL: Record<Order, string> = {
  random: '随机',
  ascending: '升序',
  descending: '降序',
};

export const SPLIT_LABEL: Record<Split, string> = {
  train: '训练',
  confirmation: '确认',
  risk: '风险',
};

export const SPLIT_DETAIL: Record<Split, string> = {
  train: '训练集：只有两条真实分支，用来拟合邻居标签、选出 SBS',
  confirmation: '确认集：模型冻结后执行，主指标只来自这里',
  risk: '构造风险集：同一前缀接三种不同未来，单列，不并入主指标',
};

export const POLICY_LABEL: Record<Policy, string> = {
  BF: '全程 BF',
  BF_then_EoH: 'BF→EoH',
  published_EoH: '全程 EoH',
  SELECTOR: '前缀选择器',
};

export const POLICY_DETAIL: Record<Policy, string> = {
  BF: '5000 项全部用 Best Fit',
  BF_then_EoH: '前 500 项 BF，之后 4500 项用固定 EoH',
  published_EoH: '从第 1 项起就用固定 EoH；第 500 项时的箱状态可能不同',
  SELECTOR: '前 500 项 BF，读取前缀后只选一次：继续 BF 或切到 EoH',
};

export const BRANCH_LABEL: Record<Branch, string> = {
  BF: '继续 BF',
  BF_then_EoH: '切到 EoH',
};

export const PREF_LABEL: Record<OraclePreference, string> = {
  BF: '继续 BF 更好',
  BF_then_EoH: '切到 EoH 更好',
  tie: '两分支相同',
};

export const POLICY_COLOR: Record<Policy, string> = {
  BF: 'var(--bf)',
  BF_then_EoH: 'var(--eoh)',
  published_EoH: 'var(--full-eoh)',
  SELECTOR: 'var(--sel)',
};

/** Raw hex for canvas drawing (CSS variables are not available there). */
export const POLICY_HEX: Record<Policy, string> = {
  BF: '#2f6fb3',
  BF_then_EoH: '#d08317',
  published_EoH: '#7a7f87',
  SELECTOR: '#1b2126',
};

export const BRANCH_HEX: Record<Branch, string> = {
  BF: '#2f6fb3',
  BF_then_EoH: '#d08317',
};

export function streamTitle(s: { split: Split; family: Family; order: Order; replicate: number }): string {
  if (s.split === 'risk') return `${FAMILY_LABEL[s.family]}前缀 · ${ORDER_LABEL[s.order]}后缀`;
  return `${FAMILY_LABEL[s.family]} · ${ORDER_LABEL[s.order]} · 第 ${s.replicate + 1} 组`;
}

export const FEATURE_GROUPS: { key: string; label: string; hint: string; from: number; to: number }[] = [
  { key: 'item_hist', label: '前缀尺寸分布', hint: '500 个已到物品落在 10 个尺寸区间的比例', from: 0, to: 10 },
  { key: 'item_stats', label: '尺寸统计', hint: '均值、总体标准差与 10/50/90 分位，均除以 100', from: 10, to: 15 },
  { key: 'order', label: '到达顺序', hint: '相邻严格增大/减小比例；后 100 项与前 100 项均值差 / 100', from: 15, to: 18 },
  { key: 'bins', label: '箱数', hint: 'BF 前缀用掉的箱数 / 500', from: 18, to: 19 },
  { key: 'residual_hist', label: '已用箱残量分布', hint: '已用箱残量落在 10 个区间的比例', from: 19, to: 29 },
  { key: 'residual_stats', label: '残量统计', hint: '已用箱残量的均值与总体标准差，除以 100', from: 29, to: 31 },
];

const FEATURE_LABEL: Record<string, string> = {
  item_mean: '尺寸均值',
  item_sd: '尺寸标准差',
  item_q10: '尺寸 10% 分位',
  item_q50: '尺寸中位数',
  item_q90: '尺寸 90% 分位',
  fraction_increase: '相邻增大比例',
  fraction_decrease: '相邻减小比例',
  last100_minus_first100: '后100−前100 均值差',
  bins_per_item: '已用箱 / 500',
  residual_mean: '残量均值',
  residual_sd: '残量标准差',
};

export function featureLabel(name: string): string {
  if (FEATURE_LABEL[name]) return FEATURE_LABEL[name];
  let m = /^item_hist_(\d+)_(\d+)$/.exec(name);
  if (m) return `尺寸 ${m[1]}–${m[2]}`;
  m = /^residual_hist_(\d+)_(\d+)$/.exec(name);
  if (m) return `残量 ${m[1]}–${m[2]}`;
  return name;
}
