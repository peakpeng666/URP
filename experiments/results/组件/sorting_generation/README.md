# P2：CodeGen-350M 排序代码生成先导实验

## 当前结论

**22 个官方模型真实生成输出及静态检查已保存；没有动态正确率或提示改进结论。先读 `RESULTS.md`。**

这是老师实践 P2 的准备，不是 URP 原创算法结果，也不替代 P1、车辆路径、EoH 或农业场景实验。所有静态检查都不等同于程序正确性验证。

2026-10-04 初始核查结果（安装前的历史记录）：

- 当前为 Debian GNU/Linux 13.6、Python 3.12.14；Ubuntu 22.04 仍未复现验证
- 缺少 torch、transformers、safetensors、huggingface_hub、tokenizers；accelerate 也缺少，但单 CPU 显式加载不必依赖它
- 默认 Hugging Face 缓存不存在；未安装包、未下载权重、未调用付费服务或外部 LLM API
- 环境记录时工作目录有 27,555,045,376 字节可用空间（约 27.56 GB）；主机内存信息不代表容器保证配额，cgroup 内存上限不可读取
- 严格无网络 bwrap 启动探针失败：`Failed to create NETLINK_ROUTE socket: Operation not permitted`
- 不放宽隔离条件，不运行任何模型生成代码；本目录没有可用的生成代码执行器

安装前证据：`results/environment.json`、`results/preflight.json`。随后获得安装与下载许可，已安装 CPU torch 2.14.1+cpu、transformers 5.18.0；实际环境见 `results/generation_environment.json` 和 `requirements.lock.txt`。权重下载实际为 797,367,631 字节，SHA256 匹配官方值。手写评测设施的 13 项自检通过，见 `results/preparation_tests.json`，这不是模型正确率。

## 模型来源、版本和加载风险

