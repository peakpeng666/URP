# 科研记录后端

Python标准库与SQLite实现本地实验包导入、结果查询、附件下载、同口径比较和路线读取。当前记录包为selector、budget、fleet、turns和bpp-history。

```sh
cd src/backend
python3 -m backend --db ../../data/backend/research.sqlite3 list
python3 -m backend --db ../../data/backend/research.sqlite3 serve --import-root ../../data/packages --port 4180
```

`packages`连接到`../../data/packages`。新数据库使用`bootstrap --package-root packages`导入；相同内容重复导入保持幂等。`--db`须放在子命令前，可指定独立数据库。

[API与数据口径](api.md) · [路线格式](docs/) · [源码来源](config/sources.json)。研究执行由`src/research`承担。

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
RESEARCH_CONSOLE_PACKAGE_ROOT=packages python3 -m unittest discover -s tests -p integration_backend.py
```

历史记录中的派生数据库位于URP根目录相对路径 `data/backend/research.sqlite3`，从本组件目录访问为 `../../data/backend/research.sqlite3`；来源与验证记录为同目录 `SOURCE.json`。历史记录为9个实验、672条路线，当前数据库内容与导入可用性尚未重新验收。
