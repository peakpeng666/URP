# P2 公开设计集：离线只读结果入口

这是一个 Python 标准库小工具。把本地保存的基础 ZIP 与增量 ZIP 明确传入，即可生成统一 60 槽 JSON/CSV 和每臂 30 槽分母汇总。无需安装依赖、解压科学包、启动容器或登录任何账号。

它只核验已有字节、整理保存的指标，并用 Fraction 检查已有分数。不会执行或导入科学包中的任何脚本、候选、solver，不调用 LLM，不联网，不读取 heldout，也不修改输入 ZIP。没有自动选择、排序或宣布赢家的逻辑。

## 1. 准备与运行

要求 Python 3.10 或更高版本。源码通过了 Python 3.10 语法模式解析；本次实际运行环境是 Python 3.12.14，未声称在 3.10 解释器上实测。工具仅使用这些版本均有的标准库接口。

保留原 ZIP 字节即可，不必保留其本地文件名。包内顶层目录和 manifest 身份必须不变。1–19 基础包必需，因其中有完整 60 槽冻结 roster 与五个 public case 的身份；reader 不猜缺失槽属于哪一臂。

把下例的 `/你的下载目录/` 换成实际路径，把输出目录改为一个尚不存在的新目录。参数顺序任意；不要传通配符，不会自动搜索邻近 ZIP，也不会顺着包内路径打开任何本地文件。

```sh
python -I -B read_p2_public.py --out /你的输出目录/p2_tables_60 \
  /你的下载目录/p2_public_scoring_1_19_delivery_20261007.zip \
  /你的下载目录/p2_public_scoring_20_25_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_26_31_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_32_37_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_38_43_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_44_49_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_50_55_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_56_60_delta_20261007.zip
```

Windows 可将命令合成一行，使用 `py -3 -I -B` 与带引号的 Windows 绝对路径。ZIP 内部路径仍必须是正常的相对 POSIX 路径。

完整 60 槽已用最终不可变 56–60 包实测，见 FINAL60_INTEGRATION.json。若暂未保存最后包，去掉最后一行即可读前 55 槽，56–60 保留未齐；以后补包时用新输出目录再运行，不必更新工具。

## 2. 输出怎么看

- `slots_60.csv`：按冻结 position 排列的 60 行。每槽有 arm、生成原状态与客户端状态、AST 状态、精确 Fraction、浮点 fitness、五列 used_bins、各项 CPU、失败原因、来源 ZIP/member/SHA。
- `slots_60.json`：同一张表的权威结构化版本，保留 null、unknown、原 fitness 对象与原状态。
- `arms.csv` / `arms.json`：EOH_TC、IID_TC 固定名称顺序，完整计划分母各 30，另列已有回执数、未齐数、生成失败、AST static 拒绝、准入次数、完整 fitness 和测量 CPU 的覆盖数。
- `report.json`：每包 ZIP/manifest SHA、逐条链校验结果、缺包清单、去重信息、原最新 SUMMARY 原样对象、公式与源 hash、独立 reader CPU/wall。
- `说明.txt`：简短中文入口。

CSV 中 `null` 是字面文本，不是空值、0 或失败分数。列表/字典列为 JSON 文本，另有 `case_0_used_bins` 至 `case_4_used_bins` 方便直接读表。避免电子表格把文本当公式，CSV 的相关文本可能加单引号；JSON 保留原字符串。UTF-8 BOM 方便中文表格软件识别。

`evidence_status=已齐` 仅表示本槽原 result 回执在明确传入的包中存在并通过本工具检查；整个链是否齐全另看 `report.integrity_status`。缺中间包时，该包对应槽标为未齐，其余已有 result 仍可浏览；不会用后包的累计表或 STATUS 快照补造 capture。缺基础包时直接报错，须补上基础 ZIP。

生成回执的 `generation_status_raw=awaiting_admission` 是源数据保留的阶段字段，并不覆盖后来的 `evaluation_status=scored/admission_rejected`。客户端 exited、非空公开答案也不代表 provider 端已获得独立证明；`provider_outcome=unknown` 保留原值。

AST 拒绝但 `failure_reason=null` 表示源回执没有保存更细原因；查看 `AST_status=rejected_static` 与 `admission_kind=static` 即可，不编造异常文字。未开始数值评分的生成失败槽 CPU 留 null，另标 `no_numeric_execution_recorded`，不会把 null 当 0。

## 3. 精确公式、成本和解释范围

只使用源包既有公式：五个 public case 的 `L1_i / used_bins_i` 的算术平均；先用 `fractions.Fraction` 相加再除 5，精确比较原 numerator/denominator。浮点值只是便于看表。每个完整分数要求五个 case 的原 outcome 为 ok、原 checker_status 为 passed，并对齐源 public 输入 SHA、L1 和候选 source SHA。本工具不重跑 checker 或候选。

