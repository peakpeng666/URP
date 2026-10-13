# P4：强化学习架构搜索 / CIFAR-10

本目录实现并真实运行受限 CPU 先导实验：4,000 张开发训练图片、1,000 张搜索验证图片、8 个固定 CNN 架构，比较 REINFORCE 与随机搜索。详细协议见 `PROTOCOL.md`，最终结果见 `RESULTS.md`。

**只报告开发验证结果；官方测试集从未用于评估。** 相同候选训练数不等于相同计算量。三个配对搜索种子和两个训练 epoch 只能验证链路，不能证明 RL 优于随机搜索，也不能代表完整 CIFAR-10/NAS 复现。

## 文件

- `config.json`：在实验前固定的数据划分、搜索空间、训练和控制器参数
- `run_experiment.py`：安全二进制训练集读取、固定 CNN、监督训练与搜索
- `results/*.jsonl`：原始候选记录，以及训练前已落盘的 started/failed/completed 事件
- `results/*_101.json` 等：每个种子完整搜索轨迹及选优记录
- `results/search_summary.csv`、`results/trials.csv`、`results/summary.json`：可重新生成的摘要
- `checkpoints/`：49 个最终子模型/优化器检查点（含固定基线），另有 6 个控制器状态
- `artifacts/split.json`：完整且互斥的 4,000 / 1,000 / 45,000 原训练集索引
- `artifacts/data_manifest.json`：官方来源、校验和、实际提取文件及类别计数
- `artifacts/presearch_freeze.json`：搜索前冻结的配置、源码和划分哈希
- `artifacts/source_at_baseline.py`、`source_at_search.py`：两个实际执行源码快照；后者只补充异常记账
- `verify_artifacts.py`：核验预算/索引/检查点哈希，并可独立重算所有已存检查点的验证指标
- `manifest.json`：不含数据集与虚拟环境的交付内容哈希清单
- `postselection/`：后续另行冻结的 5,000 张独立开发评估；三个去重后的搜索赢家与固定基线直接推理，不重训、不再次选优；详见该目录 RESULTS
- `artifacts/reviewer_cost_addendum.json`：额外独立核验的成本，原始先导搜索摘要保持不变

## 当前环境与复现

当前复用 `../sorting_generation/.venv` 中现有的 Python 3.12.14、PyTorch 2.14.1+cpu、NumPy 2.5.3，没有为本轮重复安装大型依赖；CPU 单线程、确定性算子，无 GPU。实际环境记录在 `artifacts/environment_*.json`。跨版本/硬件的位级相同不作保证。

从本目录运行：

```sh
PY=../sorting_generation/.venv/bin/python
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
$PY test_experiment.py
$PY test_failure_journal.py
$PY run_experiment.py prepare
$PY run_experiment.py baseline
$PY run_experiment.py search
$PY verify_artifacts.py --recompute
$PY summarize.py
```

已有正式结果时 baseline 拒绝覆盖，search 跳过已完整完成的种子；发现残缺尝试会停止，不能在原记录上悄悄补跑。复现实验请复制代码到新的版本目录并明确标记复跑，保留原始结果。`prepare` 会重新生成相同索引和更新准备时间，若要重建下载数据，建议在新的目录执行以免改变已冻结的数据来源记录。

在干净环境可从官方 PyTorch CPU wheel 仓库与 PyPI 安装 `requirements.txt` 所列精确版本；本次实测环境只保证上述已有安装可用，不把未验证安装方式当作已验证复现。

## 数据和交付

`data/` 共约 309 MiB，含官方压缩包与五个训练文件，仅本地实验需要；交付排除它、所有 `.venv`、缓存、临时文件。代码通过官方 HTTPS 地址下载，先验 MD5 校验通过后只提取白名单训练文件；任何架构都由手写可信原语组装，不执行模型生成代码。

不将本轮与前期车辆路径、排序生成或装箱实验混为独立样本；也不将本轮生成的检查点重评分当作新一轮搜索。审计重评分所用的额外验证图片呈现次数单列计费。

后续选优后评估已经使用原 45,000 张保留池中的固定 5,000 张；当前剩余 40,000 张未评估。原先导的 4,000 / 1,000 / 45,000 索引划分证据保持不变，后续的评估索引单独保存，不能把已消费的 5,000 张继续叫作未见数据。
