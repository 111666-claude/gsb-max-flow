# max-flow

有向图最大流与最小割，只用 Python 标准库。

```
python3 -m maxflow.cli --edges 's-a:1,s-b:1,a-b:1,a-t:1,b-t:1' --source s --sink t
python3 -m maxflow.cli --edges 's-a:3,a-t:3' --source s --sink t --min-cut
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **增广要在残量图上做**：`--edges 's-a:1,s-b:1,a-b:1,a-t:1,b-t:1'` 按口径是 `flow=2`
  （先走 s-a-t 与 s-b-t，中间那条 a-b 要靠反向残量边把流量让回去），现在给 `flow=1`。
- **增广路用 BFS（Edmonds-Karp）**：每次挑最短增广路，复杂度 O(V·E²)；结果与边的书写顺序无关。
- **最小割**：`--min-cut` 在 flow 行之后追加两行，`cut=` 是源侧可达顶点（残量图上从 source 做 BFS，
  按字母序逗号分隔），`cut_capacity=` 是这些顶点指出去的边容量之和；割容量必须等于最大流。
- 输入：`--edges` 是逗号分隔的 `u-v:容量`；同一对 u-v 写多次按容量相加（平行边）；
  自环忽略；容量必须为正十进制整数，负数、零、非数字、缺 `:`、缺 `-` 都要报错并指出是第几条边。
- 不变量：除 source/sink 外每个顶点的净流出为 0（流量守恒）；每条边的流量不超过容量；
  `max_flow == min_cut`；同一输入重复运行结果相同。
- 规模：1000 个顶点、2 万条边要在几秒内算完，内存 O(V+E)；不许把整张图复制多份。
- 对照自证：顶点数 ≤ 10 的小图，要与「枚举所有割取最小容量」的穷举实现逐例一致。

## 实现

- 残量图上每条边都有反向残量边，增广路用 BFS（Edmonds-Karp），上面的经典反例给 `flow=2`。
- `--min-cut` 在 flow 行之后追加 `cut=`（源侧可达顶点，按字母序）与 `cut_capacity=`，割容量等于最大流。
- 输入报错会指出是第几条边（缺 `:`、缺 `-`、容量非正十进制整数）。

## 计划新增的能力

```
--edges 边表        逗号分隔的 u-v:容量
--source / --sink   源点与汇点
--min-cut           额外输出最小割
```

## 输出

```
flow=2
```

## 目录

```
maxflow/flow.py   解析、增广与最小割
maxflow/cli.py    命令行入口
tests/            unittest 用例
```
