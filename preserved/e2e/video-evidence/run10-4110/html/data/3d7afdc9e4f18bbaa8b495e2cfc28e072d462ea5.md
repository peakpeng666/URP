# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: g-solve-compare.spec.ts >> G2 cvrp-depot-floor：0 个已验算可行解为预期，并显示碰撞报告
- Location: tests/g-solve-compare.spec.ts:48:1

# Error details

```
Error: expect(locator).toHaveCount(expected) failed

Locator:  locator('[data-exclusion="map_collision"]')
Expected: 3
Received: 10
Timeout:  5000ms

Call log:
  - Expect "toHaveCount" locator('[data-exclusion="map_collision"]') with timeout 5000ms
  - waiting for locator('[data-exclusion="map_collision"]')
    14 × locator resolved to 10 elements
       - unexpected value "10"

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
              - button "打开农业任务目录" [ref=e100] [cursor=pointer]
              - generic [ref=e101]:
                - textbox "搜索场景" [ref=e103]
                - generic [ref=e104]: 导入 GeoJSON / 场景 JSON
                - generic [ref=e110]:
                  - generic [ref=e111]: 我的任务地图 · 12
                  - list [ref=e112]:
                    - listitem [ref=e113]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e114] [cursor=pointer]:
                        - generic [ref=e115]: 果园采收集运
                        - generic [ref=e116]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e117]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e118] [cursor=pointer]:
                        - generic [ref=e119]: 果园采收集运
                        - generic [ref=e120]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e121]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e122] [cursor=pointer]:
                        - generic [ref=e123]: 果园采收集运
                        - generic [ref=e124]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e125]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e126] [cursor=pointer]:
                        - generic [ref=e127]: 果园采收集运
                        - generic [ref=e128]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e129]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e130] [cursor=pointer]:
                        - generic [ref=e131]: 果园采收集运
                        - generic [ref=e132]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e133]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e134] [cursor=pointer]:
                        - generic [ref=e135]: 果园采收集运
                        - generic [ref=e136]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e137]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e138] [cursor=pointer]:
                        - generic [ref=e139]: 果园采收集运
                        - generic [ref=e140]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e141]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e142] [cursor=pointer]:
                        - generic [ref=e143]: 果园采收集运
                        - generic [ref=e144]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e145]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e146] [cursor=pointer]:
                        - generic [ref=e147]: 果园采收集运
                        - generic [ref=e148]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e149]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e150] [cursor=pointer]:
                        - generic [ref=e151]: 果园采收集运
                        - generic [ref=e152]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e153]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e154] [cursor=pointer]:
                        - generic [ref=e155]: 果园采收集运
                        - generic [ref=e156]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e157]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e158] [cursor=pointer]:
                        - generic [ref=e159]: 果园采收集运
                        - generic [ref=e160]: 多车任务 · 实地坐标 · 米 · 36 个任务
                - generic [ref=e161]:
                  - generic [ref=e162]: 仿真地图 · 8
                  - list [ref=e163]:
                    - listitem [ref=e164]:
                      - button "官方迷宫 · 双点巡检闭环 转弯约束路网 · 仿真地图 · maze · 2 个任务" [ref=e165] [cursor=pointer]:
                        - generic [ref=e166]: 官方迷宫 · 双点巡检闭环
                        - generic [ref=e167]: 转弯约束路网 · 仿真地图 · maze · 2 个任务
                    - listitem [ref=e168]:
                      - button "仓储货架通道 · 作物行代理 转弯约束路网 · 仿真地图 · warehouse · 5 个任务" [ref=e169] [cursor=pointer]:
                        - generic [ref=e170]: 仓储货架通道 · 作物行代理
                        - generic [ref=e171]: 转弯约束路网 · 仿真地图 · warehouse · 5 个任务
                    - listitem [ref=e172]:
                      - button "车间空地 · 欧氏 CVRP 车辆路径 CVRP · 仿真地图 · depot · 10 个任务" [ref=e173] [cursor=pointer]:
                        - generic [ref=e174]: 车间空地 · 欧氏 CVRP
                        - generic [ref=e175]: 车辆路径 CVRP · 仿真地图 · depot · 10 个任务
                    - listitem [ref=e176]:
                      - button "车间空地 · 内缩作业区覆盖 覆盖作业 · 仿真地图 · depot" [ref=e177] [cursor=pointer]:
                        - generic [ref=e178]: 车间空地 · 内缩作业区覆盖
                        - generic [ref=e179]: 覆盖作业 · 仿真地图 · depot
                    - listitem [ref=e180]:
                      - button "仓库 · 跨通道到达 点到点规划 · 仿真地图 · warehouse" [ref=e181] [cursor=pointer]:
                        - generic [ref=e182]: 仓库 · 跨通道到达
                        - generic [ref=e183]: 点到点规划 · 仿真地图 · warehouse
                    - listitem [ref=e184]:
                      - button "仓库 · 农机转弯半径 点到点规划 · 仿真地图 · warehouse" [ref=e185] [cursor=pointer]:
                        - generic [ref=e186]: 仓库 · 农机转弯半径
                        - generic [ref=e187]: 点到点规划 · 仿真地图 · warehouse
                    - listitem [ref=e188]:
                      - button "迷宫 · 对角穿越 点到点规划 · 仿真地图 · maze" [ref=e189] [cursor=pointer]:
                        - generic [ref=e190]: 迷宫 · 对角穿越
                        - generic [ref=e191]: 点到点规划 · 仿真地图 · maze
                    - listitem [ref=e192]:
                      - button "车间 · 可倒车泊位 点到点规划 · 仿真地图 · depot" [ref=e193] [cursor=pointer]:
                        - generic [ref=e194]: 车间 · 可倒车泊位
                        - generic [ref=e195]: 点到点规划 · 仿真地图 · depot
                - generic [ref=e196]:
                  - generic [ref=e197]: 基准算例 · 26
                  - list [ref=e198]:
                    - listitem [ref=e199]:
                      - button "转弯路网 g3x3_s8000_uturn 转弯约束路网 · 基准算例 · 5 个任务" [ref=e200] [cursor=pointer]:
                        - generic [ref=e201]: 转弯路网 g3x3_s8000_uturn
                        - generic [ref=e202]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e203]:
                      - button "转弯路网 g3x3_s8001_left_cost 转弯约束路网 · 基准算例 · 5 个任务" [ref=e204] [cursor=pointer]:
                        - generic [ref=e205]: 转弯路网 g3x3_s8001_left_cost
                        - generic [ref=e206]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e207]:
                      - button "转弯路网 g3x3_s8002_left_ban 转弯约束路网 · 基准算例 · 5 个任务" [ref=e208] [cursor=pointer]:
                        - generic [ref=e209]: 转弯路网 g3x3_s8002_left_ban
                        - generic [ref=e210]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e211]:
                      - button "转弯路网 g3x3_s8003_uturn 转弯约束路网 · 基准算例 · 5 个任务" [ref=e212] [cursor=pointer]:
                        - generic [ref=e213]: 转弯路网 g3x3_s8003_uturn
                        - generic [ref=e214]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e215]:
                      - button "转弯路网 g3x3_s8004_left_cost 转弯约束路网 · 基准算例 · 5 个任务" [ref=e216] [cursor=pointer]:
                        - generic [ref=e217]: 转弯路网 g3x3_s8004_left_cost
                        - generic [ref=e218]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e219]:
                      - button "转弯路网 g3x3_s8005_left_ban 转弯约束路网 · 基准算例 · 5 个任务" [ref=e220] [cursor=pointer]:
                        - generic [ref=e221]: 转弯路网 g3x3_s8005_left_ban
                        - generic [ref=e222]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e223]:
                      - button "转弯路网 g3x3_s10000_uturn 转弯约束路网 · 基准算例 · 5 个任务" [ref=e224] [cursor=pointer]:
                        - generic [ref=e225]: 转弯路网 g3x3_s10000_uturn
                        - generic [ref=e226]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e227]:
                      - button "转弯路网 g3x3_s10000_left_cost 转弯约束路网 · 基准算例 · 5 个任务" [ref=e228] [cursor=pointer]:
                        - generic [ref=e229]: 转弯路网 g3x3_s10000_left_cost
                        - generic [ref=e230]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e231]:
                      - button "转弯路网 g3x3_s10000_left_ban 转弯约束路网 · 基准算例 · 5 个任务" [ref=e232] [cursor=pointer]:
                        - generic [ref=e233]: 转弯路网 g3x3_s10000_left_ban
                        - generic [ref=e234]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e235]:
                      - button "转弯路网 g3x4_s10000_uturn 转弯约束路网 · 基准算例 · 6 个任务" [ref=e236] [cursor=pointer]:
                        - generic [ref=e237]: 转弯路网 g3x4_s10000_uturn
                        - generic [ref=e238]: 转弯约束路网 · 基准算例 · 6 个任务
                    - listitem [ref=e239]:
                      - button "转弯路网 g3x4_s10000_left_cost 转弯约束路网 · 基准算例 · 6 个任务" [ref=e240] [cursor=pointer]:
                        - generic [ref=e241]: 转弯路网 g3x4_s10000_left_cost
                        - generic [ref=e242]: 转弯约束路网 · 基准算例 · 6 个任务
                    - listitem [ref=e243]:
                      - button "转弯路网 g3x4_s10000_left_ban 转弯约束路网 · 基准算例 · 6 个任务" [ref=e244] [cursor=pointer]:
                        - generic [ref=e245]: 转弯路网 g3x4_s10000_left_ban
                        - generic [ref=e246]: 转弯约束路网 · 基准算例 · 6 个任务
                    - listitem [ref=e247]:
                      - button "转弯路网 g4x4_s10000_uturn 转弯约束路网 · 基准算例 · 7 个任务" [ref=e248] [cursor=pointer]:
                        - generic [ref=e249]: 转弯路网 g4x4_s10000_uturn
                        - generic [ref=e250]: 转弯约束路网 · 基准算例 · 7 个任务
                    - listitem [ref=e251]:
                      - button "转弯路网 g4x4_s10000_left_cost 转弯约束路网 · 基准算例 · 7 个任务" [ref=e252] [cursor=pointer]:
                        - generic [ref=e253]: 转弯路网 g4x4_s10000_left_cost
                        - generic [ref=e254]: 转弯约束路网 · 基准算例 · 7 个任务
                    - listitem [ref=e255]:
                      - button "转弯路网 g4x4_s10000_left_ban 转弯约束路网 · 基准算例 · 7 个任务" [ref=e256] [cursor=pointer]:
                        - generic [ref=e257]: 转弯路网 g4x4_s10000_left_ban
                        - generic [ref=e258]: 转弯约束路网 · 基准算例 · 7 个任务
                    - listitem [ref=e259]:
                      - button "夹具 dead_end_infeasible 转弯约束路网 · 基准算例 · 1 个任务" [ref=e260] [cursor=pointer]:
                        - generic [ref=e261]: 夹具 dead_end_infeasible
                        - generic [ref=e262]: 转弯约束路网 · 基准算例 · 1 个任务
                    - listitem [ref=e263]:
                      - button "夹具 single_customer_cycle 转弯约束路网 · 基准算例 · 1 个任务" [ref=e264] [cursor=pointer]:
                        - generic [ref=e265]: 夹具 single_customer_cycle
                        - generic [ref=e266]: 转弯约束路网 · 基准算例 · 1 个任务
                    - listitem [ref=e267]:
                      - button "夹具 g3x3_s7000_none 转弯约束路网 · 基准算例 · 4 个任务" [ref=e268] [cursor=pointer]:
                        - generic [ref=e269]: 夹具 g3x3_s7000_none
                        - generic [ref=e270]: 转弯约束路网 · 基准算例 · 4 个任务
                    - listitem [ref=e271]:
                      - button "欧氏 CVRP · 均匀分布 n=20 车辆路径 CVRP · 基准算例 · 20 个任务" [ref=e272] [cursor=pointer]:
                        - generic [ref=e273]: 欧氏 CVRP · 均匀分布 n=20
                        - generic [ref=e274]: 车辆路径 CVRP · 基准算例 · 20 个任务
                    - listitem [ref=e275]:
                      - button "欧氏 CVRP · 均匀分布 n=50 车辆路径 CVRP · 基准算例 · 50 个任务" [ref=e276] [cursor=pointer]:
                        - generic [ref=e277]: 欧氏 CVRP · 均匀分布 n=50
                        - generic [ref=e278]: 车辆路径 CVRP · 基准算例 · 50 个任务
                    - listitem [ref=e279]:
                      - button "欧氏 CVRP · 均匀分布 n=100 车辆路径 CVRP · 基准算例 · 100 个任务" [ref=e280] [cursor=pointer]:
                        - generic [ref=e281]: 欧氏 CVRP · 均匀分布 n=100
                        - generic [ref=e282]: 车辆路径 CVRP · 基准算例 · 100 个任务
                    - listitem [ref=e283]:
                      - button "欧氏 CVRP · 均匀分布 n=200 车辆路径 CVRP · 基准算例 · 200 个任务" [ref=e284] [cursor=pointer]:
                        - generic [ref=e285]: 欧氏 CVRP · 均匀分布 n=200
                        - generic [ref=e286]: 车辆路径 CVRP · 基准算例 · 200 个任务
                    - listitem [ref=e287]:
                      - button "欧氏 CVRP · 聚簇分布 n=20 车辆路径 CVRP · 基准算例 · 20 个任务" [ref=e288] [cursor=pointer]:
                        - generic [ref=e289]: 欧氏 CVRP · 聚簇分布 n=20
                        - generic [ref=e290]: 车辆路径 CVRP · 基准算例 · 20 个任务
                    - listitem [ref=e291]:
                      - button "欧氏 CVRP · 聚簇分布 n=50 车辆路径 CVRP · 基准算例 · 50 个任务" [ref=e292] [cursor=pointer]:
                        - generic [ref=e293]: 欧氏 CVRP · 聚簇分布 n=50
                        - generic [ref=e294]: 车辆路径 CVRP · 基准算例 · 50 个任务
                    - listitem [ref=e295]:
                      - button "欧氏 CVRP · 聚簇分布 n=100 车辆路径 CVRP · 基准算例 · 100 个任务" [ref=e296] [cursor=pointer]:
                        - generic [ref=e297]: 欧氏 CVRP · 聚簇分布 n=100
                        - generic [ref=e298]: 车辆路径 CVRP · 基准算例 · 100 个任务
                    - listitem [ref=e299]:
                      - button "欧氏 CVRP · 聚簇分布 n=200 车辆路径 CVRP · 基准算例 · 200 个任务" [ref=e300] [cursor=pointer]:
                        - generic [ref=e301]: 欧氏 CVRP · 聚簇分布 n=200
                        - generic [ref=e302]: 车辆路径 CVRP · 基准算例 · 200 个任务
        - generic [ref=e308]:
          - region "地图" [ref=e310]:
            - tablist [ref=e313]:
              - tab "地图" [selected] [ref=e314] [cursor=pointer]:
                - generic [ref=e315]:
                  - generic [ref=e316]: 地图
                  - button "Close 地图" [ref=e317]
            - tabpanel "地图" [ref=e321]
          - region "方案对比" [ref=e323]:
            - tablist [ref=e326]:
              - tab "方案对比" [active] [selected] [ref=e327] [cursor=pointer]:
                - generic [ref=e328]:
                  - generic [ref=e329]: 方案对比
                  - button "Close 方案对比" [ref=e330]
              - tab "验算" [ref=e333] [cursor=pointer]
              - tab "实验结果" [ref=e336] [cursor=pointer]
              - tab "仿真回放" [ref=e339] [cursor=pointer]
              - tab "科研图表" [ref=e342] [cursor=pointer]
              - tab "日志" [ref=e345] [cursor=pointer]
            - tabpanel "方案对比" [ref=e349]:
              - generic [ref=e351]:
                - generic [ref=e352]:
                  - paragraph [ref=e353]: 本批 3 次运行 · 0 个已验算可行解。最佳值仅在相同输入、目标、单位和时间预算内标记。
                  - generic "地图检查未计入的运行" [ref=e354]:
                    - generic [ref=e355]:
                      - generic [ref=e356]: PyVRP 迭代局部搜索 · run_2026：地图碰撞检查未通过，不计入已验算可行解（最小净空 0.000 m < 阈值 0.225 m）。
                      - list "碰撞线段" [ref=e357]:
                        - listitem [ref=e358]: 路线 0 第 0 段 · (-7.582, 3.360) · 净空 0.000 m
                    - generic [ref=e359]:
                      - generic [ref=e360]: OR-Tools 引导局部搜索 · run_2026：地图碰撞检查未通过，不计入已验算可行解（最小净空 0.000 m < 阈值 0.225 m）。
                      - list "碰撞线段" [ref=e361]:
                        - listitem [ref=e362]: 路线 2 第 4 段 · (-7.775, 3.885) · 净空 0.000 m
                    - generic [ref=e363]:
                      - generic [ref=e364]: Clarke–Wright 节约算法 · run_2026：地图碰撞检查未通过，不计入已验算可行解（最小净空 0.000 m < 阈值 0.225 m）。
                      - list "碰撞线段" [ref=e365]:
                        - listitem [ref=e366]: 路线 2 第 5 段 · (-7.775, 3.885) · 净空 0.000 m
                  - paragraph [ref=e367]: 未取整欧氏距离之和 · m · 输入 4eae9b29e513
                  - generic "历史运行" [ref=e368]:
                    - button "历史运行（本场景，含失败/已隔离/身份未核验）" [ref=e369] [cursor=pointer]
                - generic [ref=e374]:
                  - table [ref=e375]:
                    - rowgroup [ref=e376]:
                      - row [ref=e377]:
                        - columnheader "算法" [ref=e378]
                        - columnheader "状态" [ref=e379]
                        - columnheader "目标值" [ref=e380]
                        - columnheader "与 BKS 差距" [ref=e381]
                        - columnheader "路线数" [ref=e382]
                        - columnheader "计算" [ref=e383]
                        - columnheader "验算" [ref=e384]
                        - columnheader [ref=e385]
                    - rowgroup [ref=e386]:
                      - row [selected] [ref=e387] [cursor=pointer]:
                        - cell "PyVRP 迭代局部搜索 run_2026 · 预算 3 s · 种子 42 不参与排名 身份未核验" [ref=e388]:
                          - text: PyVRP 迭代局部搜索
                          - generic "冻结 run_id：run_20261022T153003_5ac092；预算 3 s · 种子 42" [ref=e389]: run_2026 · 预算 3 s · 种子 42
                          - generic [ref=e390]:
                            - generic [ref=e391]: 不参与排名
                            - generic [ref=e392]: 身份未核验
                        - cell "检查未通过" [ref=e393]
                        - cell "54.92 m" [ref=e394]
                        - cell "未记录" [ref=e395]
                        - cell "3" [ref=e396]
                        - cell "3.04 s" [ref=e397]
                        - cell "通过" [ref=e398]
                        - cell [ref=e402]:
                          - link "JSON" [ref=e403]:
                            - /url: /lab/api/runs/run_20261022T153003_5ac092/export?format=json
                          - link "CSV" [ref=e404]:
                            - /url: /lab/api/runs/run_20261022T153003_5ac092/export?format=csv
                          - link "GeoJSON" [ref=e405]:
                            - /url: /lab/api/runs/run_20261022T153003_5ac092/export?format=geojson
                      - row [ref=e406] [cursor=pointer]:
                        - cell "OR-Tools 引导局部搜索 run_2026 · 预算 3 s 不参与排名 身份未核验" [ref=e407]:
                          - text: OR-Tools 引导局部搜索
                          - generic "冻结 run_id：run_20261022T153003_8bf0fd；预算 3 s" [ref=e408]: run_2026 · 预算 3 s
                          - generic [ref=e409]:
                            - generic [ref=e410]: 不参与排名
                            - generic [ref=e411]: 身份未核验
                        - cell "检查未通过" [ref=e412]
                        - cell "54.92 m" [ref=e413]
                        - cell "未记录" [ref=e414]
                        - cell "3" [ref=e415]
                        - cell "3.05 s" [ref=e416]
                        - cell "通过" [ref=e417]
                        - cell [ref=e421]:
                          - link "JSON" [ref=e422]:
                            - /url: /lab/api/runs/run_20261022T153003_8bf0fd/export?format=json
                          - link "CSV" [ref=e423]:
                            - /url: /lab/api/runs/run_20261022T153003_8bf0fd/export?format=csv
                          - link "GeoJSON" [ref=e424]:
                            - /url: /lab/api/runs/run_20261022T153003_8bf0fd/export?format=geojson
                      - row [ref=e425] [cursor=pointer]:
                        - cell "Clarke–Wright 节约算法 run_2026 · 预算 3 s 不参与排名 身份未核验" [ref=e426]:
                          - text: Clarke–Wright 节约算法
                          - generic "冻结 run_id：run_20261022T153003_0ad196；预算 3 s" [ref=e427]: run_2026 · 预算 3 s
                          - generic [ref=e428]:
                            - generic [ref=e429]: 不参与排名
                            - generic [ref=e430]: 身份未核验
                        - cell "检查未通过" [ref=e431]
                        - cell "57.63 m" [ref=e432]
                        - cell "未记录" [ref=e433]
                        - cell "3" [ref=e434]
                        - cell "40 ms" [ref=e435]
                        - cell "通过" [ref=e436]
                        - cell [ref=e440]:
                          - link "JSON" [ref=e441]:
                            - /url: /lab/api/runs/run_20261022T153003_0ad196/export?format=json
                          - link "CSV" [ref=e442]:
                            - /url: /lab/api/runs/run_20261022T153003_0ad196/export?format=csv
                          - link "GeoJSON" [ref=e443]:
                            - /url: /lab/api/runs/run_20261022T153003_0ad196/export?format=geojson
                  - generic [ref=e444]:
                    - heading "选中方案追溯" [level=3] [ref=e445]
                    - generic "运行追溯" [ref=e446]:
                      - generic [ref=e447]: 运行
                      - generic [ref=e448]: run_20261022T153003_5ac092
                      - generic [ref=e449]: 输入场景
                      - link "cvrp-depot-floor" [ref=e451] [cursor=pointer]:
                        - /url: "#/plan/cvrp-depot-floor"
                      - generic [ref=e452]: 实例哈希
                      - generic "4eae9b29e513adf6ba231c7bbb2210c776384dedfa8218d511dbc1d37c2130e9" [ref=e453]:
                        - text: 4eae9b29e513
                        - button "复制实例哈希" [ref=e454] [cursor=pointer]
                      - generic [ref=e458]: 算法
                      - generic [ref=e459]: pyvrp.hgs · 版本 0.14.0
                      - generic [ref=e460]: 种子
                      - generic [ref=e461]: "42"
                      - generic [ref=e462]: 预算
                      - generic [ref=e463]: 3 s
                      - generic [ref=e464]: 参数
                      - generic [ref=e465]: 无其他参数
                      - generic [ref=e466]: 源码身份
                      - generic [ref=e467]: 身份未核验
                    - generic [ref=e468]:
                      - generic [ref=e469]: 本运行：地图碰撞检查未通过，不计入已验算可行解（最小净空 0.000 m < 阈值 0.225 m）。
                      - list "碰撞线段" [ref=e470]:
                        - listitem [ref=e471]: 路线 0 第 0 段 · (-7.582, 3.360) · 净空 0.000 m
                  - generic [ref=e472]:
                    - heading "未参与比较与排名（3）" [level=3] [ref=e473]
                    - list "未参与比较的运行" [ref=e474]:
                      - listitem [ref=e475]:
                        - text: PyVRP 迭代局部搜索 · run_2026 · 检查未通过 · 地图碰撞检查未通过（1 处）· 不计入已验算可行解
                        - generic [ref=e476]:
                          - generic [ref=e477]: 碰撞明细：地图碰撞检查未通过，不计入已验算可行解（最小净空 0.000 m < 阈值 0.225 m）。
                          - list "碰撞线段" [ref=e478]:
                            - listitem [ref=e479]: 路线 0 第 0 段 · (-7.582, 3.360) · 净空 0.000 m
                      - listitem [ref=e480]:
                        - text: OR-Tools 引导局部搜索 · run_2026 · 检查未通过 · 地图碰撞检查未通过（1 处）· 不计入已验算可行解
                        - generic [ref=e481]:
                          - generic [ref=e482]: 碰撞明细：地图碰撞检查未通过，不计入已验算可行解（最小净空 0.000 m < 阈值 0.225 m）。
                          - list "碰撞线段" [ref=e483]:
                            - listitem [ref=e484]: 路线 2 第 4 段 · (-7.775, 3.885) · 净空 0.000 m
                      - listitem [ref=e485]:
                        - text: Clarke–Wright 节约算法 · run_2026 · 检查未通过 · 地图碰撞检查未通过（1 处）· 不计入已验算可行解
                        - generic [ref=e486]:
                          - generic [ref=e487]: 碰撞明细：地图碰撞检查未通过，不计入已验算可行解（最小净空 0.000 m < 阈值 0.225 m）。
                          - list "碰撞线段" [ref=e488]:
                            - listitem [ref=e489]: 路线 2 第 5 段 · (-7.775, 3.885) · 净空 0.000 m
                - paragraph [ref=e491]: 内部搜索曲线使用量化、松弛或加权成本，与最终验算目标不同，可在原始记录中查看。
                - figure [ref=e492]:
                  - heading "收敛：跨种子中位数与四分位区间（当前比较组）" [level=4] [ref=e493]
                  - paragraph [ref=e494]: 数据未提供：没有可用轨迹：须为已验算可行解且 trace_contract 为 reported_objective、轨迹终值等于目标值（已隔离 0，未成功 3，无一致轨迹 0）
                - figure "样本：n = 3/3；未计入：已隔离 0，未完成 0，无独立验算值 0，无报告值 0，单位不同 0 最大相对偏差 0.00%；空心标记 = 验算未通过；检查器：urp_lab.solvers.routing · 按原始坐标与需求复算（未取整欧氏距离） 参照：对角线 y = x（完全一致）；数据为 objective.value 与 check.computed_cost 原值 单位：m；方向：越贴近对角线越一致" [ref=e495]:
                  - heading "独立验算一致性：求解器报告目标 vs 独立重算" [level=4] [ref=e496]
                  - img "验算一致性散点，3 次运行" [ref=e497]:
                    - generic [ref=e498]:
                      - generic [ref=e499]: "55"
                      - generic [ref=e501]: "56"
                      - generic [ref=e503]: "57"
                      - generic [ref=e505]: "55"
                      - generic [ref=e507]: "56"
                      - generic [ref=e509]: "57"
                      - generic [ref=e512]: 求解器报告目标 (m)
                      - generic [ref=e513]: 独立重算 (m)
                    - generic "PyVRP 迭代局部搜索 · run_20261022T153003_5ac092 · 报告 54.92395214306953 · 重算 54.92395214306953" [ref=e515]
                    - generic "OR-Tools 引导局部搜索 · run_20261022T153003_8bf0fd · 报告 54.92395214306953 · 重算 54.92395214306953" [ref=e517]
                    - generic "Clarke–Wright 节约算法 · run_20261022T153003_0ad196 · 报告 57.62535472512377 · 重算 57.62535472512377" [ref=e519]
                  - list "图例" [ref=e521]:
                    - listitem [ref=e522]:
                      - generic [ref=e525]: PyVRP 迭代局部搜索（验算通过）
                    - listitem [ref=e526]:
                      - generic [ref=e529]: OR-Tools 引导局部搜索（验算通过）
                    - listitem [ref=e530]:
                      - generic [ref=e533]: Clarke–Wright 节约算法（验算通过）
                  - generic [ref=e534]:
                    - generic [ref=e535]: 样本：n = 3/3；未计入：已隔离 0，未完成 0，无独立验算值 0，无报告值 0，单位不同 0
                    - generic [ref=e536]: 最大相对偏差 0.00%；空心标记 = 验算未通过；检查器：urp_lab.solvers.routing · 按原始坐标与需求复算（未取整欧氏距离）
                    - generic [ref=e537]: 参照：对角线 y = x（完全一致）；数据为 objective.value 与 check.computed_cost 原值
                    - generic [ref=e538]: 单位：m；方向：越贴近对角线越一致
                - figure "样本：n = 3 次运行；身份字段缺失（source_identity_verified 未记录）共 3 次，其中有解的单列为“有解 · 身份未核验” 只有“成功”类进入排名与比较；已隔离运行不提供任何数值 参照：状态取自运行记录 state/status/check 与源码身份核对；每类有独立纹理与文字标签" [ref=e539]:
                  - heading "运行状态流向" [level=4] [ref=e540]
                  - img "3 次运行的状态分布：有解 · 未通过验算或缺依据 3" [ref=e541]:
                    - generic [ref=e543]: 全部 3
                    - generic [ref=e544]: 有解 · 未通过验算或缺依据 · 3（100%）
                  - generic [ref=e548]:
                    - generic [ref=e549]: 样本：n = 3 次运行；身份字段缺失（source_identity_verified 未记录）共 3 次，其中有解的单列为“有解 · 身份未核验”
                    - generic [ref=e550]: 只有“成功”类进入排名与比较；已隔离运行不提供任何数值
                    - generic [ref=e551]: 参照：状态取自运行记录 state/status/check 与源码身份核对；每类有独立纹理与文字标签
        - region "推荐与求解" [ref=e553]:
          - tablist [ref=e556]:
            - tab "推荐与求解" [selected] [ref=e557] [cursor=pointer]:
              - generic [ref=e558]:
                - generic [ref=e559]: 推荐与求解
                - button "Close 推荐与求解" [ref=e560]
            - tab "检查器" [ref=e563] [cursor=pointer]
            - tab "决策记录" [ref=e566] [cursor=pointer]
          - tabpanel "推荐与求解" [ref=e570]:
            - generic [ref=e573]:
              - generic [ref=e574]:
                - heading "推荐算法" [level=3] [ref=e575]
                - button "重新分析" [ref=e576] [cursor=pointer]
              - paragraph [ref=e582]: 推荐 PyVRP 迭代局部搜索：CVRP 迭代局部搜索对照；相对最优已知解的差距由本次求解实测，不预设性能数字
              - generic [ref=e583]:
                - generic [ref=e584]:
                  - generic [ref=e585]: 客户数
                  - strong [ref=e586]: "10"
                - generic [ref=e587]:
                  - generic [ref=e588]: 容量
                  - strong [ref=e589]: "8"
                - generic [ref=e590]:
                  - generic [ref=e591]: 最少车辆
                  - strong [ref=e592]: "3"
              - list [ref=e593]:
                - listitem [ref=e594]:
                  - generic [ref=e595] [cursor=pointer]:
                    - checkbox "1 PyVRP 迭代局部搜索 PyVRP 推荐" [checked] [ref=e596]
                    - generic [ref=e597]: "1"
                    - generic [ref=e598]: PyVRP 迭代局部搜索
                    - generic [ref=e599]: PyVRP
                    - generic [ref=e600]: 推荐
                  - paragraph [ref=e601]: CVRP 迭代局部搜索对照；相对最优已知解的差距由本次求解实测，不预设性能数字
                - listitem [ref=e602]:
                  - generic [ref=e603] [cursor=pointer]:
                    - checkbox "2 OR-Tools 引导局部搜索 OR-Tools" [checked] [ref=e604]
                    - generic [ref=e605]: "2"
                    - generic [ref=e606]: OR-Tools 引导局部搜索
                    - generic [ref=e607]: OR-Tools
                  - paragraph [ref=e608]: 稳健的对照求解器
                - listitem [ref=e609]:
                  - generic [ref=e610] [cursor=pointer]:
                    - checkbox "3 Clarke–Wright 节约算法 本项目" [checked] [ref=e611]
                    - generic [ref=e612]: "3"
                    - generic [ref=e613]: Clarke–Wright 节约算法
                    - generic [ref=e614]: 本项目
                  - paragraph [ref=e615]: 节约算法构造基线（≤ 100 客户），耗时以实测为准
                - listitem [ref=e616]:
                  - generic [ref=e617] [cursor=pointer]:
                    - checkbox "4 最近邻构造 本项目" [ref=e618]
                    - generic [ref=e619]: "4"
                    - generic [ref=e620]: 最近邻构造
                    - generic [ref=e621]: 本项目
                  - paragraph [ref=e622]: 最近邻构造基线，成本经独立验算
              - generic [ref=e623]:
                - generic "允许范围 0.05–600 s" [ref=e624]:
                  - generic [ref=e625]: 时间预算
                  - generic [ref=e626]:
                    - spinbutton "时间预算 秒/算法" [ref=e627]: "3"
                    - emphasis [ref=e628]: 秒/算法
                - generic "允许范围 0–2147483647" [ref=e629]:
                  - generic [ref=e630]: 随机种子
                  - generic [ref=e631]:
                    - spinbutton "随机种子 提交时冻结" [ref=e632]: "42"
                    - emphasis [ref=e633]: 提交时冻结
                - button "对比 3 个算法" [ref=e634] [cursor=pointer]
      - status [ref=e637]: 日志 opened
      - alert [ref=e638]
    - generic [ref=e641]:
      - generic [ref=e642]:
        - generic [ref=e643]: 官方 depot 地图左侧开阔地面 10 个任务点，仓库 = 机器人起点；直线段经地图间隙检查（可能穿过柱子，会如实报告）。
        - button "经典视图" [ref=e644] [cursor=pointer]
      - generic [ref=e645]:
        - application "场景地图。拖动平移，滚轮或双指缩放，加减号缩放，0 适应内容。" [ref=e646]:
          - img [aria-hidden] [ref=e647]:
            - generic [ref=e672]:
              - generic [ref=e673]: D
              - generic [ref=e674]: P1
              - generic [ref=e675]: P2
              - generic [ref=e676]: P3
              - generic [ref=e677]: P4
              - generic [ref=e678]: P5
              - generic [ref=e679]: P6
              - generic [ref=e680]: P7
              - generic [ref=e681]: P8
              - generic [ref=e682]: P9
              - generic [ref=e683]: P10
              - generic [ref=e712]:
                - generic [ref=e713]: "1"
                - generic [ref=e716]: "2"
                - generic [ref=e719]: "3"
                - generic [ref=e722]: "4"
              - generic [ref=e765]:
                - generic [ref=e766]: "1"
                - generic [ref=e769]: "2"
                - generic [ref=e772]: "3"
                - generic [ref=e775]: "4"
                - generic [ref=e778]: "5"
              - generic [ref=e797]: "1"
              - generic [ref=e972]: D
              - generic [ref=e975]: P1 · 2
              - generic [ref=e978]: P2 · 1
              - generic [ref=e981]: P3 · 2
              - generic [ref=e984]: P4 · 3
              - generic [ref=e987]: P5 · 1
              - generic [ref=e990]: P6 · 2
              - generic [ref=e993]: P7 · 3
              - generic [ref=e996]: P8 · 2
              - generic [ref=e999]: P9 · 1
              - generic [ref=e1002]: P10 · 1
          - generic:
            - generic [ref=e1014]: PyVRP 迭代局部搜索 · 54.92 m
            - generic "map 坐标系，单位米": 2 m
          - generic [ref=e1017]:
            - button "放大" [ref=e1018] [cursor=pointer]
            - button "缩小" [ref=e1020] [cursor=pointer]
            - button "适应内容" [ref=e1022] [cursor=pointer]
        - generic [ref=e1028]:
          - button "同一输入 · 3 个方案" [expanded] [ref=e1029]
          - generic [ref=e1033]:
            - button "PyVRP 迭代局部搜索" [pressed] [ref=e1035] [cursor=pointer]
            - generic [ref=e1036]: 54.92 m
            - button "显示 PyVRP 迭代局部搜索 路线" [pressed] [ref=e1037] [cursor=pointer]
          - generic [ref=e1040]:
            - button "OR-Tools 引导局部搜索" [ref=e1042] [cursor=pointer]
            - generic [ref=e1043]: 54.92 m
            - button "显示 OR-Tools 引导局部搜索 路线" [pressed] [ref=e1044] [cursor=pointer]
          - generic [ref=e1047]:
            - button "Clarke–Wright 节约算法" [ref=e1049] [cursor=pointer]
            - generic [ref=e1050]: 57.63 m
            - button "显示 Clarke–Wright 节约算法 路线" [pressed] [ref=e1051] [cursor=pointer]
  - contentinfo [ref=e1054]:
    - generic [ref=e1055]: 已连接
    - generic [ref=e1057]: 求解空闲
    - generic [ref=e1058]: 田间：未运行 · TB4：未运行
    - generic [ref=e1062]: 车间空地 · 欧氏 CVRP
    - link "CVRP 数值任务" [ref=e1063] [cursor=pointer]:
      - /url: "#/jobs"
    - link "BPP 历史" [ref=e1064] [cursor=pointer]:
      - /url: "#/bpp"
```

