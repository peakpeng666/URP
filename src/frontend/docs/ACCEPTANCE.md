# 实际验收记录

日期：2026-10-06（Asia/Tokyo）。主产品运行于 http://127.0.0.1:4173。科学核验、产品浏览器、迁移与包内历史审计分别记录。浏览器总索引是 artifacts/browser_acceptance.json，其中11个套件均为生产构建PASS；较早的失败截图和日志保留为开发历史，不作为当前状态。

| 范围 | 实际结果 | 证据 |
| --- | --- | --- |
| 原 ZIP 与导入 | PASS：25,366,752字节、1915成员、1914 MANIFEST哈希；差一项为清单自身 | artifacts/import_report.json |
| 独立科学核验 | PASS：264输入、768 runs、3,840,000步、120选择、264共同前缀、4风险组、18单元、10000历史bootstrap、284冻结哈希 | artifacts/validation_report.json |
| 锁定运行环境 | WSL Ubuntu22.04；Python3.10.12、NumPy2.2.6、Node24.11.1、npm11.6.2 | validation_report.json；clean_rebuild.json的environment |
| Python与导出一致性 | 26项通过：故障注入、信任/工程边界，以及全量输入、轨迹、决策和来源字节导出一致性 | artifacts/integration-tests.log；干净重建test日志 |
| 回放内核与加载 | 23项通过：全部768终态、随机定位、同步、稀疏槽、取消/旧响应、SHA256、损坏语义拒绝 | 同上；tests/replay*.mjs |
| 冻结模型前端复算 | 4项通过，覆盖120选择；特征最大误差8.33e-17，平方距离1.11e-16 | artifacts/integration-tests.log；干净重建test日志 |
| 前端路由回归 | 5项通过；最终统一测试包含上述4项复算，共9项Vitest | 干净重建test日志 |
| 生产构建 | 类型检查及Vite构建通过；字体、图标、依赖本地打包 | artifacts/production-build.log |
| 总览 | 5/5 PASS：主指标、108点、收益方向、抽屉焦点、尺寸适配 | product-overview/overview-report.json |
| 缺失/损坏恢复 | 7/7 PASS：坏URL、404/无效JSON、FAIL状态、缺失CI、有效但篡改的bootstrap拒绝 | product-errors/errors-report.json |
| 样本与风险 | 9/9 PASS：264/144计数及缺失语义、筛选/搜索/刷新、返回、首行点击、训练无效筛选、悬停可读、4组12未来 | product-browse/browse-report.json |
| 回放产品操作 | 12/12 PASS：端点、随机定位、两支同步、键盘、播放/500暂停、观察/事后、训练策略、切换、错误重试保持500、同页地址及历史定位无循环 | product-functional.json |
| 触摸与适配 | 43/43 PASS：六配置布局、真实端点、拖动、播放暂停、导航返回、同流地址项数同步、减少动效初态暂停 | product-mobile/mobile-report.json |
| 最后短屏布局调整 | 横屏时间栏改正常文档流并前置，避免覆盖画布；受影响横屏7/7定点复验，其他已通过配置不无故重跑 | product-mobile/mobile-report-844x390-landscape-touch.json |
| 证据链 | 9/9 PASS：预览/下载/哈希同字节、MANIFEST根绑定及自核验、篡改/交替响应/伪清单拒绝、切策略/流重置、旧核验迟到隔离 | product-evidence/evidence-report.json |
| Canvas与曲线 | 最大真实样本4719箱=4719绘制条，0裁切；曲线端点及同前缀已知轴2/2 PASS | canvas-audit/canvas-audit.json；curve-audit.json |
| 五页截图及请求 | 27组页面/视口完成真实内容加载，无整页横溢、运行时异常或外部请求；另存一组CSS缩放诊断 | product/visual-report.json |
| 真正浏览器200%缩放 | 总览与回放PASS；回放缩放后滑块500→501→500可达且稳定 | product-browser-zoom/browser-zoom.json；product-replay-browser-zoom/browser-zoom.json |
| WSL干净重建 | 独立报告记录安装→转换→全量核验→刷新状态→测试→构建六步；仅status=PASS且执行期源码无变更才成立 | artifacts/clean_rebuild.json；artifacts/clean_rebuild_logs/ |

表中简写的产品报告路径位于 artifacts/codex-browser/，命令日志在 artifacts/final-browser-logs/。迁移最终统一测试为26 Python + 23 Node + 9 Vitest，具体退出码与原始输出直接保存在干净重建日志；早期4项前端测试不冒充最终9项。

尺寸覆盖360×800、390×844、430×932、1366×900、1920×1080，以及844×390横屏、900×1366竖屏。根代理目检桌面总览/回放/样本/证据、三种手机宽度、风险组、横屏与真实200%缩放截图；截图等待懒加载、数据和字体完成，加载占位壳不算验收。最新主要图片在product/，专项交互截图在各报告旁。

真实浏览器缩放由隔离临时扩展调用Chrome tabs.setZoom/getZoom=2；实测1366→683 CSS px、DPR1→2、visualViewport.scale=1。未手动点击工具栏菜单，CSS zoom、DPR模拟、CDP pinch独立记录，不混作浏览器缩放。CSS zoom诊断可能有不同布局行为，不参与真实tab zoom的PASS判定。

复现：先运行 bash scripts/console.sh browser-setup --with-deps，在另一终端完成build和serve，再执行 bash scripts/browser_acceptance.sh。它串行执行11套检查并生成总索引；开发阶段的定点补测保留各自范围。

preview/ 的独立验收页12项PASS仅用于早期接口核对，不冒充正式产品；最终产品以根目录src/的构建为准。

未测/限制：真实手机、原生Ubuntu22.04未实机验证；未开启局域网；视觉参考图未查看；未认证完整历史900 CPU秒预算；未重跑历史策略评分、768次策略实验、训练或调参。科学复核恢复既有分配并核对冻结模型的记录算术，保留历史审计的验证器中断与缓存版重新验证说明。
