# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e-fork-timeout.spec.ts >> E Fork 超时重试：只生成一份“我的场景”
- Location: tests/e-fork-timeout.spec.ts:4:1

# Error details

```
Error: Channel closed
```

```
Error: page.waitForTimeout: Test ended.
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
                  - generic [ref=e111]: 我的任务地图 · 18
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
                    - listitem [ref=e161]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e162] [cursor=pointer]:
                        - generic [ref=e163]: 果园采收集运
                        - generic [ref=e164]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e165]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e166] [cursor=pointer]:
                        - generic [ref=e167]: 果园采收集运
                        - generic [ref=e168]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e169]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e170] [cursor=pointer]:
                        - generic [ref=e171]: 果园采收集运
                        - generic [ref=e172]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e173]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e174] [cursor=pointer]:
                        - generic [ref=e175]: 果园采收集运
                        - generic [ref=e176]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e177]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e178] [cursor=pointer]:
                        - generic [ref=e179]: 果园采收集运
                        - generic [ref=e180]: 多车任务 · 实地坐标 · 米 · 36 个任务
                    - listitem [ref=e181]:
                      - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务" [ref=e182] [cursor=pointer]:
                        - generic [ref=e183]: 果园采收集运
                        - generic [ref=e184]: 多车任务 · 实地坐标 · 米 · 36 个任务
                - generic [ref=e185]:
                  - generic [ref=e186]: 我的其他场景 · 3
                  - list [ref=e187]:
                    - listitem [ref=e188]:
                      - button "车间空地 · 欧氏 CVRP（我的） 车辆路径 CVRP · 仿真地图 · depot · 10 个任务" [ref=e189] [cursor=pointer]:
                        - generic [ref=e190]: 车间空地 · 欧氏 CVRP（我的）
                        - generic [ref=e191]: 车辆路径 CVRP · 仿真地图 · depot · 10 个任务
                    - listitem [ref=e192]:
                      - button "车间空地 · 欧氏 CVRP（我的） 车辆路径 CVRP · 仿真地图 · depot · 10 个任务" [ref=e193] [cursor=pointer]:
                        - generic [ref=e194]: 车间空地 · 欧氏 CVRP（我的）
                        - generic [ref=e195]: 车辆路径 CVRP · 仿真地图 · depot · 10 个任务
                    - listitem [ref=e196]:
                      - button "车间空地 · 欧氏 CVRP（我的） 车辆路径 CVRP · 仿真地图 · depot · 10 个任务" [ref=e197] [cursor=pointer]:
                        - generic [ref=e198]: 车间空地 · 欧氏 CVRP（我的）
                        - generic [ref=e199]: 车辆路径 CVRP · 仿真地图 · depot · 10 个任务
                - generic [ref=e200]:
                  - generic [ref=e201]: 仿真地图 · 8
                  - list [ref=e202]:
                    - listitem [ref=e203]:
                      - button "官方迷宫 · 双点巡检闭环 转弯约束路网 · 仿真地图 · maze · 2 个任务" [ref=e204] [cursor=pointer]:
                        - generic [ref=e205]: 官方迷宫 · 双点巡检闭环
                        - generic [ref=e206]: 转弯约束路网 · 仿真地图 · maze · 2 个任务
                    - listitem [ref=e207]:
                      - button "仓储货架通道 · 作物行代理 转弯约束路网 · 仿真地图 · warehouse · 5 个任务" [ref=e208] [cursor=pointer]:
                        - generic [ref=e209]: 仓储货架通道 · 作物行代理
                        - generic [ref=e210]: 转弯约束路网 · 仿真地图 · warehouse · 5 个任务
                    - listitem [ref=e211]:
                      - button "车间空地 · 欧氏 CVRP 车辆路径 CVRP · 仿真地图 · depot · 10 个任务" [ref=e212] [cursor=pointer]:
                        - generic [ref=e213]: 车间空地 · 欧氏 CVRP
                        - generic [ref=e214]: 车辆路径 CVRP · 仿真地图 · depot · 10 个任务
                    - listitem [ref=e215]:
                      - button "车间空地 · 内缩作业区覆盖 覆盖作业 · 仿真地图 · depot" [ref=e216] [cursor=pointer]:
                        - generic [ref=e217]: 车间空地 · 内缩作业区覆盖
                        - generic [ref=e218]: 覆盖作业 · 仿真地图 · depot
                    - listitem [ref=e219]:
                      - button "仓库 · 跨通道到达 点到点规划 · 仿真地图 · warehouse" [ref=e220] [cursor=pointer]:
                        - generic [ref=e221]: 仓库 · 跨通道到达
                        - generic [ref=e222]: 点到点规划 · 仿真地图 · warehouse
                    - listitem [ref=e223]:
                      - button "仓库 · 农机转弯半径 点到点规划 · 仿真地图 · warehouse" [ref=e224] [cursor=pointer]:
                        - generic [ref=e225]: 仓库 · 农机转弯半径
                        - generic [ref=e226]: 点到点规划 · 仿真地图 · warehouse
                    - listitem [ref=e227]:
                      - button "迷宫 · 对角穿越 点到点规划 · 仿真地图 · maze" [ref=e228] [cursor=pointer]:
                        - generic [ref=e229]: 迷宫 · 对角穿越
                        - generic [ref=e230]: 点到点规划 · 仿真地图 · maze
                    - listitem [ref=e231]:
                      - button "车间 · 可倒车泊位 点到点规划 · 仿真地图 · depot" [ref=e232] [cursor=pointer]:
                        - generic [ref=e233]: 车间 · 可倒车泊位
                        - generic [ref=e234]: 点到点规划 · 仿真地图 · depot
                - generic [ref=e235]:
                  - generic [ref=e236]: 基准算例 · 26
                  - list [ref=e237]:
                    - listitem [ref=e238]:
                      - button "转弯路网 g3x3_s8000_uturn 转弯约束路网 · 基准算例 · 5 个任务" [ref=e239] [cursor=pointer]:
                        - generic [ref=e240]: 转弯路网 g3x3_s8000_uturn
                        - generic [ref=e241]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e242]:
                      - button "转弯路网 g3x3_s8001_left_cost 转弯约束路网 · 基准算例 · 5 个任务" [ref=e243] [cursor=pointer]:
                        - generic [ref=e244]: 转弯路网 g3x3_s8001_left_cost
                        - generic [ref=e245]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e246]:
                      - button "转弯路网 g3x3_s8002_left_ban 转弯约束路网 · 基准算例 · 5 个任务" [ref=e247] [cursor=pointer]:
                        - generic [ref=e248]: 转弯路网 g3x3_s8002_left_ban
                        - generic [ref=e249]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e250]:
                      - button "转弯路网 g3x3_s8003_uturn 转弯约束路网 · 基准算例 · 5 个任务" [ref=e251] [cursor=pointer]:
                        - generic [ref=e252]: 转弯路网 g3x3_s8003_uturn
                        - generic [ref=e253]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e254]:
                      - button "转弯路网 g3x3_s8004_left_cost 转弯约束路网 · 基准算例 · 5 个任务" [ref=e255] [cursor=pointer]:
                        - generic [ref=e256]: 转弯路网 g3x3_s8004_left_cost
                        - generic [ref=e257]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e258]:
                      - button "转弯路网 g3x3_s8005_left_ban 转弯约束路网 · 基准算例 · 5 个任务" [ref=e259] [cursor=pointer]:
                        - generic [ref=e260]: 转弯路网 g3x3_s8005_left_ban
                        - generic [ref=e261]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e262]:
                      - button "转弯路网 g3x3_s10000_uturn 转弯约束路网 · 基准算例 · 5 个任务" [ref=e263] [cursor=pointer]:
                        - generic [ref=e264]: 转弯路网 g3x3_s10000_uturn
                        - generic [ref=e265]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e266]:
                      - button "转弯路网 g3x3_s10000_left_cost 转弯约束路网 · 基准算例 · 5 个任务" [ref=e267] [cursor=pointer]:
                        - generic [ref=e268]: 转弯路网 g3x3_s10000_left_cost
                        - generic [ref=e269]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e270]:
                      - button "转弯路网 g3x3_s10000_left_ban 转弯约束路网 · 基准算例 · 5 个任务" [ref=e271] [cursor=pointer]:
                        - generic [ref=e272]: 转弯路网 g3x3_s10000_left_ban
                        - generic [ref=e273]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e274]:
                      - button "转弯路网 g3x4_s10000_uturn 转弯约束路网 · 基准算例 · 6 个任务" [ref=e275] [cursor=pointer]:
                        - generic [ref=e276]: 转弯路网 g3x4_s10000_uturn
                        - generic [ref=e277]: 转弯约束路网 · 基准算例 · 6 个任务
                    - listitem [ref=e278]:
                      - button "转弯路网 g3x4_s10000_left_cost 转弯约束路网 · 基准算例 · 6 个任务" [ref=e279] [cursor=pointer]:
                        - generic [ref=e280]: 转弯路网 g3x4_s10000_left_cost
                        - generic [ref=e281]: 转弯约束路网 · 基准算例 · 6 个任务
                    - listitem [ref=e282]:
                      - button "转弯路网 g3x4_s10000_left_ban 转弯约束路网 · 基准算例 · 6 个任务" [ref=e283] [cursor=pointer]:
                        - generic [ref=e284]: 转弯路网 g3x4_s10000_left_ban
                        - generic [ref=e285]: 转弯约束路网 · 基准算例 · 6 个任务
                    - listitem [ref=e286]:
                      - button "转弯路网 g4x4_s10000_uturn 转弯约束路网 · 基准算例 · 7 个任务" [ref=e287] [cursor=pointer]:
                        - generic [ref=e288]: 转弯路网 g4x4_s10000_uturn
                        - generic [ref=e289]: 转弯约束路网 · 基准算例 · 7 个任务
                    - listitem [ref=e290]:
                      - button "转弯路网 g4x4_s10000_left_cost 转弯约束路网 · 基准算例 · 7 个任务" [ref=e291] [cursor=pointer]:
                        - generic [ref=e292]: 转弯路网 g4x4_s10000_left_cost
                        - generic [ref=e293]: 转弯约束路网 · 基准算例 · 7 个任务
                    - listitem [ref=e294]:
                      - button "转弯路网 g4x4_s10000_left_ban 转弯约束路网 · 基准算例 · 7 个任务" [ref=e295] [cursor=pointer]:
                        - generic [ref=e296]: 转弯路网 g4x4_s10000_left_ban
                        - generic [ref=e297]: 转弯约束路网 · 基准算例 · 7 个任务
                    - listitem [ref=e298]:
                      - button "夹具 dead_end_infeasible 转弯约束路网 · 基准算例 · 1 个任务" [ref=e299] [cursor=pointer]:
                        - generic [ref=e300]: 夹具 dead_end_infeasible
                        - generic [ref=e301]: 转弯约束路网 · 基准算例 · 1 个任务
                    - listitem [ref=e302]:
                      - button "夹具 single_customer_cycle 转弯约束路网 · 基准算例 · 1 个任务" [ref=e303] [cursor=pointer]:
                        - generic [ref=e304]: 夹具 single_customer_cycle
                        - generic [ref=e305]: 转弯约束路网 · 基准算例 · 1 个任务
                    - listitem [ref=e306]:
                      - button "夹具 g3x3_s7000_none 转弯约束路网 · 基准算例 · 4 个任务" [ref=e307] [cursor=pointer]:
                        - generic [ref=e308]: 夹具 g3x3_s7000_none
                        - generic [ref=e309]: 转弯约束路网 · 基准算例 · 4 个任务
                    - listitem [ref=e310]:
                      - button "欧氏 CVRP · 均匀分布 n=20 车辆路径 CVRP · 基准算例 · 20 个任务" [ref=e311] [cursor=pointer]:
                        - generic [ref=e312]: 欧氏 CVRP · 均匀分布 n=20
                        - generic [ref=e313]: 车辆路径 CVRP · 基准算例 · 20 个任务
                    - listitem [ref=e314]:
                      - button "欧氏 CVRP · 均匀分布 n=50 车辆路径 CVRP · 基准算例 · 50 个任务" [ref=e315] [cursor=pointer]:
                        - generic [ref=e316]: 欧氏 CVRP · 均匀分布 n=50
                        - generic [ref=e317]: 车辆路径 CVRP · 基准算例 · 50 个任务
                    - listitem [ref=e318]:
                      - button "欧氏 CVRP · 均匀分布 n=100 车辆路径 CVRP · 基准算例 · 100 个任务" [ref=e319] [cursor=pointer]:
                        - generic [ref=e320]: 欧氏 CVRP · 均匀分布 n=100
                        - generic [ref=e321]: 车辆路径 CVRP · 基准算例 · 100 个任务
                    - listitem [ref=e322]:
                      - button "欧氏 CVRP · 均匀分布 n=200 车辆路径 CVRP · 基准算例 · 200 个任务" [ref=e323] [cursor=pointer]:
                        - generic [ref=e324]: 欧氏 CVRP · 均匀分布 n=200
                        - generic [ref=e325]: 车辆路径 CVRP · 基准算例 · 200 个任务
                    - listitem [ref=e326]:
                      - button "欧氏 CVRP · 聚簇分布 n=20 车辆路径 CVRP · 基准算例 · 20 个任务" [ref=e327] [cursor=pointer]:
                        - generic [ref=e328]: 欧氏 CVRP · 聚簇分布 n=20
                        - generic [ref=e329]: 车辆路径 CVRP · 基准算例 · 20 个任务
                    - listitem [ref=e330]:
                      - button "欧氏 CVRP · 聚簇分布 n=50 车辆路径 CVRP · 基准算例 · 50 个任务" [ref=e331] [cursor=pointer]:
                        - generic [ref=e332]: 欧氏 CVRP · 聚簇分布 n=50
                        - generic [ref=e333]: 车辆路径 CVRP · 基准算例 · 50 个任务
                    - listitem [ref=e334]:
                      - button "欧氏 CVRP · 聚簇分布 n=100 车辆路径 CVRP · 基准算例 · 100 个任务" [ref=e335] [cursor=pointer]:
                        - generic [ref=e336]: 欧氏 CVRP · 聚簇分布 n=100
                        - generic [ref=e337]: 车辆路径 CVRP · 基准算例 · 100 个任务
                    - listitem [ref=e338]:
                      - button "欧氏 CVRP · 聚簇分布 n=200 车辆路径 CVRP · 基准算例 · 200 个任务" [ref=e339] [cursor=pointer]:
                        - generic [ref=e340]: 欧氏 CVRP · 聚簇分布 n=200
                        - generic [ref=e341]: 车辆路径 CVRP · 基准算例 · 200 个任务
        - generic [ref=e347]:
          - region "地图" [ref=e349]:
            - tablist [ref=e352]:
              - tab "地图" [selected] [ref=e353] [cursor=pointer]:
                - generic [ref=e354]:
                  - generic [ref=e355]: 地图
                  - button "Close 地图" [ref=e356]
            - tabpanel "地图" [ref=e360]
          - region "方案对比" [ref=e362]:
            - tablist [ref=e365]:
              - tab "方案对比" [selected] [ref=e366] [cursor=pointer]:
                - generic [ref=e367]:
                  - generic [ref=e368]: 方案对比
                  - button "Close 方案对比" [ref=e369]
              - tab "验算" [ref=e372] [cursor=pointer]
              - tab "实验结果" [ref=e375] [cursor=pointer]
              - tab "仿真回放" [ref=e378] [cursor=pointer]
              - tab "科研图表" [ref=e381] [cursor=pointer]
              - tab "日志" [ref=e384] [cursor=pointer]
            - tabpanel "方案对比" [ref=e388]:
              - generic [ref=e389]:
                - generic [ref=e390]:
                  - paragraph [ref=e400]: 还没有方案
                  - paragraph [ref=e401]: 在“推荐与求解”里勾选算法后点击对比，结果会出现在这里。
                - generic "历史运行" [ref=e402]:
                  - button "历史运行（本场景，含失败/已隔离/身份未核验）" [ref=e403] [cursor=pointer]
        - region "检查器" [ref=e409]:
          - tablist [ref=e412]:
            - tab "推荐与求解" [ref=e413] [cursor=pointer]
            - tab "检查器" [selected] [ref=e416] [cursor=pointer]:
              - generic [ref=e417]:
                - generic [ref=e418]: 检查器
                - button "Close 检查器" [ref=e419]
            - tab "决策记录" [ref=e422] [cursor=pointer]
          - tabpanel "检查器" [ref=e426]:
            - generic [ref=e428]:
              - generic [ref=e429]:
                - heading "规划问题与约束" [level=3] [ref=e430]
                - paragraph [ref=e431]: 坐标：map · m · X 向右 / Y 向上。角度输入为度，提交保存为弧度。
                - generic [ref=e432]:
                  - text: 车辆容量
                  - spinbutton "车辆容量" [ref=e433]: "9"
                - group [ref=e434]:
                  - generic "任务清单 · 10 项" [ref=e435]
                - generic [ref=e436]:
                  - generic [ref=e437]:
                    - text: 新任务 X
                    - spinbutton "新任务 X" [ref=e438]: "0"
                  - generic [ref=e439]:
                    - text: 新任务 Y
                    - spinbutton "新任务 Y" [ref=e440]: "0"
                  - button "添加任务点" [ref=e441] [cursor=pointer]
                - group [ref=e442]:
                  - generic "完整任务输入 · JSON" [ref=e443]
              - generic [ref=e444]:
                - heading "车间空地 · 欧氏 CVRP（我的）" [level=3] [ref=e445]
                - paragraph [ref=e446]: 官方 depot 地图左侧开阔地面 10 个任务点，仓库 = 机器人起点；直线段经地图间隙检查（可能穿过柱子，会如实报告）。
                - paragraph [ref=e447]: 任务点由固定种子在空闲区域内抽样（只按点位间隙筛选，不按求解结果筛选）；路线为直线段，碰撞由 map_check 报告。
                - link "场景 JSON" [ref=e449] [cursor=pointer]:
                  - /url: /lab/api/scenarios/cvrp-depot-floor-my-a170fb131de0/export?format=json
      - status [ref=e453]: 日志 opened
      - alert [ref=e454]
    - generic [ref=e457]:
      - generic [ref=e458]:
        - generic [ref=e459]: 官方 depot 地图左侧开阔地面 10 个任务点，仓库 = 机器人起点；直线段经地图间隙检查（可能穿过柱子，会如实报告）。
        - generic [ref=e460]: 已保存
        - button "经典视图" [ref=e461] [cursor=pointer]
      - application "场景地图。拖动平移，滚轮或双指缩放，加减号缩放，0 适应内容。" [ref=e463]:
        - img [aria-hidden] [ref=e464]:
          - generic [ref=e470]:
            - generic [ref=e471]: D
            - generic [ref=e472]: P1
            - generic [ref=e473]: P2
            - generic [ref=e474]: P3
            - generic [ref=e475]: P4
            - generic [ref=e476]: P5
            - generic [ref=e477]: P6
            - generic [ref=e478]: P7
            - generic [ref=e479]: P8
            - generic [ref=e480]: P9
            - generic [ref=e481]: P10
            - generic [ref=e482]: D
            - generic [ref=e485]: P1 · 2
            - generic [ref=e488]: P2 · 1
            - generic [ref=e491]: P3 · 2
            - generic [ref=e494]: P4 · 3
            - generic [ref=e497]: P5 · 1
            - generic [ref=e500]: P6 · 2
            - generic [ref=e503]: P7 · 3
            - generic [ref=e506]: P8 · 2
            - generic [ref=e509]: P9 · 1
            - generic [ref=e512]: P10 · 1
        - generic:
          - generic "map 坐标系，单位米": 2 m
        - generic [ref=e516]:
          - button "放大" [ref=e517] [cursor=pointer]
          - button "缩小" [ref=e519] [cursor=pointer]
          - button "适应内容" [ref=e521] [cursor=pointer]
  - contentinfo [ref=e527]:
    - generic [ref=e528]: 已连接
    - generic [ref=e530]: 求解空闲
    - generic [ref=e531]: 田间：未运行 · TB4：未运行
    - generic [ref=e535]: 车间空地 · 欧氏 CVRP（我的）
    - link "CVRP 数值任务" [ref=e536] [cursor=pointer]:
      - /url: "#/jobs"
    - link "BPP 历史" [ref=e537] [cursor=pointer]:
      - /url: "#/bpp"
```

