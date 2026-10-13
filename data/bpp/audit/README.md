# BPP 本次重建审计证据

本目录保存 2026-10-13 UTC 在 dot 云端工作环境中新生成的校验、转换与测试证据。重放对象是既有记录、既有分配轨迹、冻结模型的算术和已存 bootstrap 索引；不是新增实验。未运行策略、solver、API、模型训练或新随机采样。历史包审计及其原有预算限制仍在，不能由本次 PASS 补证。

## 本次结果

- 新完整性及记录证据验证 PASS：264 输入、768 既有运行、3,840,000 轨迹步、120 冻结选择器决策、4 风险组、18 确认单元、10,000 已存 bootstrap 重放
- 21 项原测试 PASS，包含全部 768 导出运行与原字段、六数组及来源 SHA 的全量 parity
- 2,973 个 exports 文件，共 143,493,637 字节；最终 exports 与 staging 每文件摘要一致
- 1,915 个原记录、原 ZIP、原脚本/测试/锁文件前后摘要未变

## 文件用途

- validation_report.json：本次新验证的环境、范围、覆盖、来源 SHA 与限制
- import_report.json：原 ZIP 和成员清单校验
- bpp_rebuild_report.json、execution_report.json：结果、实际命令、退出码、时间及环境
- source_inventory_before.json、source_inventory_after.json：原记录、ZIP、脚本/测试/锁文件前后字节数及 SHA-256
- exports_inventory.json：全部派生 exports 的相对路径、字节数及 SHA-256
- 01–05 日志：依赖安装、导入、证据验证、转换及 21 项测试的原始输出
- test_execution_context.json：原测试的路径重定向、实际测试适配器文本及摘要；测试断言未改写，验证上下文只用了本次新报告
- audit_bundle_manifest.json：本审计包的逐文件摘要；自身不列入自身摘要

## 命令及环境路径

报告保留执行时的真实绝对路径，作为当次环境记录，不表示收件人的电脑具有同一目录。独立环境为 Python 3.12.14 / NumPy 2.2.6，按交付中的 requirements.lock 从官方 PyPI 通过 --require-hashes --only-binary=:all: 安装。便携交付位置为 data/bpp/records、data/bpp/inputs、data/bpp/exports 和 src/frontend；在其他环境重做验证时应将报告中的根目录映射到实际项目位置，并使用新的输出目录与新的报告，不能把本目录的 PASS 当作新一轮验证。

本目录只携带必要 JSON、日志和说明，不含 venv、临时 fixture 或重复测试目录。复制前检查了命令、环境与日志内容，并扫描常见凭证格式；未发现密钥、口令、认证头或含凭证 URL，没有对原报告/日志做删改。
