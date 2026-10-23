# 暂存区与工作树独立证据

本轮只读检查了原先有暂存改动的两个工作树：`labpatch-5065046` 5项、`verify-5065046` 127项。132项 stage-0 index 的字节与原工作树字节逐项相同；不能因此把它们与 HEAD 混作一个版本。

`index-evidence.json` 对每个路径记录 HEAD、index(stage/mode/Git blob/SHA-256)、工作树原字节 SHA-256、相等关系与恢复载荷路径。HEAD 版本与 index 版本在 `preserved/index-evidence/` 分开保留；原 HEAD 中不存在的新增文件明确标记。与工作树一致的 index 版本可共用已验证的工作树字节，但清单仍分别记账。

捕获前后，两个原 index 文件的 SHA-256 未改变。未复制原 `.git/index`，未更改原 HEAD、index 或工作树；此分支没有继承原 Git 历史。

## 在新目录恢复

1. 先准备该来源 HEAD 提交的文件树副本及所需运行资产；保全分支仍是增量包。不要把含敏感历史的原 `.git` 导入恢复目录。
2. 将该来源 `head` 载荷放回相应路径，按清单文件模式建立恢复基线；HEAD 原本不存在的路径应在基线保持不存在。
3. 对清单中每个 stage 版本，核对载荷 SHA-256，用 Git `hash-object --no-filters -w` 写入新恢复仓库，再按记录的 mode、stage、Git blob 和路径构造新的 index。存在冲突 stage 时应分别恢复，不能默认取 stage 0。
4. 最后写入 `working_version.payload`，核对工作树 SHA-256。此次132项 index/工作树相同，预期只有暂存差异；HEAD 与 index 的变更照实保留。

恢复目标是相同的文件字节、模式及暂存/未暂存关系；新机器 index 的 inode/mtime/stat 缓存不会与原 index 二进制相同。原 index 的前后校验用于证明本轮未改现场。
