# DEAP Sphere 最小化教学补充（一次固定运行）

## 与教师要求的对应

原文定位：`docs/code_review/teacher/teacher_original_extract.txt` 672–674行，第13–14周「GA、PSO、DE / DEAP 实现优化器」；331行普通float fitness下用max选父代方向不适合Sphere；363–373行新个体未评价便选择/打印fitness会处理None。本例补DEAP框架的真实教学运行，既有180次GA/PSO/DE冻结实验与原源码均未改。

本例不是旧P1自写GA的数值等价版本，也不是DEAP eaSimple、默认h1最大化PSO或原论文复现。仅一个Sphere种子，不能比较算法强弱或说明跨问题泛化，不能增加论文复现数量。

## 代码读法

- `src/sphere_ga.py: Individual / make_toolbox`：DEAP creator定义weights=(-1.0,)，原始Sphere越小越好；weighted Fitness比较中大者反而代表原始目标小者。注册初始化、评价、锦标赛、SBX、多项式变异、存活选择
- `CountedSphere`：有限/边界/维度检查，目标返回单元素tuple；每次评价保存坐标副本、值和连续编号，防止后来变异污染账本
- `vary`：选择返回父代引用，所以逐个deepcopy；原地mate/mutate只动克隆；所有子代del fitness.values。未变克隆也重新收费是显式教学预算选择，与eaSimple只评价invalid缓存策略不同
- `evaluate_invalid → replace`：先评价子代，再父子合并selBest选N存活；无效fitness直接拒绝，返回再克隆保证无共享个体。初代及每代最佳记录于history
- `run`：保存/恢复Python random状态；DEAP算子使用全局random，运行须单线程，不供并发调用
- `src/audit_result.py`：不import优化器/DEAP，独立从保存账本重算Sphere值、全部历史前缀最优、预算、边界、来源哈希

## 事前固定参数

D=5，[-5.12,5.12]，N=20，G=20，seed=20261005；SBX eta=15、cxpb=.8；多项式变异eta=20、个体概率=.3、坐标概率=1/D；锦标赛大小3，有精英的(mu+lambda)存活。每代20次目标调用，加初始20，共420。所有初始点即ledger前20行。不是调参实验；只运行一个正式槽，无选优重跑。

## 真实结果

- 初始最好Sphere：18.591493140617015
- 最后最好Sphere：0.008735831615323184（理论最优为0，未达到0）
- 实际目标评价：420/420；21条最优轨迹；独立保存结果核验通过
- 8项测试通过：手算25/5与最小化方向、克隆/fitness失效/输入账本不共享、拒绝未评价选择、重复克隆计费与预算上限、可重复及RNG恢复、原始账本/边界/精英单调、无效输入、奇数种群及零代
- 单元测试另有微型优化调用；它们是代码测试，未混入这个正式槽，正式结果没有含测试均值

## 环境与证据

Python 3.12.14、DEAP发行版1.4.3、NumPy2.3.5。独立`.venv`，未改原研究环境。原环境未找到DEAP。官方PyPI精确版本wheel下载后与PyPI JSON SHA256核对，见`results/dependency_verification.json`；`requirements.lock`锁版本与当前Linux cp312 wheel哈希。不是跨平台通用lock。NumPy为DEAP依赖，目标本身用math.fsum。

`results/protocol_frozen.json`为运行前参数/代码哈希；`run.json`保留完整初始点、每次评价、每代轨迹、末代种群与环境；`run.log`保留stdout；`tests.log`测试日志；`postrun_audit.json`独立检查。官方来源：https://pypi.org/pypi/deap/1.4.3/json 、https://pypi.org/pypi/numpy/2.3.5/json 。

## 实际使用的命令（从URP根目录）

```bash
python -m venv experiments/deap_teaching_v1/.venv
PYTHONDONTWRITEBYTECODE=1 experiments/deap_teaching_v1/.venv/bin/python -m pip download --index-url https://pypi.org/simple --only-binary=:all: --dest experiments/deap_teaching_v1/vendor deap==1.4.3 numpy==2.3.5
# 核对PyPI JSON的对应wheel哈希并生成requirements.lock后安装：
PYTHONDONTWRITEBYTECODE=1 experiments/deap_teaching_v1/.venv/bin/python -m pip install --no-index --no-compile --find-links experiments/deap_teaching_v1/vendor --require-hashes -r experiments/deap_teaching_v1/requirements.lock
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=experiments/deap_teaching_v1/src OPENBLAS_NUM_THREADS=1 experiments/deap_teaching_v1/.venv/bin/python -m unittest discover -s experiments/deap_teaching_v1/tests -v
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 experiments/deap_teaching_v1/.venv/bin/python experiments/deap_teaching_v1/src/sphere_ga.py --output experiments/deap_teaching_v1/results/run.json
PYTHONDONTWRITEBYTECODE=1 experiments/deap_teaching_v1/.venv/bin/python experiments/deap_teaching_v1/src/audit_result.py
```

运行入口拒绝覆盖既有run.json，重复上述正式命令会报已存在；复验应另指定输出，不应删除/覆盖旧证据。
