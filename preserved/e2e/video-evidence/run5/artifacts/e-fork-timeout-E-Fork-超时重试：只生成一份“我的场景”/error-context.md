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
                  - generic [ref=e111]: 我的任务地图 · 15
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
                - generic [ref=e173]:
                  - generic [ref=e174]: 我的其他场景 · 2
                  - list [ref=e175]:
                    - listitem [ref=e176]:
                      - button "车间空地 · 欧氏 CVRP（我的） 车辆路径 CVRP · 仿真地图 · depot · 10 个任务" [ref=e177] [cursor=pointer]:
                        - generic [ref=e178]: 车间空地 · 欧氏 CVRP（我的）
                        - generic [ref=e179]: 车辆路径 CVRP · 仿真地图 · depot · 10 个任务
                    - listitem [ref=e180]:
                      - button "车间空地 · 欧氏 CVRP（我的） 车辆路径 CVRP · 仿真地图 · depot · 10 个任务" [ref=e181] [cursor=pointer]:
                        - generic [ref=e182]: 车间空地 · 欧氏 CVRP（我的）
                        - generic [ref=e183]: 车辆路径 CVRP · 仿真地图 · depot · 10 个任务
                - generic [ref=e184]:
                  - generic [ref=e185]: 仿真地图 · 8
                  - list [ref=e186]:
                    - listitem [ref=e187]:
                      - button "官方迷宫 · 双点巡检闭环 转弯约束路网 · 仿真地图 · maze · 2 个任务" [ref=e188] [cursor=pointer]:
                        - generic [ref=e189]: 官方迷宫 · 双点巡检闭环
                        - generic [ref=e190]: 转弯约束路网 · 仿真地图 · maze · 2 个任务
                    - listitem [ref=e191]:
                      - button "仓储货架通道 · 作物行代理 转弯约束路网 · 仿真地图 · warehouse · 5 个任务" [ref=e192] [cursor=pointer]:
                        - generic [ref=e193]: 仓储货架通道 · 作物行代理
                        - generic [ref=e194]: 转弯约束路网 · 仿真地图 · warehouse · 5 个任务
                    - listitem [ref=e195]:
                      - button "车间空地 · 欧氏 CVRP 车辆路径 CVRP · 仿真地图 · depot · 10 个任务" [ref=e196] [cursor=pointer]:
                        - generic [ref=e197]: 车间空地 · 欧氏 CVRP
                        - generic [ref=e198]: 车辆路径 CVRP · 仿真地图 · depot · 10 个任务
                    - listitem [ref=e199]:
                      - button "车间空地 · 内缩作业区覆盖 覆盖作业 · 仿真地图 · depot" [ref=e200] [cursor=pointer]:
                        - generic [ref=e201]: 车间空地 · 内缩作业区覆盖
                        - generic [ref=e202]: 覆盖作业 · 仿真地图 · depot
                    - listitem [ref=e203]:
                      - button "仓库 · 跨通道到达 点到点规划 · 仿真地图 · warehouse" [ref=e204] [cursor=pointer]:
                        - generic [ref=e205]: 仓库 · 跨通道到达
                        - generic [ref=e206]: 点到点规划 · 仿真地图 · warehouse
                    - listitem [ref=e207]:
                      - button "仓库 · 农机转弯半径 点到点规划 · 仿真地图 · warehouse" [ref=e208] [cursor=pointer]:
                        - generic [ref=e209]: 仓库 · 农机转弯半径
                        - generic [ref=e210]: 点到点规划 · 仿真地图 · warehouse
                    - listitem [ref=e211]:
                      - button "迷宫 · 对角穿越 点到点规划 · 仿真地图 · maze" [ref=e212] [cursor=pointer]:
                        - generic [ref=e213]: 迷宫 · 对角穿越
                        - generic [ref=e214]: 点到点规划 · 仿真地图 · maze
                    - listitem [ref=e215]:
                      - button "车间 · 可倒车泊位 点到点规划 · 仿真地图 · depot" [ref=e216] [cursor=pointer]:
                        - generic [ref=e217]: 车间 · 可倒车泊位
                        - generic [ref=e218]: 点到点规划 · 仿真地图 · depot
                - generic [ref=e219]:
                  - generic [ref=e220]: 基准算例 · 26
                  - list [ref=e221]:
                    - listitem [ref=e222]:
                      - button "转弯路网 g3x3_s8000_uturn 转弯约束路网 · 基准算例 · 5 个任务" [ref=e223] [cursor=pointer]:
                        - generic [ref=e224]: 转弯路网 g3x3_s8000_uturn
                        - generic [ref=e225]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e226]:
                      - button "转弯路网 g3x3_s8001_left_cost 转弯约束路网 · 基准算例 · 5 个任务" [ref=e227] [cursor=pointer]:
                        - generic [ref=e228]: 转弯路网 g3x3_s8001_left_cost
                        - generic [ref=e229]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e230]:
                      - button "转弯路网 g3x3_s8002_left_ban 转弯约束路网 · 基准算例 · 5 个任务" [ref=e231] [cursor=pointer]:
                        - generic [ref=e232]: 转弯路网 g3x3_s8002_left_ban
                        - generic [ref=e233]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e234]:
                      - button "转弯路网 g3x3_s8003_uturn 转弯约束路网 · 基准算例 · 5 个任务" [ref=e235] [cursor=pointer]:
                        - generic [ref=e236]: 转弯路网 g3x3_s8003_uturn
                        - generic [ref=e237]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e238]:
                      - button "转弯路网 g3x3_s8004_left_cost 转弯约束路网 · 基准算例 · 5 个任务" [ref=e239] [cursor=pointer]:
                        - generic [ref=e240]: 转弯路网 g3x3_s8004_left_cost
                        - generic [ref=e241]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e242]:
                      - button "转弯路网 g3x3_s8005_left_ban 转弯约束路网 · 基准算例 · 5 个任务" [ref=e243] [cursor=pointer]:
                        - generic [ref=e244]: 转弯路网 g3x3_s8005_left_ban
                        - generic [ref=e245]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e246]:
                      - button "转弯路网 g3x3_s10000_uturn 转弯约束路网 · 基准算例 · 5 个任务" [ref=e247] [cursor=pointer]:
                        - generic [ref=e248]: 转弯路网 g3x3_s10000_uturn
                        - generic [ref=e249]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e250]:
                      - button "转弯路网 g3x3_s10000_left_cost 转弯约束路网 · 基准算例 · 5 个任务" [ref=e251] [cursor=pointer]:
                        - generic [ref=e252]: 转弯路网 g3x3_s10000_left_cost
                        - generic [ref=e253]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e254]:
                      - button "转弯路网 g3x3_s10000_left_ban 转弯约束路网 · 基准算例 · 5 个任务" [ref=e255] [cursor=pointer]:
                        - generic [ref=e256]: 转弯路网 g3x3_s10000_left_ban
                        - generic [ref=e257]: 转弯约束路网 · 基准算例 · 5 个任务
                    - listitem [ref=e258]:
                      - button "转弯路网 g3x4_s10000_uturn 转弯约束路网 · 基准算例 · 6 个任务" [ref=e259] [cursor=pointer]:
                        - generic [ref=e260]: 转弯路网 g3x4_s10000_uturn
                        - generic [ref=e261]: 转弯约束路网 · 基准算例 · 6 个任务
                    - listitem [ref=e262]:
                      - button "转弯路网 g3x4_s10000_left_cost 转弯约束路网 · 基准算例 · 6 个任务" [ref=e263] [cursor=pointer]:
                        - generic [ref=e264]: 转弯路网 g3x4_s10000_left_cost
                        - generic [ref=e265]: 转弯约束路网 · 基准算例 · 6 个任务
                    - listitem [ref=e266]:
                      - button "转弯路网 g3x4_s10000_left_ban 转弯约束路网 · 基准算例 · 6 个任务" [ref=e267] [cursor=pointer]:
                        - generic [ref=e268]: 转弯路网 g3x4_s10000_left_ban
                        - generic [ref=e269]: 转弯约束路网 · 基准算例 · 6 个任务
                    - listitem [ref=e270]:
                      - button "转弯路网 g4x4_s10000_uturn 转弯约束路网 · 基准算例 · 7 个任务" [ref=e271] [cursor=pointer]:
                        - generic [ref=e272]: 转弯路网 g4x4_s10000_uturn
                        - generic [ref=e273]: 转弯约束路网 · 基准算例 · 7 个任务
                    - listitem [ref=e274]:
                      - button "转弯路网 g4x4_s10000_left_cost 转弯约束路网 · 基准算例 · 7 个任务" [ref=e275] [cursor=pointer]:
                        - generic [ref=e276]: 转弯路网 g4x4_s10000_left_cost
                        - generic [ref=e277]: 转弯约束路网 · 基准算例 · 7 个任务
                    - listitem [ref=e278]:
                      - button "转弯路网 g4x4_s10000_left_ban 转弯约束路网 · 基准算例 · 7 个任务" [ref=e279] [cursor=pointer]:
                        - generic [ref=e280]: 转弯路网 g4x4_s10000_left_ban
                        - generic [ref=e281]: 转弯约束路网 · 基准算例 · 7 个任务
                    - listitem [ref=e282]:
                      - button "夹具 dead_end_infeasible 转弯约束路网 · 基准算例 · 1 个任务" [ref=e283] [cursor=pointer]:
                        - generic [ref=e284]: 夹具 dead_end_infeasible
                        - generic [ref=e285]: 转弯约束路网 · 基准算例 · 1 个任务
                    - listitem [ref=e286]:
                      - button "夹具 single_customer_cycle 转弯约束路网 · 基准算例 · 1 个任务" [ref=e287] [cursor=pointer]:
                        - generic [ref=e288]: 夹具 single_customer_cycle
                        - generic [ref=e289]: 转弯约束路网 · 基准算例 · 1 个任务
                    - listitem [ref=e290]:
                      - button "夹具 g3x3_s7000_none 转弯约束路网 · 基准算例 · 4 个任务" [ref=e291] [cursor=pointer]:
                        - generic [ref=e292]: 夹具 g3x3_s7000_none
                        - generic [ref=e293]: 转弯约束路网 · 基准算例 · 4 个任务
                    - listitem [ref=e294]:
                      - button "欧氏 CVRP · 均匀分布 n=20 车辆路径 CVRP · 基准算例 · 20 个任务" [ref=e295] [cursor=pointer]:
                        - generic [ref=e296]: 欧氏 CVRP · 均匀分布 n=20
                        - generic [ref=e297]: 车辆路径 CVRP · 基准算例 · 20 个任务
                    - listitem [ref=e298]:
                      - button "欧氏 CVRP · 均匀分布 n=50 车辆路径 CVRP · 基准算例 · 50 个任务" [ref=e299] [cursor=pointer]:
                        - generic [ref=e300]: 欧氏 CVRP · 均匀分布 n=50
                        - generic [ref=e301]: 车辆路径 CVRP · 基准算例 · 50 个任务
                    - listitem [ref=e302]:
                      - button "欧氏 CVRP · 均匀分布 n=100 车辆路径 CVRP · 基准算例 · 100 个任务" [ref=e303] [cursor=pointer]:
                        - generic [ref=e304]: 欧氏 CVRP · 均匀分布 n=100
                        - generic [ref=e305]: 车辆路径 CVRP · 基准算例 · 100 个任务
                    - listitem [ref=e306]:
                      - button "欧氏 CVRP · 均匀分布 n=200 车辆路径 CVRP · 基准算例 · 200 个任务" [ref=e307] [cursor=pointer]:
                        - generic [ref=e308]: 欧氏 CVRP · 均匀分布 n=200
                        - generic [ref=e309]: 车辆路径 CVRP · 基准算例 · 200 个任务
                    - listitem [ref=e310]:
                      - button "欧氏 CVRP · 聚簇分布 n=20 车辆路径 CVRP · 基准算例 · 20 个任务" [ref=e311] [cursor=pointer]:
                        - generic [ref=e312]: 欧氏 CVRP · 聚簇分布 n=20
                        - generic [ref=e313]: 车辆路径 CVRP · 基准算例 · 20 个任务
                    - listitem [ref=e314]:
                      - button "欧氏 CVRP · 聚簇分布 n=50 车辆路径 CVRP · 基准算例 · 50 个任务" [ref=e315] [cursor=pointer]:
                        - generic [ref=e316]: 欧氏 CVRP · 聚簇分布 n=50
                        - generic [ref=e317]: 车辆路径 CVRP · 基准算例 · 50 个任务
                    - listitem [ref=e318]:
                      - button "欧氏 CVRP · 聚簇分布 n=100 车辆路径 CVRP · 基准算例 · 100 个任务" [ref=e319] [cursor=pointer]:
                        - generic [ref=e320]: 欧氏 CVRP · 聚簇分布 n=100
                        - generic [ref=e321]: 车辆路径 CVRP · 基准算例 · 100 个任务
                    - listitem [ref=e322]:
                      - button "欧氏 CVRP · 聚簇分布 n=200 车辆路径 CVRP · 基准算例 · 200 个任务" [ref=e323] [cursor=pointer]:
                        - generic [ref=e324]: 欧氏 CVRP · 聚簇分布 n=200
                        - generic [ref=e325]: 车辆路径 CVRP · 基准算例 · 200 个任务
        - generic [ref=e331]:
          - region "地图" [ref=e333]:
            - tablist [ref=e336]:
              - tab "地图" [selected] [ref=e337] [cursor=pointer]:
                - generic [ref=e338]:
                  - generic [ref=e339]: 地图
                  - button "Close 地图" [ref=e340]
            - tabpanel "地图" [ref=e344]
          - region "方案对比" [ref=e346]:
            - tablist [ref=e349]:
              - tab "方案对比" [selected] [ref=e350] [cursor=pointer]:
                - generic [ref=e351]:
                  - generic [ref=e352]: 方案对比
                  - button "Close 方案对比" [ref=e353]
              - tab "验算" [ref=e356] [cursor=pointer]
              - tab "实验结果" [ref=e359] [cursor=pointer]
              - tab "仿真回放" [ref=e362] [cursor=pointer]
              - tab "科研图表" [ref=e365] [cursor=pointer]
              - tab "日志" [ref=e368] [cursor=pointer]
            - tabpanel "方案对比" [ref=e372]:
              - generic [ref=e373]:
                - generic [ref=e374]:
                  - paragraph [ref=e384]: 还没有方案
                  - paragraph [ref=e385]: 在“推荐与求解”里勾选算法后点击对比，结果会出现在这里。
                - generic "历史运行" [ref=e386]:
                  - button "历史运行（本场景，含失败/已隔离/身份未核验）" [ref=e387] [cursor=pointer]
        - region "检查器" [ref=e393]:
          - tablist [ref=e396]:
            - tab "推荐与求解" [ref=e397] [cursor=pointer]
            - tab "检查器" [selected] [ref=e400] [cursor=pointer]:
              - generic [ref=e401]:
                - generic [ref=e402]: 检查器
                - button "Close 检查器" [ref=e403]
            - tab "决策记录" [ref=e406] [cursor=pointer]
          - tabpanel "检查器" [ref=e410]:
            - generic [ref=e412]:
              - generic [ref=e413]:
                - heading "规划问题与约束" [level=3] [ref=e414]
                - alert [ref=e415]:
                  - generic [ref=e418]:
                    - text: 未保存：请求超时（30000 ms）：/scenarios/cvrp-depot-floor/fork
                    - generic [ref=e419]:
                      - button "重试保存" [ref=e420] [cursor=pointer]
                      - button "另存草稿副本" [ref=e421] [cursor=pointer]
                - paragraph [ref=e422]: 坐标：map · m · X 向右 / Y 向上。角度输入为度，提交保存为弧度。
                - generic [ref=e423]:
                  - text: 车辆容量
                  - spinbutton "车辆容量" [ref=e424]: "9"
                - group [ref=e425]:
                  - generic "任务清单 · 10 项" [ref=e426]
                - generic [ref=e427]:
                  - generic [ref=e428]:
                    - text: 新任务 X
                    - spinbutton "新任务 X" [ref=e429]: "0"
                  - generic [ref=e430]:
                    - text: 新任务 Y
                    - spinbutton "新任务 Y" [ref=e431]: "0"
                  - button "添加任务点" [ref=e432] [cursor=pointer]
                - group [ref=e433]:
                  - generic "完整任务输入 · JSON" [ref=e434]
              - generic [ref=e435]:
                - heading "车间空地 · 欧氏 CVRP" [level=3] [ref=e436]
                - paragraph [ref=e437]: 官方 depot 地图左侧开阔地面 10 个任务点，仓库 = 机器人起点；直线段经地图间隙检查（可能穿过柱子，会如实报告）。
                - paragraph [ref=e438]: 任务点由固定种子在空闲区域内抽样（只按点位间隙筛选，不按求解结果筛选）；路线为直线段，碰撞由 map_check 报告。
                - link "场景 JSON" [ref=e440] [cursor=pointer]:
                  - /url: /lab/api/scenarios/cvrp-depot-floor/export?format=json
      - status [ref=e444]: 日志 opened
      - alert [ref=e445]
    - generic [ref=e448]:
      - generic [ref=e449]:
        - generic [ref=e450]: 官方 depot 地图左侧开阔地面 10 个任务点，仓库 = 机器人起点；直线段经地图间隙检查（可能穿过柱子，会如实报告）。
        - generic "请求超时（30000 ms）：/scenarios/cvrp-depot-floor/fork" [ref=e451]: 保存失败
        - button "经典视图" [ref=e452] [cursor=pointer]
      - application "场景地图。拖动平移，滚轮或双指缩放，加减号缩放，0 适应内容。" [ref=e454]:
        - img [aria-hidden] [ref=e455]:
          - generic [ref=e461]:
            - generic [ref=e462]: D
            - generic [ref=e463]: P1
            - generic [ref=e464]: P2
            - generic [ref=e465]: P3
            - generic [ref=e466]: P4
            - generic [ref=e467]: P5
            - generic [ref=e468]: P6
            - generic [ref=e469]: P7
            - generic [ref=e470]: P8
            - generic [ref=e471]: P9
            - generic [ref=e472]: P10
            - generic [ref=e473]: D
            - generic [ref=e476]: P1 · 2
            - generic [ref=e479]: P2 · 1
            - generic [ref=e482]: P3 · 2
            - generic [ref=e485]: P4 · 3
            - generic [ref=e488]: P5 · 1
            - generic [ref=e491]: P6 · 2
            - generic [ref=e494]: P7 · 3
            - generic [ref=e497]: P8 · 2
            - generic [ref=e500]: P9 · 1
            - generic [ref=e503]: P10 · 1
        - generic:
          - generic "map 坐标系，单位米": 2 m
        - generic [ref=e507]:
          - button "放大" [ref=e508] [cursor=pointer]
          - button "缩小" [ref=e510] [cursor=pointer]
          - button "适应内容" [ref=e512] [cursor=pointer]
  - contentinfo [ref=e518]:
    - generic [ref=e519]: 已连接
    - generic [ref=e521]: 求解空闲
    - generic [ref=e522]: 田间：未运行 · TB4：未运行
    - generic [ref=e526]: 车间空地 · 欧氏 CVRP
    - link "CVRP 数值任务" [ref=e527] [cursor=pointer]:
      - /url: "#/jobs"
    - link "BPP 历史" [ref=e528] [cursor=pointer]:
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