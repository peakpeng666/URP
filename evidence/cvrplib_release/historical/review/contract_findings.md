# CVRPLIB 来源合同独立复核

核对日期：2026-10-14 UTC。本文只记录来源合同与可复核推导，不代表正式实验已经运行或代码已经准入。

## 已证实结论

- 小16权威来源为 public_route_strong_baseline_20261009_r1/freeze/TASKS.json 和 PROTOCOL.json，组成 A6/B6/P4，合同为至多 K_ref 非空路线、固定成本零、逐边 EUC_2D 整数距离。名单不得替换成 E/F 跨族16。
- 一手来源 Uchoa 等 §2、§3.3 说明传统 ABEFMP 的整数距离/固定K约定，而新X采用不固定路线数；X名称K只是下界，不能当上限。
- 独立读取本次41个非X输入，全部满足 ceil(总需求/Q)=K。因每条路线载重不超过Q，任何可行解至少K条；与“至多K”相交后恰好K。该等价性是本面板逐例算术证明，不推广到所有CVRPLIB。官方逐例K、Q、输入哈希仍由全量数据审计确认。
- X配置可提供客户数辆同质车辆、固定成本0。这是无限可用非空路线的有限等价表示，不是K约束。
- 原公共强基线为 PyVRP 0.14.0 ILS；旧 MaxRuntime(1)只计主循环、不含初始化，不能作为新1秒端到端结果。

## 来源和证据

- https://optimization-online.org/wp-content/uploads/2014/10/4597.pdf ：§2及§3.3；下载SHA256 dbe0c20bf8a37602f1b71be111b62edd62cbeec9f42a76035dee52fa868b3942。
- https://galgos.inf.puc-rio.br/cvrplib/en/instances ：官方每例规模、K、容量、上界及最优标签。
- review/nonx_capacity_lowerbounds.json ：独立计算，列为name、K、ceil(total demand/Q)、Q。正式发布应重新由严格解析器复算并保存可运行命令。

## 限制

证明至多K与恰好K等价不证明参考解成本；53份参考仍须独立检查覆盖、容量、车数、逐边距离、总成本及来源最优标签。已验证可行参考并不自动等于已证明最优。公开小16已有使用历史，整面板不能称严格未见测试集。规模与来源混杂、重复底本也不因输入正确而消失。
