# 科研面板

React/Vite面板展示BPP结果、逐步装箱回放、选择解释、同前缀风险和原始证据。

从本目录运行：

```sh
bash scripts/console.sh build
bash scripts/console.sh serve      # 127.0.0.1:4173
bash scripts/console.sh dev
bash scripts/console.sh test
```

| 内容 | 位置 |
|---|---|
| 页面与交互 | `src/` |
| 装箱回放与数据读取 | `core/` |
| 路线检查与文件适配 | [core/routing](core/routing/README.md) |
| 原始输入 | `inputs/` → `../../data/bpp/inputs` |
| 实验记录 | `research/` → `../../data/bpp/records` |
| 展示数据 | `public/data/` → `../../../data/bpp/exports` |

当前页面读取静态记录；下一步连接[后端API](../backend/api.md)，复用路线组件增加路线结果视图。

[设计与交互](docs/FRONTEND.md) · [静态数据接口](docs/DATA_API.md) · [安装与迁移](docs/MIGRATION.md) · [验收](docs/ACCEPTANCE.md)。
