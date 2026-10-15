import { Page } from '../shell/Page';
import { Card,Notice } from '../ui';
export function Archive(){return <Page title="实验档案" subtitle="当前实验与历史资料分别保留"><Card title="当前科研实验"><p>本次求解与仿真记录保存在本机，每条记录提供 JSON / CSV 导出。</p><p><a href="#/runs">打开运行记录</a></p></Card><Notice>历史 BPP 原始归档尚未恢复，不显示虚构实验数据。<a href="#/bpp">检查 BPP 历史数据状态</a></Notice></Page>;}