# Test source

```ts
  1  | import { test, expect, shot, listScenarios, API } from './helpers';
  2  | import type { Page } from '@playwright/test';
  3  | // Mamba: "0 个已验算可行解" can be correct (e.g. cvrp-depot-floor runs fail map_check.collision_free). Assert the summary
  4  | // count is consistent with the table (check column 通过, PlanPanels.tsx:855,914) once no row is 排队中/计算中.
  5  | test('G 真实小规模求解并打开比较', async ({ page }, info) => {
  6  |   const all = await listScenarios(page);
  7  |   const sc = all.find((s) => s.id === 'bench-cvrp-uniform-n20') ?? all.find((s) => (s as any).problem_class === 'euclidean_cvrp');
  8  |   test.skip(!sc, 'no scenarios');
  9  |   await page.goto(`/#/plan/${encodeURIComponent(sc!.id)}`);
  10 |   const solve = page.getByRole('button', { name: /^对比 \d+ 个算法$/ });
  11 |   const summary = page.getByText(/本批 \d+ 次运行 · \d+ 个已验算可行解/);
  12 |   await test.step('求解', async () => {
  13 |     await expect(solve).toBeEnabled({ timeout: 30_000 });
  14 |     await shot(page, info, 'before-solve');
  15 |     await solve.click();
  16 |     await expect(summary).toBeVisible({ timeout: 150_000 });
  17 |     // wait until the batch settles: status bar 求解空闲 (Studio.tsx:432) and no 排队中/计算中 cell (run8 v1 counted too early)
  18 |     // (v2 rerun showed 求解空闲 matched before the batch registered → wait for the batch to appear first, then settle)
  19 |     const pending = page.locator('td').filter({ hasText: /排队中|计算中/ });
  20 |     await expect(page.getByText(/^求解 \d+$/).or(pending.first())).toBeVisible({ timeout: 30_000 }).catch(() => {});
  21 |     await expect(pending).toHaveCount(0, { timeout: 150_000 });
  22 |     await expect(page.getByText('求解空闲', { exact: true })).toBeVisible({ timeout: 30_000 });
  23 |     await expect(summary).toBeVisible();
  24 |     const m = (await summary.innerText()).match(/本批 (\d+) 次运行 · (\d+) 个已验算可行解/)!;
  25 |     const passed = await page.locator('tbody tr').filter({ has: page.locator('td', { hasText: /^\s*通过\s*$/ }) }).filter({ hasNot: page.locator('td', { hasText: /检查未通过|待检查/ }) }).count() /* 检查 column (PlanPanels.tsx:914) only reflects r.check; map_check failure shows in 状态 as 检查未通过 (comparison.ts:91) */;
  26 |     info.annotations.push({ type: 'solve-summary', description: `${m[0]}; table rows with 通过=${passed}; scenario=${sc!.id}` });
  27 |     await shot(page, info, 'solved');
  28 |     expect(Number(m[2]), 'map_check-clean scenario yields verified-feasible solutions').toBeGreaterThan(0);
  29 |     expect(Number(m[2]), 'summary verified count == rows with check 通过').toBe(passed);
  30 |   });
  31 | });
  32 | 
  33 | async function solveAndSettle(page: Page) {
  34 |   const solve = page.getByRole('button', { name: /^对比 \d+ 个算法$/ });
  35 |   const summary = page.getByText(/本批 \d+ 次运行 · \d+ 个已验算可行解/);
  36 |   await expect(solve).toBeEnabled({ timeout: 30_000 });
  37 |   await solve.click();
  38 |   await expect(summary).toBeVisible({ timeout: 150_000 });
  39 |   const pending = page.locator('td').filter({ hasText: /排队中|计算中/ });
  40 |   await expect(page.getByText(/^求解 \d+$/).or(pending.first())).toBeVisible({ timeout: 30_000 }).catch(() => {});
  41 |   await expect(pending).toHaveCount(0, { timeout: 150_000 });
  42 |   await expect(page.getByText('求解空闲', { exact: true })).toBeVisible({ timeout: 30_000 });
  43 |   const m = (await summary.innerText()).match(/本批 (\d+) 次运行 · (\d+) 个已验算可行解/)!;
  44 |   return { runs: Number(m[1]), verified: Number(m[2]), passed: await page.locator('tbody tr').filter({ has: page.locator('td', { hasText: /^\s*通过\s*$/ }) }).filter({ hasNot: page.locator('td', { hasText: /检查未通过|待检查/ }) }).count() /* 检查 column (PlanPanels.tsx:914) only reflects r.check; map_check failure shows in 状态 as 检查未通过 (comparison.ts:91) */ };
  45 | }
  46 | // Mamba: on cvrp-depot-floor every run fails map_check.collision_free (straight segments cross map pillars) → 0 verified is
  47 | // correct. Collision report (Mamba 04f4e381, MapExclusionNote.tsx) is enforced from a74d5479 on.
  48 | test('G2 cvrp-depot-floor：0 个已验算可行解为预期，并显示碰撞报告', async ({ page }, info) => {
  49 |   await page.goto('/#/plan/cvrp-depot-floor');
  50 |   const t0 = new Date().toISOString();
  51 |   const r = await solveAndSettle(page);
  52 |   await shot(page, info, 'solved-floor');
  53 |   info.annotations.push({ type: 'solve-summary', description: `本批 ${r.runs} 次运行 · ${r.verified} 个已验算可行解; 通过=${r.passed}` });
  54 |   expect(r.verified, '0 verified-feasible expected on cvrp-depot-floor').toBe(0);
  55 |   expect(r.passed).toBe(0);
  56 |   const runs = ((await (await page.request.get(`${API}/runs?limit=200`)).json()).runs as any[])
  57 |     .filter((x) => x.scenario_id === 'cvrp-depot-floor' && (x.created_utc ?? '') >= t0);
  58 |   info.annotations.push({ type: 'map_check', description: JSON.stringify(runs.map((x) => ({ id: x.run_id, state: x.state, check: x.check?.valid, map_check: x.map_check }))).slice(0, 2000) });
  59 |   expect(runs.length, 'API has the new runs').toBeGreaterThan(0);
  60 |   for (const x of runs) expect(x.map_check?.collision_free, `${x.run_id} map_check.collision_free`).toBe(false);
  61 |   await test.step('验算：地图净空未通过', async () => {
  62 |     await page.getByRole('tab', { name: '验算' }).click();
  63 |     await expect(page.locator('li[data-bad]', { hasText: '地图净空' }).first()).toBeVisible({ timeout: 10_000 }); // PlanPanels.tsx:1062
  64 |     await shot(page, info, 'verify-tab');
  65 |   });
  66 |   await test.step('碰撞报告（Mamba 04f4e381 selectors；未构建时 pending）', async () => {
  67 |     await page.getByRole('tab', { name: '方案对比' }).click();
  68 |     const summaryBox = page.locator('[data-exclusion-summary="map_check"]');
  69 |     await expect(summaryBox, 'Mamba 04f4e381 map_check summary (PlanPanels.tsx:860)').toBeVisible({ timeout: 10_000 });
  70 |     const excl = page.locator('[data-exclusion="map_collision"]');
> 71 |     await expect(excl).toHaveCount(r.runs);
     |                        ^ Error: expect(locator).toHaveCount(expected) failed
  72 |     for (let i = 0; i < r.runs; i++) {
  73 |       await expect(excl.nth(i)).toHaveAttribute('data-run-id', /.+/);
  74 |       await expect(excl.nth(i)).toHaveAttribute('data-violation-count', /^[1-9]\d*$/);
  75 |     }
  76 |     const v = summaryBox.locator('li[data-map-violation="true"]');
  77 |     await expect(v.first()).toBeVisible();
  78 |     await expect(v.first()).toHaveAttribute('data-route', /.+/);
  79 |     await expect(v.first()).toHaveAttribute('data-segment', /.+/);
  80 |     await expect(page.getByText(/本批 \d+ 次运行 · 0 个已验算可行解/)).toBeVisible();
  81 |     info.annotations.push({ type: 'collision-note', description: (await summaryBox.innerText()).slice(0, 1500) });
  82 |     info.annotations.push({ type: 'violations', description: JSON.stringify(await v.evaluateAll((els) => els.map((e) => ({ route: e.getAttribute('data-route'), segment: e.getAttribute('data-segment'), text: e.textContent })))).slice(0, 1500) });
  83 |     await shot(page, info, 'collision-report');
  84 |   });
  85 | });
  86 | 
```