- 官方模型：[Salesforce/codegen-350M-mono](https://huggingface.co/Salesforce/codegen-350M-mono)
- 冻结修订：[d9107f71cca463240db1143f4a75a927a27fcb27](https://huggingface.co/Salesforce/codegen-350M-mono/commit/d9107f71cca463240db1143f4a75a927a27fcb27)
- 官方文件列表显示 `pytorch_model.bin` 约 797 MB，完整仓库约 801 MB；这是页面显示的四舍五入大小，不是本地下载实测
- [权重页面](https://huggingface.co/Salesforce/codegen-350M-mono/blob/main/pytorch_model.bin)显示 SHA256：`90e20f4887289739a435452f26974d97937adb41485f9c1a7b3d3810aac6773d`
- 当前官方 main 未列出 safetensors；`.bin` 属于 pickle 格式，网站扫描的 Safe 标记不是安全执行保证
- 模型页标为 BSD-3-Clause；[官方 CodeGen1 许可证](https://github.com/salesforce/CodeGen/blob/main/codegen1/LICENSE.txt)对应 BSD-3-Clause。仓库顶层后来用于其他版本的 Apache-2.0 许可证不应直接当成该模型许可证
- 模型卡说明这是研究发布，并提醒下游使用需评估安全和准确性；本任务仅做教学研究，不部署给用户
- 原生 [Transformers CodeGen 实现](https://huggingface.co/docs/transformers/model_doc/codegen)可用于该模型，不需要 `trust_remote_code=True`

实际已执行与剩余门槛：

1. 用户许可后，在本目录独立 `.venv` 安装 CPU torch 和 transformers 依赖；依赖计划、安装日志、完整版本锁和 pip check 已保留。未安装 CUDA 包，未改动系统 Python
2. 从官方固定修订下载九个模型/分词器文件，逐个记录字节数和 SHA256，见 `results/model_download.json`。只有模型权重约 797 MB；依赖与全部模型文件合计约 1.05 GB，下载请求含少量元数据且解析可能重新传输 wheel，因此此值不是精确网络流量
3. 官方缺少 safetensors。采用当前官方 PyTorch 的 `weights_only=True` 和 `TORCH_FORCE_WEIGHTS_ONLY_LOAD=1`，静态检查未发现需额外允许的 pickle 全局对象。没有把任何额外对象加入反序列化允许列表，没有回退到 unrestricted pickle，没有远程模型代码
4. 从已校验本地文件离线加载，`local_files_only=True`、`trust_remote_code=False`，关闭 Hub 遥测和隐式身份信息使用。`weights_only` 可减小反序列化攻击面，但不是完全安全保证或执行沙箱；[官方 PyTorch 说明](https://docs.pytorch.org/docs/2.14/notes/serialization.html)仍列明拒绝服务等风险
5. 模型成功加载为 CodeGenForCausalLM，356,712,448 个参数。新版本 Transformers 报告 20 个旧 causal_mask 缓冲为 unexpected；没有缺失参数警告，新原生实现通过 create_causal_mask 构造掩码。原始加载警告保留在 `results/generation.log`，不能把跨版本加载称为与旧环境逐位等价
6. 正确率评测仍被安全执行环境限制：必须建立无网络、不可写文件、无凭据/用户文件暴露、禁止派生进程、CPU/内存/墙钟/输出限额的独立沙箱，并以故障探针验证。bwrap 探针失败后没有放宽边界或执行候选程序。推理过程的内存和时间限额不是生成代码沙箱

模型真实推理和静态检查已完成，计划 22 个候选全部有记录；实际尝试为 23 次，包含一次 CPU 资源中断。真实原始记录在 `results/raw_generations.jsonl`；`results/static_summary.json` 的 expected=22、recorded=22、missing=[]。全部输出达到 256-token 上限，不能称为 22 个完整可执行程序。

## 冻结实验设计

`config.json` 和 `prompts/` 给出精确配置。`results/freeze.json` 记录准备文件的 SHA256；任何实验设计变更都应生成新版本并注明发生在推理前还是之后。

### 对照问题

两种提示都要求相同语义：输入必须是普通 Python list，元素必须是普通 int（排除 bool），返回升序的新 list，保留重复元素且不改变输入；其他类型抛出 TypeError。空列表、负数也必须正确。允许内置 sorted，因此这里只测代码正确性和契约遵守，不声称发明排序算法。

- `baseline.txt`：紧凑自然语言契约
- `clear_constraints.txt`：把同一契约分解为明确约束，强调类型、别名和边界条件；不展示测试输入，不提供参考实现

不把新增需求当成提示改进。两组共用函数签名、正确性判定和预算。

这是基础代码补全模型，不是聊天指令模型；英文注释加函数签名符合模型卡的使用方式，未套用聊天模板。但无限定函数边界的续写可能继续生成其他函数或测试；本次整段 AST/单函数指标同时受停止策略、输出格式和 256-token 截断影响，不能单独归因于算法能力。下一版若研究这些因素，应在生成前登记函数边界停止规则及更充足的 token 预算；不能事后提取可用片段并记成本次成功。

### 计划生成规模和参数

- 每组 1 个贪心输出，另有 10 个抽样种子，共计划 22 个候选程序
- 抽样温度 0.7、top-p 0.95、top-k 0、单 beam、最大新增 256 tokens
- 相同 10 个种子配对两种提示，每次生成前重置随机数状态；两种提示交替运行，避免运行次序全部偏向某一组
- CPU float32、batch=1、2 个 torch 线程；固定模型为 eval 模式，使用 inference_mode；记录实际软件版本、设备、输入和输出 token 数及生成耗时
- 每次保留原始提示、原始 continuation、全部 token IDs、EOS/长度上限停止原因、异常和时间；失败不得静默重试或丢弃
- 候选源码为原始提示加原样 continuation；不自动删测试调用、提取局部代码、修复缩进或重新提示
- 已记录实际包版本与硬件环境；即使启用确定性算法，也不能声称跨 CPU、软件版本或操作系统逐位一致

### 独立输入和契约检查

`src/cases.py` 使用与采样种子分离的固定生成种子，已生成 `fixtures/cases.json`：

- 12 个边界输入：空、单元素、重复值、全相同、负数、混合正负、已有序、逆序、全零、大整数、交替值等
- 48 个伪随机有效输入：长度 2、3、8、16、32、64、128、257；宽值域和高重复值域各 3 次
- 12 个无效输入：tuple、dict、单个 bool/int/float/string/None，以及含 bool/float/string/None/嵌套列表的 list
- 所有数组均不写入模型提示，不允许按候选失败情况修改这批测试后仍称为同一次冻结比较

正确性检查须覆盖：与可信 sorted 结果一致、元素多重集守恒、输出为普通 list[int]、输入最终状态不变、返回值不与输入同一对象、非法输入恰为 TypeError。输入最终状态检查不能检测“先修改再恢复”的瞬态行为，这一限制要保留。尚未实现的沙箱执行器必须在 JSON 序列化之前记录对象同一性和异常类别。

这里的 72 是测试用例数，60 是有效输入用例数；可能存在相同数组，不能把用例数当成独立任务数。它们只覆盖一个排序契约，不能推断其他编程任务的泛化。

### 指标和解释边界

- 主指标：每种提示的 10 个随机候选中，全部 72 例及结构契约都通过的候选比例；贪心输出另报
- 次指标：有效排序通过数 / 60、无效类型通过数 / 12、非变异和新对象契约通过情况、语法错误率、结构/安全拒绝率、运行异常、超时和输出截断
- 所有失败计入候选总数；详细报告有效输入核心排序与类型契约，避免用一个汇总数掩盖失败原因
- 静态检查为 syntax_valid 的程序仍可能完全错误；被沙箱或结构规则拒绝的候选单列，不伪装成已运行的错误结果
- 以候选程序为单位比较 10 个配对种子；不能把 22×72 次测试当作独立样本。小规模结果只作描述，不预设显著性、不声称“优化一定有效”
- 若未来根据此结果继续改提示，这批输入成为开发数据；需要另冻结新的未参与提示修改的测试集后再报告泛化

## 可复现的已执行部分

本目录准备脚本只依赖 Python 标准库：

```sh
cd URP/experiments/sorting_generation
python -B src/cases.py
python -B -m unittest discover -s tests -v
```

手写参考实现仅用于验证数据和 checker；测试不会 `exec` 或 `eval` 模型生成内容。`src/static_review.py` 只解析 AST、报告结构与敏感名称，不执行候选、也不是安全沙箱。

`raw_generations.jsonl` 保留真实输出，静态汇总不含动态正确率。没有候选执行结果；不要把缺失值补成零、复制参考代码当模型结果，或把准备自检通过率当模型准确率。

## 完成条件

P2 小型先导结果需要：实际模型加载记录、22 个真实原始生成记录、通过隔离探针的执行器、逐候选逐例结果与失败清单、两种提示比较和局限说明。本次到真实生成和静态检查为止，P2 的正确率比较尚未完成。

## 运行与交付注意

真实推理命令为：

```sh
timeout --signal=TERM --kill-after=10 1200 .venv/bin/python -u -B src/generate_static.py
python -B src/summarize_static.py
```

生成脚本拒绝覆盖已经存在的原始记录；不能直接重跑后覆盖证据。模型下载脚本只取固定官方文件，拒绝覆盖现有模型文件。若换机器，需要先复现官方源依赖安装和文件校验，并重新评估资源上限。

`.venv/`、`.model/`、`.cache/` 是本地运行环境和权重，不包含在轻量交付包；`requirements.lock.txt`、官方来源、校验值、源代码、冻结文件、测试输入和真实结果必须保留。模型加载/推理日志和未运行阶段不能省略。

### 资源中断与补跑

首次进程在 900 秒 CPU 安全上限处终止，已完整保存 18 个候选；正在生成的 sample_257_baseline 没有写出完整输出。这一次也计入生成尝试及基础设施失败，不当成成功或静默删除。只补四个未保存的候选，使用相同冻结参数，不重跑已完成输出。原始日志保留在 `results/attempts/initial/`，中断说明在 `results/runtime_interruption.json`。

`src/resume_static.py` 是资源恢复用扩展：与冻结生成器相同，只允许跳过已保存 ID 并追加记录；代码哈希记录在中断说明中。计划仍为 22 个不同候选；补跑已完成，实际为 23 次生成尝试，其中一次中断。按尝试报告完整输出比例时不能排除这次失败。

逐条完整输出的生成耗时有记录；被中断的局部生成没有完整墙钟计时，实际完整总耗时不可精确重建。汇总因此明确标记未知，不把成功记录耗时之和称为完整运行总成本。初始进程的工具观察时间窗约为 478 秒，含启动和报告延迟，仅供排错。

首轮中断记录的证据限制：当时没有在每次 generate 前写入 start 事件，也没有保存局部 token，因此中断候选标识 sample_257_baseline 是根据最后一个完整记录后的下一计划任务推定，不是直接的 attempt-start 观测。23 次尝试的统计包含这一推定的中断尝试；完整保存的 22 条记录有直接证据。下一轮单独记录开始事件与完整进程耗时。
