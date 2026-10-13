# 第二轮：函数补全与边界提取的静态开发实验

**10 次真实生成均完成，无重试；预先规定的函数提取改变了静态格式指标。没有执行任何生成代码，不能报告排序正确率，也没有证据表明更详细提示提高功能正确性。**

本轮是看过首轮输出后设计的开发实验。模型不变，但提示改为函数签名 + docstring，token 上限从 256 增为 512，另加预先冻结的结构提取，并将 CPU 线程从 2 改为 1。不能将跨轮变化归因于单一提示因素，也不能跨轮比较耗时当模型速度结论。

## 核心结果

两组各 5 个相同配对新种子，总计 10 个不同候选、10 次实际 generate 调用、10 条完成记录；缺失记录 0、生成错误 0、重试 0。30 条 start/generate-start/completion 事件均保留。

- 紧凑 docstring：原文 AST/编译通过 4/5，原文单函数结构 1/5；提取后 AST/编译/单函数结构均为 5/5
- 明确约束 docstring：原文 AST/编译通过 1/5，原文单函数结构 0/5；提取后 AST/编译/单函数结构均为 5/5
- 紧凑组 4 个、明确组 5 个检测到真实顶层边界并截取；另 1 个只有 EOF 的自动 DEDENT，按规则原样保留
- 所有提取后函数均有 docstring 之外的函数体语句，没有把输入自带 docstring 的空实现算成生成实现
- 紧凑组 2/5、明确组 4/5 达到 512-token 上限；其余由 EOS 结束。总共保留 4,100 个真实生成 token

这些分子/分母只描述静态解析、编译和结构，不是功能通过率或 pass@1。提取没有改变模型原始输出，也没有减少本次推理成本；完整原文同时保留。

## 静态阅读中的语义问题

逐个静态阅读发现 10 个提取函数均有具体契约反例，完整清单见 `results/static_counterexamples.json`。其中 7 个对合法空列表报错，另 3 个分别丢掉重复值、访问空列表第 0 项、接受 bool 元素。

这不是运行测得的“正确率 0%”，而是逐例源码反例。举例：

- 紧凑提示 seed 499 创建 unique_elements，直接丢掉重复值
- 明确提示 seed 499 对空列表使用 values[0]，没有满足空列表契约
- 明确提示 seed 541 只检查外层 list，不检查每个元素是否为普通 int，违反非法类型处理要求
- 多个输出主动拒绝空列表、重复元素或未排序输入，与题目要求相反

这些是代码阅读发现，未执行测试。不能把“提取后均可编译”宣传成“两组都得到 5 个正确程序”。

## 运行和核验

- 模型、固定修订、官方权重校验和 CPU PyTorch/Transformers 环境沿用首轮，见上两级目录的 requirements.lock.txt 与 results/model_download.json
- 本轮完整进程墙钟：421.453892 秒；用户 CPU：421.254178 秒；系统 CPU：1.457297 秒
- 进程峰值 RSS：2,465,924 KiB（约 2.35 GiB），不是整个容器总内存
- 外层监督器正常退出，未达到 900 秒 CPU / 1200 秒墙钟上限
- 14 项提取器/静态分析测试通过；8 个冻结文件、10 条候选记录、30 条事件的完整性验证通过
- 生成器只从本地加载已校验官方权重，weights_only=True，不启用远程模型代码
- Python compile 只作静态编译检查，从未运行其代码对象；网络/写文件限制下的动态执行器仍未建立
- Debian 13.6、Python 3.12.14 上实测；Ubuntu 22.04 仍未验证

## 文件入口

- `PROTOCOL.md`：执行前审阅的规则和解释边界
- `config.json`、`prompts/`、`results/freeze.json`：实际冻结参数与哈希
- `results/raw_generations.jsonl`：原始 token、原文、提取前后代码与静态检查
- `results/attempt_events.jsonl`：生成前已 flush/fsync 的开始记录及完成记录
- `results/process_status.json`：完整进程资源耗时与退出状态
- `results/static_summary.json`：原文与提取后指标并列汇总，功能正确率明确为 null
- `results/artifact_verification.json`：完整性检查
- `manifest.json`：本轮轻量文件清单与 SHA256；不含上级模型、虚拟环境或缓存

## 复现与继续

本轮复用首轮 `.venv` 和 `.model`，首次执行命令是 `python -u -B src/supervise.py`。已有输出时会拒绝覆盖和自动重试。分析复核可运行：

```sh
python -B -m unittest discover -s tests -v
python -B src/summarize.py
python -B src/verify.py
```

继续 P2 仍需要经验证的安全动态执行环境，以及逐候选逐输入的真实正确性结果。本轮只能证明函数边界/整段续写会强烈影响表面的语法结构指标；不能证明正确率改善、研究创新或 P2 教师验收完成。
