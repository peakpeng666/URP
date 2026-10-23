# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: d-import-idempotency.spec.ts >> D 导入幂等：丢失响应后重新导入，场景列表无重复
- Location: tests/d-import-idempotency.spec.ts:3:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('region', { name: '农业任务目录' }).locator('details').first().getByRole('alert')
Expected: visible
Error: strict mode violation: getByRole('region', { name: '农业任务目录' }).locator('details').first().getByRole('alert') resolved to 2 elements:
    1) <div role="alert">…</div> aka getByRole('alert').first()
    2) <div role="alert" class="_notice_a5ga1_446 _notice_error_a5ga1_467">…</div> aka getByRole('alert').nth(1)

Call log:
  - Expect "toBeVisible" getByRole('region', { name: '农业任务目录' }).locator('details').first().getByRole('alert') with timeout 30000ms
  - waiting for getByRole('region', { name: '农业任务目录' }).locator('details').first().getByRole('alert')

```

# Page snapshot

```yaml
- generic [ref=e2]:
  - banner [ref=e3]:
    - generic [ref=e4]: 农业机器人路径规划
    - generic [ref=e10]:
      - generic [ref=e11]:
        - textbox "任务描述" [ref=e15]:
          - /placeholder: 用一句话描述任务，例如：在 200×120 米的果园里，3 台机器人从西南角出发采样 40 个点，避开两个池塘
        - button "示例" [ref=e16] [cursor=pointer]
      - button "生成地图" [disabled] [ref=e19]
      - button "导入" [ref=e23] [cursor=pointer]
    - generic [ref=e27]:
      - group "工作区" [ref=e28]:
        - button "任务规划" [pressed] [ref=e29] [cursor=pointer]
        - button "资产库" [ref=e32] [cursor=pointer]
        - button "算法实验" [ref=e43] [cursor=pointer]
        - button "仿真" [ref=e46] [cursor=pointer]
        - button "资料" [ref=e50] [cursor=pointer]
        - button "系统" [ref=e53] [cursor=pointer]
      - button "恢复当前工作区的默认布局" [ref=e57] [cursor=pointer]
      - button "⌘K" [ref=e61] [cursor=pointer]
  - generic [ref=e66]:
    - generic [ref=e76]:
      - generic [ref=e83]:
        - region "场景库" [ref=e85]:
          - tablist [ref=e88]:
            - tab "场景库" [selected] [ref=e89] [cursor=pointer]:
              - generic [ref=e90]:
                - generic [ref=e91]: 场景库
                - button "Close 场景库" [ref=e92]
          - tabpanel "场景库" [ref=e96]:
            - generic [ref=e98]:
              - button "返回已有场景" [expanded] [ref=e100] [cursor=pointer]
              - region "农业任务目录" [ref=e102]:
                - paragraph [ref=e103]: 选择农业任务并调整参数，保存后进入现有任务规划流程。
                - generic [ref=e104]:
                  - text: 生产环境
                  - combobox "生产环境" [ref=e105]:
                    - option "全部环境" [selected]
                    - option "大田与旱作地"
                    - option "水田"
                    - option "果园"
                    - option "葡萄园"
                    - option "茶园"
                    - option "设施温室"
                    - option "苗圃"
                    - option "丘陵梯田"
                    - option "牧草地与牧场"
                    - option "畜禽养殖设施"
                    - option "农场仓储与装卸区"
                    - option "多田块农场及连接路网"
                    - option "水产养殖水面"
                    - option "农业空域（无人机）"
                - generic [ref=e106]:
                  - text: 农业作业
                  - combobox "农业作业" [ref=e107]:
                    - option "全部作业" [selected]
                    - option "耕整地"
                    - option "播种"
                    - option "移栽"
                    - option "中耕"
                    - option "植保（全田喷施）"
                    - option "植保（选择性/斑块）"
                    - option "植保（逐株定点）"
                    - option "除草（机械）"
                    - option "施肥（变量追肥）"
                    - option "土壤及作物采样"
                    - option "环境监测"
                    - option "逐株检查"
                    - option "灌溉设施巡检"
                    - option "采收"
                    - option "果园修剪"
                    - option "接粮与运输"
                    - option "联合收获"
                    - option "草捆收集"
                    - option "秸秆处理"
                    - option "割草"
                    - option "搂草"
                    - option "打捆"
                    - option "苗木及物料搬运"
                    - option "饲喂"
                    - option "推料"
                    - option "圈舍清扫"
                    - option "补水补药（站点补给）"
                    - option "充电（充电桩调度）"
                    - option "卸载（港池/粮库排队）"
                    - option "入库与转场"
                - generic [ref=e108]:
                  - text: 模式状态
                  - combobox "模式状态" [ref=e109]:
                    - option "全部状态" [selected]
                    - option "可构建模板"
                    - option "近似模板"
                    - option "提案（不可提交）"
                - paragraph [ref=e110]: 当前 39 个模式
                - generic [ref=e111]:
                  - button "下载完整矩阵 JSON" [ref=e112] [cursor=pointer]
                  - button "下载完整矩阵 CSV" [ref=e113] [cursor=pointer]
                - group [ref=e115]:
                  - generic "果园采收集运 · 可构建模板" [ref=e116]
                  - paragraph [ref=e117]: 采摘点（树位/行间集中点）带载果需求，车辆沿行间通道收集并卸至田头装车点，多趟往返。
                  - paragraph [ref=e118]: 采摘点是真实的带需求点集（点集 + 容量 + 卸载），不是行服务的近似；行间通行用 travel=rows 的真实通道图，地头/机耕路为开阔区。
                  - paragraph [ref=e119]: 目标：点集（可带需求） / 容量车辆路径
                  - list [ref=e120]:
                    - listitem [ref=e121]: 定义：yes · 任务、容量、卸载点、行间通行均有契约字段。
                    - listitem [ref=e122]: 编辑：yes · 任务点、车库、容量、需求在既有地图编辑器全部可改。
                    - listitem [ref=e123]: 求解：yes · fleet_routing 原生语义：点集需求 + 容量 + unload_points 卸货 + rows 通行。
                    - listitem [ref=e124]: 验算：yes · fleet.check 独立复算容量、趟次、作业位置与通行约束（rows 时重生成作物行核对路线不斜穿作物）。
                    - listitem [ref=e125]: 仿真：partial · 同构差速、无曲率约束、≤15 台时可申请进入生成的田间 Gazebo 世界（串行预约执行）；其余组合执行入口按契约返回 422。
                    - listitem [ref=e126]: 实验：no · 本版本模板尚无关联的持久化运行证据；请提交真实求解并检查独立验算结果，不将历史文案视为通过。
                  - figure [ref=e127]:
                    - img "果园采收集运 几何预览" [ref=e128]:
                      - generic "地块 地块1" [ref=e130]
                      - generic "障碍 O1（pond）" [ref=e131]
                      - generic "采摘点1，需求 200，(114.29, 102.56) m" [ref=e132] [cursor=pointer]
                      - generic "采摘点2，需求 200，(139.68, 102.56) m" [ref=e134] [cursor=pointer]
                      - generic "采摘点3，需求 200，(95.08, 96.56) m" [ref=e136] [cursor=pointer]
                      - generic "采摘点4，需求 200，(95.21, 66.56) m" [ref=e138] [cursor=pointer]
                      - generic "采摘点5，需求 200，(149.73, 102.56) m" [ref=e140] [cursor=pointer]
                      - generic "采摘点6，需求 200，(119.96, 48.56) m" [ref=e142] [cursor=pointer]
                      - generic "采摘点7，需求 200，(24.14, 102.56) m" [ref=e144] [cursor=pointer]
                      - generic "采摘点8，需求 200，(95.09, 96.56) m" [ref=e146] [cursor=pointer]
                      - generic "采摘点9，需求 200，(51.07, 48.56) m" [ref=e148] [cursor=pointer]
                      - generic "采摘点10，需求 200，(109.64, 102.56) m" [ref=e150] [cursor=pointer]
                      - generic "采摘点11，需求 200，(98.22, 78.56) m" [ref=e152] [cursor=pointer]
                      - generic "采摘点12，需求 200，(142.82, 42.56) m" [ref=e154] [cursor=pointer]
                      - generic "采摘点13，需求 200，(104.38, 24.56) m" [ref=e156] [cursor=pointer]
                      - generic "采摘点14，需求 200，(126.8, 42.56) m" [ref=e158] [cursor=pointer]
                      - generic "采摘点15，需求 200，(82.88, 30.56) m" [ref=e160] [cursor=pointer]
                      - generic "采摘点16，需求 200，(123.43, 72.56) m" [ref=e162] [cursor=pointer]
                      - generic "采摘点17，需求 200，(91.14, 102.56) m" [ref=e164] [cursor=pointer]
                      - generic "采摘点18，需求 200，(50.51, 96.56) m" [ref=e166] [cursor=pointer]
                      - generic "采摘点19，需求 200，(48.16, 66.56) m" [ref=e168] [cursor=pointer]
                      - generic "采摘点20，需求 200，(108.77, 18.56) m" [ref=e170] [cursor=pointer]
                      - generic "采摘点21，需求 200，(113.64, 102.56) m" [ref=e172] [cursor=pointer]
                      - generic "采摘点22，需求 200，(133.48, 66.56) m" [ref=e174] [cursor=pointer]
                      - generic "采摘点23，需求 200，(147.17, 78.56) m" [ref=e176] [cursor=pointer]
                      - generic "采摘点24，需求 200，(45.96, 60.56) m" [ref=e178] [cursor=pointer]
                      - generic "采摘点25，需求 200，(101.52, 84.56) m" [ref=e180] [cursor=pointer]
                      - generic "采摘点26，需求 200，(47.81, 36.56) m" [ref=e182] [cursor=pointer]
                      - generic "采摘点27，需求 200，(51.38, 96.56) m" [ref=e184] [cursor=pointer]
                      - generic "采摘点28，需求 200，(114.38, 84.56) m" [ref=e186] [cursor=pointer]
                      - generic "采摘点29，需求 200，(147.17, 48.56) m" [ref=e188] [cursor=pointer]
                      - generic "采摘点30，需求 200，(43.75, 60.56) m" [ref=e190] [cursor=pointer]
                      - generic "采摘点31，需求 200，(107.36, 12.56) m" [ref=e192] [cursor=pointer]
                      - generic "采摘点32，需求 200，(97.93, 72.56) m" [ref=e194] [cursor=pointer]
                      - generic "采摘点33，需求 200，(117.06, 48.56) m" [ref=e196] [cursor=pointer]
                      - generic "采摘点34，需求 200，(77.34, 96.56) m" [ref=e198] [cursor=pointer]
                      - generic "采摘点35，需求 200，(99.19, 54.56) m" [ref=e200] [cursor=pointer]
                      - generic "采摘点36，需求 200，(110.8, 18.56) m" [ref=e202] [cursor=pointer]
                      - generic "库点 1" [ref=e204]
                      - generic "卸货点 1" [ref=e205]
                      - generic [ref=e206]: 原点 (0,0) · x→ y↑
                      - generic [ref=e208]: 50 m
                    - generic [ref=e210]:
                      - text: 36 个服务对象，1 个库点，1 个卸货点，车体半径 0.75 m。 范围 180.0 × 120.0 m。图例：圆为服务对象，方块为库点或起点，三角为卸货点，斜线填充为障碍，虚线为地块，红色和感叹号为问题。
                      - group "图层" [ref=e211]:
                        - generic [ref=e212]:
                          - checkbox "地块" [checked] [ref=e213]
                          - text: 地块
                        - generic [ref=e214]:
                          - checkbox "障碍" [checked] [ref=e215]
                          - text: 障碍
                        - generic [ref=e216]:
                          - checkbox "服务对象" [checked] [ref=e217]
                          - text: 服务对象
                        - generic [ref=e218]:
                          - checkbox "库点/卸货点" [checked] [ref=e219]
                          - text: 库点/卸货点
                        - generic [ref=e220]:
                          - checkbox "问题标记" [checked] [ref=e221]
                          - text: 问题标记
                  - group [ref=e222]:
                    - generic [ref=e223]:
                      - text: 田块宽度 (m)
                      - spinbutton "果园采收集运 田块宽度" [ref=e224]: "180"
                    - generic [ref=e225]:
                      - text: 田块高度 (m)
                      - spinbutton "果园采收集运 田块高度" [ref=e226]: "120"
                    - generic [ref=e227]:
                      - text: 行向角 (°)
                      - spinbutton "果园采收集运 行向角" [ref=e228]: "0"
                    - generic [ref=e229]:
                      - text: 任务点数
                      - spinbutton "果园采收集运 任务点数" [ref=e230]: "36"
                    - generic [ref=e231]:
                      - text: 单点需求
                      - spinbutton "果园采收集运 单点需求" [ref=e232]: "200"
                    - generic [ref=e233]:
                      - text: 车辆数
                      - spinbutton "果园采收集运 车辆数" [ref=e234]: "3"
                    - generic [ref=e235]:
                      - text: 单车容量
                      - spinbutton "果园采收集运 单车容量" [ref=e236]: "1200"
                    - generic [ref=e237]:
                      - text: 行驶速度 (m/s)
                      - spinbutton "果园采收集运 行驶速度" [ref=e238]: "0.8"
                    - generic [ref=e239]:
                      - text: 机器人半径 (m)
                      - spinbutton "果园采收集运 机器人半径" [ref=e240]: "0.75"
                    - generic [ref=e241]:
                      - text: 车库位置
                      - combobox "果园采收集运 车库位置" [ref=e242]:
                        - option "西南角" [selected]
                        - option "北侧机耕路"
                        - option "东侧机耕路"
                    - generic [ref=e243]:
                      - text: 优化目标
                      - combobox "果园采收集运 优化目标" [ref=e244]:
                        - option "均衡完成时间" [selected]
                        - option "总里程"
                    - generic [ref=e245]:
                      - text: 田头补给/卸载点
                      - checkbox "果园采收集运 田头补给/卸载点" [checked] [ref=e246]
                    - generic [ref=e247]:
                      - text: 内部障碍数
                      - spinbutton "果园采收集运 内部障碍数" [ref=e248]: "1"
                    - generic [ref=e249]:
                      - text: 障碍半径 (m)
                      - spinbutton "果园采收集运 障碍半径" [ref=e250]: "12"
                    - generic [ref=e251]:
                      - text: 随机种子
                      - spinbutton "果园采收集运 随机种子" [ref=e252]: "9091"
                    - button "下载原始场景 JSON" [ref=e253] [cursor=pointer]
                    - button "清除草稿并恢复默认" [ref=e254] [cursor=pointer]
                    - button "校验并导入任务规划" [ref=e255] [cursor=pointer]
                  - paragraph [ref=e256]: 保存后可继续编辑地图、选择算法并求解；仿真可用性由当前场景与车型决定。
                  - alert [ref=e257]:
                    - alert [ref=e258]:
                      - generic [ref=e261]: 请先核对保存结果（agri-orchard-harvest-tran-fe4d29e4-57e6-46fa-b368-aded8860c46f）：连接不上工作台服务（127.0.0.1:4100）。再次点击将先查询该场景。
                - group [ref=e263]:
                  - generic "果园植保（离散喷施点近似） · 近似模板" [ref=e264]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e266]:
                  - generic "大田接粮运输（固定装载点） · 可构建模板" [ref=e267]
                  - option "西南角"
                  - option "北侧机耕路" [selected]
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e269]:
                  - generic "土壤与作物采样 · 可构建模板" [ref=e270]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间"
                  - option "总里程" [selected]
                - group [ref=e272]:
                  - generic "定点变量除草 · 可构建模板" [ref=e273]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间"
                  - option "总里程" [selected]
                - group [ref=e275]:
                  - generic "温室采收物流 · 可构建模板" [ref=e276]
                  - option "西南角"
                  - option "北侧机耕路"
                  - option "东侧机耕路" [selected]
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e278]:
                  - generic "多田块机群作业分配 · 近似模板" [ref=e279]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e281]:
                  - generic "牧场与草地巡检 · 可构建模板" [ref=e282]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间"
                  - option "总里程" [selected]
                - group [ref=e284]:
                  - generic "茶园鲜叶集运 · 近似模板" [ref=e285]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e287]:
                  - generic "草捆收集运输 · 可构建模板" [ref=e288]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e290]:
                  - generic "异构机队集运（大小车混编） · 可构建模板" [ref=e291]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e293]:
                  - generic "不可倒车车辆转场（Dubins 曲率约束） · 可构建模板" [ref=e294]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间"
                  - option "总里程" [selected]
                - group [ref=e296]:
                  - generic "大田耕整全覆盖 · 可构建模板" [ref=e297]
                  - option "往复（boustrophedon）" [selected]
                  - option "蛇形"
                  - option "螺旋"
                - group [ref=e299]:
                  - generic "含障碍田块覆盖 · 可构建模板" [ref=e300]
                - group [ref=e302]:
                  - generic "无人机田区航测（平面近似） · 近似模板" [ref=e303]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e305]:
                  - generic "水田秧苗/稻谷转运（无下陷近似） · 近似模板" [ref=e306]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e308]:
                  - generic "葡萄园植保（行间近似） · 近似模板" [ref=e309]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e311]:
                  - generic "牛舍推料（通道近似） · 近似模板" [ref=e312]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e314]:
                  - generic "苗圃盆苗集运（无配对近似） · 近似模板" [ref=e315]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e317]:
                  - generic "梯田集运（无坡度近似） · 近似模板" [ref=e318]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e320]:
                  - generic "水产养殖投喂巡检（水面近似） · 近似模板" [ref=e321]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e323]:
                  - generic "温室轨道巡检（自由点访问代理） · 近似模板" [ref=e324]
                  - option "西南角" [selected]
                  - option "北侧机耕路"
                  - option "东侧机耕路"
                  - option "均衡完成时间" [selected]
                  - option "总里程"
                - group [ref=e326]:
                  - generic "行服务 CARP（果树/大田逐行作业） · 提案（不可提交）" [ref=e327]
                - group [ref=e329]:
                  - generic "地头转弯模式优化（B-pattern） · 提案（不可提交）" [ref=e330]
                - group [ref=e332]:
                  - generic "压实约束路径（CTF 行走道） · 提案（不可提交）" [ref=e333]
                - group [ref=e335]:
                  - generic "牵引机具扫掠转弯校验 · 提案（不可提交）" [ref=e336]
                - group [ref=e338]:
                  - generic "斑块选择性覆盖（病虫草害） · 提案（不可提交）" [ref=e339]
                - group [ref=e341]:
                  - generic "坡地与梯田风险约束路径 · 提案（不可提交）" [ref=e342]
                - group [ref=e344]:
                  - generic "水田插秧行服务 · 提案（不可提交）" [ref=e345]
                - group [ref=e347]:
                  - generic "并行时空冲突调度（多机共道） · 提案（不可提交）" [ref=e348]
                - group [ref=e350]:
                  - generic "收割机—接粮车动态汇合 · 提案（不可提交）" [ref=e351]
                - group [ref=e353]:
                  - generic "空地协同（无人机+地面车） · 提案（不可提交）" [ref=e354]
                - group [ref=e356]:
                  - generic "采收时间窗（成熟度与冷链） · 提案（不可提交）" [ref=e357]
                - group [ref=e359]:
                  - generic "动态任务流（病虫草情即时报送） · 提案（不可提交）" [ref=e360]
                - group [ref=e362]:
                  - generic "动态障碍（牲畜/人员活动区） · 提案（不可提交）" [ref=e363]
                - group [ref=e365]:
                  - generic "定时饲喂班次（TMR 配送） · 提案（不可提交）" [ref=e366]
                - group [ref=e368]:
                  - generic "农场仓储出入库取送 · 提案（不可提交）" [ref=e369]
                - group [ref=e371]:
                  - generic "多塘水产转场（闸口连接） · 提案（不可提交）" [ref=e372]
                - group [ref=e374]:
                  - generic "无人机能耗覆盖航测 · 提案（不可提交）" [ref=e375]
        - generic [ref=e381]:
          - region "地图" [ref=e383]:
            - tablist [ref=e386]:
              - tab "地图" [selected] [ref=e387] [cursor=pointer]:
                - generic [ref=e388]:
                  - generic [ref=e389]: 地图
                  - button "Close 地图" [ref=e390]
            - tabpanel "地图" [ref=e394]
          - region "方案对比" [ref=e396]:
            - tablist [ref=e399]:
              - tab "方案对比" [selected] [ref=e400] [cursor=pointer]:
                - generic [ref=e401]:
                  - generic [ref=e402]: 方案对比
                  - button "Close 方案对比" [ref=e403]
              - tab "验算" [ref=e406] [cursor=pointer]
              - tab "实验结果" [ref=e409] [cursor=pointer]
              - tab "仿真回放" [ref=e412] [cursor=pointer]
              - tab "科研图表" [ref=e415] [cursor=pointer]
              - tab "日志" [ref=e418] [cursor=pointer]
            - tabpanel "方案对比" [ref=e422]:
              - generic [ref=e424]:
                - paragraph [ref=e434]: 还没有方案
                - paragraph [ref=e435]: 在“推荐与求解”里勾选算法后点击对比，结果会出现在这里。
        - region "推荐与求解" [ref=e437]:
          - tablist [ref=e440]:
            - tab "推荐与求解" [selected] [ref=e441] [cursor=pointer]:
              - generic [ref=e442]:
                - generic [ref=e443]: 推荐与求解
                - button "Close 推荐与求解" [ref=e444]
            - tab "检查器" [ref=e447] [cursor=pointer]
            - tab "决策记录" [ref=e450] [cursor=pointer]
          - tabpanel "推荐与求解" [ref=e454]:
            - paragraph [ref=e457]: 未打开场景
      - status [ref=e458]: 日志 opened
      - alert [ref=e459]
    - generic [ref=e462]:
      - paragraph [ref=e466]: 从一句话开始
      - paragraph [ref=e467]: 在上方输入任务描述并生成地图，或从左侧场景库打开一个场景。
  - contentinfo [ref=e468]:
    - generic [ref=e469]: 已连接
    - generic [ref=e471]: 求解空闲
    - generic [ref=e472]: 田间：未运行 · TB4：未运行
    - link "CVRP 数值任务" [ref=e476] [cursor=pointer]:
      - /url: "#/jobs"
    - link "BPP 历史" [ref=e477] [cursor=pointer]:
      - /url: "#/bpp"
  - generic [ref=e478]: 农业模板导入失败：请先核对保存结果（agri-orchard-harvest-tran-fe4d29e4-57e6-46fa-b368-aded8860c46f）：连接不上工作台服务（127.0.0.1:4100）。再次点击将先查询该场景。
