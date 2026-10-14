# URP

面向农业机器人的路径规划算法库构建与智能推荐研究，以老师的LLM自动算法设计指南为主线。

**[CVRPLIB当前入口](experiments/CVRPLIB入口.md) · [下一阶段](下一阶段.md) · [当前实验进度](experiments/状态.md) · [老师要求与成果](materials/学习/老师要求与进度.md) · [按需取用](按需取用.md)**

项目包含源码、论文精读、论文原文、教材、算例和实验原始记录。[私有云盘](https://drive.google.com/drive/folders/1ZpHAznk36B-PVwL19lo_-kulRF3pwtBY)与[私有GitHub仓库](https://github.com/peakpeng666/URP)保存同一项目；范围和来源记录见[storage.json](storage.json)。

| 内容 | 入口 |
|---|---|
| 论文精读与研究分析 | [literature](literature/README.md) · [综合分析](literature/综合分析.md) |
| 实验报告、源码和结果 | [experiments](experiments/README.md) · [实验目录](experiments/目录.md) |
| 研究实现与软件 | [src](src/README.md) |
| 外部论文代码 | [代码目录](src/repos/README.md) |
| 论文原文 | [papers](papers/README.md) |
| 老师指南、学习手册和项目材料 | [materials](materials/README.md) |
| 输入、算例与记录包 | [data](data/README.md) |

## 本机启动

```sh
bash src/start.sh backend
bash src/start.sh frontend
```

前端为BPP静态结果面板，后端提供实验记录API；两者待接通。[src/checks.json](src/checks.json)保存2026年10月10日的253项历史PASS；全库目录、前后端和用户主机环境尚未重新验收。2026年10月14日已单独完成CVRPLIB运行前验收及来源核验，范围见[当前入口](experiments/CVRPLIB入口.md)，不据此声称全库测试或构建通过。