# Test source

```ts
  1  | import { test, expect, shot, listScenarios, API, openInspectorTab } from './helpers';
  2  | // Fork endpoint: POST /lab/api/scenarios/:id/fork (src/studio/api.ts:101-102); auto-fork on first edit of a
  3  | // built-in scenario saves as “我的场景” (src/studio/store.ts:398,428).
  4  | test('E Fork 超时重试：只生成一份“我的场景”', async ({ page }, info) => {
  5  |   const before = await listScenarios(page);
  6  |   // No built-in fleet_routing scenarios exist; built-in euclidean_cvrp uses GenericMap + TaskEditor (车辆容量).
  7  |   const builtin = before.find((s) => s.origin === 'builtin' && (s as any).problem_class === 'euclidean_cvrp');
  8  |   test.skip(!builtin, 'no built-in scenario');
  9  |   let forkCalls = 0;
  10 |   await page.route(`**${API}/scenarios/*/fork`, async (route) => {
  11 |     forkCalls++;
  12 |     const res = await route.fetch();
  13 |     await new Promise((r) => setTimeout(r, 45_000)); // beyond client timeout (uncertain exact value)
  14 |     await route.fulfill({ response: res }).catch(() => {});
  15 |   });
  16 |   await page.goto(`/#/plan/${encodeURIComponent(builtin.id)}`);
  17 |   await test.step('编辑内置场景触发自动另存', async () => {
  18 |     await openInspectorTab(page);
  19 |     const cap = page.getByLabel('车辆容量'); // lab/views/plan/TaskEditor.tsx:19
  20 |     await expect(cap).toBeVisible({ timeout: 30_000 });
  21 |     await cap.fill(String(Number(await cap.inputValue()) + 1));
  22 |     await cap.blur();
  23 |     await shot(page, info, 'edited-builtin');
  24 |     await expect.poll(() => forkCalls, { timeout: 20_000 }).toBeGreaterThan(0);
  25 |   });
  26 |   await test.step('等待超时与重试', async () => {
> 27 |     await page.waitForTimeout(60_000);
     |                ^ Error: page.waitForTimeout: Test ended.
  28 |     const retry = page.getByRole('button', { name: '重试保存' }); // PlanPanels.tsx:179
  29 |     if (await retry.isVisible()) { await retry.click(); await page.waitForTimeout(50_000); }
  30 |     await shot(page, info, 'after-retry');
  31 |   });
  32 |   await test.step('断言只有一份副本', async () => {
  33 |     const after = await listScenarios(page);
  34 |     const copies = after.filter((s) => !before.some((b) => b.id === s.id) && s.origin === 'user');
  35 |     info.annotations.push({ type: 'forkCalls', description: String(forkCalls) });
  36 |     expect(copies.length).toBe(1);
  37 |   });
  38 | });
  39 | 
```