```

# Test source

```ts
  1  | import { test, expect, shot, openAgriCatalog, firstRunnablePattern, listScenarios, API } from './helpers';
  2  | // catalog.ts:39-100 dedupes only in-flight imports in memory; a lost response + retry may duplicate on baseline.
  3  | test('D 导入幂等：丢失响应后重新导入，场景列表无重复', async ({ page }, info) => {
  4  |   const baseline = await listScenarios(page);
  5  |   await openAgriCatalog(page);
  6  |   const { card, name } = await firstRunnablePattern(page);
  7  |   await card.getByLabel(`${name} 随机种子`).fill('9091');
  8  |   await test.step('首次导入：服务端处理后丢弃响应', async () => {
  9  |     await page.route(`**${API}/scenarios`, async (route) => {
  10 |       if (route.request().method() !== 'POST') return route.fallback();
  11 |       await route.fetch(); // server commits
  12 |       await route.abort('connectionreset'); // client never sees it
  13 |     }, { times: 1 });
  14 |     await card.getByRole('button', { name: '校验并导入任务规划' }).click();
> 15 |     await expect(card.getByRole('alert')).toBeVisible({ timeout: 30_000 });
     |                                           ^ Error: expect(locator).toBeVisible() failed
  16 |     await shot(page, info, 'lost-response');
  17 |   });
  18 |   await test.step('重新导入同一参数', async () => {
  19 |     await card.getByRole('button', { name: '校验并导入任务规划' }).click();
  20 |     await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 });
  21 |     await shot(page, info, 'reimported');
  22 |   });
  23 |   await test.step('查询场景列表并断言无重复', async () => {
  24 |     const after = await listScenarios(page);
  25 |     const added = after.filter((s) => !baseline.some((b) => b.id === s.id));
  26 |     const titles = added.map((s) => s.title);
  27 |     info.annotations.push({ type: 'added', description: JSON.stringify(titles) });
  28 |     expect(added.length, `new scenarios: ${titles.join(', ')}`).toBe(1);
  29 |   });
  30 | });
  31 | 
```