数值 CPU 按原账口径读取：

`admission.worker.cpu_seconds + Σ(pack.worker.cpu_seconds + pack.supervisor.actual_supervisor_cpu_seconds)`

inclusive wait4 已包括相关子进程；score_call_cpu_ns 也已在 child CPU 中，二者只单列展示，不再相加。原 SUMMARY 的资源、claim、unknown 和范围说明不改写，全部保存在 `source_summary_raw`。每臂 CPU 是已测数值回执的和，并列已测/未知/未运行槽数；不代表 provider 计费、生成 CPU、全部科研支出或历史剩余预算。

reader 的 `process_cpu_seconds` 和 wall 单独列在 `reader_cost_separate_from_science`，测量范围明确写在报告中，不计入科学 CPU。测试脚本启动与复制开销也不是科学成本。

每臂覆盖率都属于固定 public 设计集的描述性指标。完整分数覆盖率的计划分母始终为 30，失败不删除；尚未齐槽另列，不能当已失败或 0 分。没有均值填补或自动跨臂优劣判断。

`source_reported_best_public_design_raw` 只是原最新 SUMMARY 已有 best-design 字段的原样副本，本工具不重新选候选或排列榜单。它与覆盖率均不构成 heldout、泛化或两臂有效性结论。保存的证据不包含原来未保存的 provider HTTP、私有推理、完整 assignment 数组等；该工具不宣传可重现 provider 生成或原硬件运行。

## 4. SHA 与链的含义

每个包的全部 manifest 项按大小和 SHA-256 核验；非 JSON 文件仅当作不透明字节做 hash，不执行、不向磁盘提取。BASE_REFERENCE / CHAIN_REFERENCE 中的前序 ZIP SHA、manifest SHA 和 manifest 副本一并对比。累计 state hash、累计精确分数表只作交叉检查；汇总来源始终是去重后的原 result。

同一输入 ZIP 重复列出、顺序变化不会增加槽数、分数或成本。逻辑相同的 state 文件只在字节一致时去重；同一包身份却不同 ZIP 字节会报错（即使只是重新压缩）。拒绝 ZIP 路径穿越、绝对路径、符号链接、未列入 manifest 的文件和冲突重复条目；不提取文件，不建立数据库。

SHA 是给定文件与链内引用的一致性检查，不是数字签名，也不能证明文件在进入本工具之前未被连同 manifest 替换。尤其最新 ZIP 没有后包为它背书时，可使用来自可信交接记录的外部 SHA：

```sh
python -I -B read_p2_public.py --out /新的输出目录 \
  --expect-sha256 "/你的下载目录/某包.zip=交接记录中的64位SHA256" \
  /你的下载目录/基础包.zip /你的下载目录/某包.zip
```

`--expect-sha256` 可重复；只适用于同一次命令明确列入的 ZIP。`KNOWN_INPUTS.json` 是本次已检查文件的参考清单，reader 不自动读取它，更不会把清单当新的访问授权。

## 5. 退出码与问题排查

- `0`：60 槽原 result 齐全且给定链完整，成功写表。并不代表 60 个候选全部成功。
- `2`：已有证据已写表，但 60 槽或包链尚未齐全。前 55 槽正常读取时就是这个状态。
- `1`：校验失败、输入身份冲突、缺基础包或路径错误。核验失败时不创建新输出目录；写出阶段发生文件系统错误时可能留下不完整输出，换一个新目录重试。

输出目录必须尚不存在，防止覆盖旧结果。SHA 失败时重新取得正确原 ZIP，不要改 manifest 来让工具通过；缺包时补上明确的路径重新输出。

## 6. 本次验证与可选自测

`TEST_RESULTS_55.json`、`FINAL60_INTEGRATION.json` 和 `测试记录.md` 保存实测结果。未携带原科学大 ZIP、候选、数据、凭证或依赖环境；本工具包只含代码、说明与小型核验记录。

可选自测（只运行本目录 reader，始终先把列出的原 ZIP 复制到新目录，不执行包内代码）：

```sh
python -I -B test_reader.py --work /全新测试目录 --expected-slots 55 \
  /你的下载目录/p2_public_scoring_1_19_delivery_20261007.zip \
  /你的下载目录/p2_public_scoring_20_25_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_26_31_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_32_37_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_38_43_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_44_49_delta_20261007.zip \
  /你的下载目录/p2_public_scoring_50_55_delta_20261007.zip
```

完整 60 槽可改 `--expected-slots 60` 并补最终包。测试内容是完整输入集成、倒序重复包不加计、缺中间包不补造、缺基础包报错、损坏 SHA 报错、不安全 ZIP 路径报错、错误外部 SHA 报错、重压缩但同身份的重复 ZIP 冲突。原 ZIP 测试前后 SHA 必须不变。
