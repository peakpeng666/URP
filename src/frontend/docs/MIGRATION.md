# 安装、离线运行与迁移

本项目消费随包提供的历史实验。转换和验证只读原始输入，恢复已记录的轨迹，不启动实验 runner、不重新训练。所有脚本从自身位置定位项目，项目可迁移到其他路径。

## 运行环境

本机使用Ubuntu 22.04、Python 3.10.12、Node.js 24.11.1与npm 11.6.2。运行检查见[当前记录](../../checks.json)，浏览器交互的原始验收记录见[ACCEPTANCE.md](ACCEPTANCE.md)。

Python 使用项目内隔离 `.venv`，`requirements.lock` 固定 NumPy 2.2.6，并列出官方发布文件 SHA256；安装只接受锁定的 wheel。支持 Python 3.10–3.13，建议 Ubuntu 22.04 自带 Python 3.10。版本/文件来源：[NumPy 2.2.6 官方 PyPI 元数据](https://pypi.org/project/numpy/2.2.6/)。Node/npm 使用与本机一致的版本，并以 `package-lock.json` 执行 `npm ci`。不迁移 `.venv` 或 `node_modules`。

Ubuntu 上需预装 Python 与 venv 支持，以及 Node/npm。若 `python3 -m venv` 报缺少 ensurepip，请安装 `python3-venv` 后重试。安装依赖时需要网络；数据转换完成后，工作台运行不依赖远程 API、模型、登录或数据库。

中文显示使用本机字体回退，拉丁字体随前端依赖在构建中打包。Ubuntu 最小安装请在联网安装阶段执行 `sudo apt-get install python3-venv fonts-noto-cjk`，以便随后离线正确显示中文；不依赖 Google Fonts 等远程字体请求。

## 从交付包启动

先用 ZIP 旁的 `.sha256` 校验交付包，再解压并进入包内 `bpp-research-console` 文件夹。ZIP 中 `DELIVERY_MANIFEST.json` 记录交付文件的大小和 SHA256；该清单描述文件完整性，不代表科学核验或浏览器验收自动通过。

```bash
sha256sum -c bpp-research-console-delivery.zip.sha256
unzip bpp-research-console-delivery.zip
cd bpp-research-console
bash scripts/console.sh setup
bash scripts/console.sh data-convert
bash scripts/console.sh validate
bash scripts/console.sh test
bash scripts/console.sh build
bash scripts/console.sh serve
```

默认构建预览地址为 `http://127.0.0.1:4173`，只绑定本机回环地址。开发时使用 `bash scripts/console.sh dev`，地址以终端实际输出为准。没有默认开启局域网或手机真机访问。端口可用 `BPP_PORT=4174 bash scripts/console.sh serve` 调整。

Windows 用户在 Ubuntu WSL 终端执行上述命令，不使用 Windows Python/Node 创建第二套环境。不要从 Windows 复制 Python 虚拟环境到 Ubuntu。位于挂载盘的工作区可以直接运行；若产生文件监听问题，再将源码与原始 ZIP 复制到 WSL 本地目录重新执行安装和转换。

## 浏览器验收环境

日常浏览工作台不要求安装 Playwright；自动化浏览器验收另使用 `tools/browser/package.json` 和其锁文件固定 Playwright 1.63.0，避免代替或改变产品前端的技术选型。迁移后要重跑浏览器验收时，在项目根目录执行：

```bash
sudo apt-get update
sudo apt-get install -y fonts-noto-cjk
bash scripts/console.sh browser-setup --with-deps
fc-match 'Noto Sans CJK SC'
```

上述步骤首次会下载浏览器和必要系统依赖。浏览器缓存不随交付包搬运；WSL 中曾实测缺少 `libasound.so.2`，由 Ubuntu 包 `libasound2` 提供，完整 `--with-deps` 安装可补齐依赖。无中文字体时 DOM 文本仍可能正确但截图显示方框，因此验收须使用实际中文字体。浏览器实际启动及字体选择结果见 `artifacts/browser_environment.json`（仅在该报告实际存在时成立）。

## 数据与交付内容

交付 ZIP 包含完整原始实验 ZIP，原包 SHA256 为 `5f47d49fade8f926bb5751818b038288a772b711d4249d70a7a392eeb9719350`。原 ZIP 在 `inputs/`，运行导入后核对 ZIP 路径、MANIFEST 成员、字节数和哈希，安全解压到 `research/`。派生静态接口写入 `public/data/`。这两个生成目录不需要随包搬运，必须从原 ZIP 重建。

若通过源码仓库取得项目而没有原始 ZIP，将原实验包放入 `inputs/` 再执行转换。不要替换为测试夹具。`data-convert` 会在导入异常时停止。原始输入不加入 Git。

打包命令 `bash scripts/console.sh package` 默认生成 `delivery/bpp-research-console-delivery.zip` 和同名 `.sha256`。打包白名单包括源码、锁文件、说明、测试、输入 ZIP 和实际存在的 `artifacts/` 报告/截图，排除 `research/`、`public/data/`、`dist/`、环境缓存与备份。打包过程验证所有归档成员，但不替代完整安装、转换、测试和构建。

## 验收与未覆盖范围

数据、回放、浏览器和迁移分别留证；以交付包内 `artifacts/` 和验收文档的实际运行结果为准。历史包内审计与当前项目的新核验不是同一结论。

已完成 Python 部分早检：在另一 `/tmp/bpp-python-portability-*` 空目录仅复制 setup/console 脚本和 `requirements.lock`，从项目目录之外调用 `setup --python-only`，隔离安装 NumPy 2.2.6 成功；记录见 `artifacts/python_portability.json` 与日志。打包工具独立夹具的白名单、嵌套截图收集、成员哈希/外部校验和、符号链接拒绝检查通过，见 `artifacts/engineering_smoke.json`。两者均不代表完整应用迁移通过。

完整 WSL 干净重建的实际结果见 artifacts/clean_rebuild.json：只有 status=PASS、六步骤成功且 source_changed_during_run 为空，才能记录“WSL 干净重建通过”。它在另一个空目录仅凭白名单源码、原 ZIP 与锁文件重建，不复制旧报告、派生数据或环境。报告保留实际目录、版本、命令、退出码和日志。原生 Ubuntu、真实手机均未验证。

可复用的重建命令为 `python3 scripts/clean_rebuild.py --parent /tmp`。它创建新的项目外目录，只复制白名单源码、锁文件与原 ZIP，明确排除旧 `artifacts/`、派生数据、依赖目录和构建输出，执行安装→转换→科学核验→刷新核验元数据→测试→构建。执行计划可先用 `--plan` 查看；`--stage-only` 仅复制文件，其结果为 `STAGED_NOT_EXECUTED`，不代表迁移通过。

新证据写入原项目 `artifacts/clean_rebuild.json` 和 `artifacts/clean_rebuild_logs/`，包含命令、退出码、环境版本、每步日志、全部输入源码的哈希和执行期间的文件变化。执行期间若源码变化，已通过的快照被标为 `STALE`，避免把过期快照等同于当前源码。临时目录保留便于复查，不自动删除用户文件。默认 `console.sh validate` 通过后会刷新现有静态接口的验证元数据；提供自定义参数时只运行验证器，不猜测自定义输出的位置。
