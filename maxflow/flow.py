"""最大流与最小割。只用标准库。残量图 + BFS（Edmonds-Karp）。"""

from collections import deque


class FlowError(Exception):
    """输入不合法，消息里带第几条边。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def parse_edges(text):
    """把 "s-a:1,s-b:2" 解析成 (u, v, 容量) 列表；出错时报第几条边。"""
    edges = []
    for index, item in enumerate(text.split(","), start=1):
        item = item.strip()
        if not item:
            continue
        pair, sep, raw_cap = item.partition(":")
        left, dash, right = pair.partition("-")
        if not sep:
            raise FlowError("第%d条边缺少 ':'：%s" % (index, item))
        if not dash:
            raise FlowError("第%d条边缺少 '-'：%s" % (index, item))
        raw = raw_cap.strip()
        if not raw or not raw.isascii() or not raw.isdigit():
            raise FlowError("第%d条边容量必须是正十进制整数：%s" % (index, item))
        capacity = int(raw)
        if capacity <= 0:
            raise FlowError("第%d条边容量必须是正十进制整数：%s" % (index, item))
        edges.append((left.strip(), right.strip(), capacity))
    return edges


def build_caps(edges):
    """平行边容量相加，自环忽略。返回 {(u, v): 容量}。"""
    caps = {}
    for u, v, capacity in edges:
        if u == v:
            continue
        caps[(u, v)] = caps.get((u, v), 0) + capacity
    return caps


def _build_residual(caps):
    """正向边容量相加，同时为每条边建反向残量边（初始 0）。"""
    residual = {}
    for (u, v), capacity in caps.items():
        residual.setdefault(u, {})
        residual.setdefault(v, {})
        residual[u][v] = residual[u].get(v, 0) + capacity
        residual[v].setdefault(u, 0)
    return residual


def _bfs_parent(residual, source, sink):
    """在残量图上 BFS 找最短增广路，返回 parent 字典；到不了 sink 返回 None。"""
    parent = {source: None}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v, capacity in residual.get(u, {}).items():
            if capacity > 0 and v not in parent:
                parent[v] = u
                if v == sink:
                    return parent
                queue.append(v)
    return None


def _solve(edges, source, sink):
    """Edmonds-Karp：返回 (最大流, 残量图, 聚合容量)。"""
    caps = build_caps(edges)
    residual = _build_residual(caps)
    total = 0
    while True:
        parent = _bfs_parent(residual, source, sink)
        if parent is None:
            return total, residual, caps
        amount = None
        v = sink
        while v != source:
            u = parent[v]
            capacity = residual[u][v]
            amount = capacity if amount is None else min(amount, capacity)
            v = u
        v = sink
        while v != source:
            u = parent[v]
            residual[u][v] -= amount
            residual[v][u] = residual[v].get(u, 0) + amount
            v = u
        total += amount


def max_flow(edges, source, sink):
    """Edmonds-Karp 最大流，结果与边的书写顺序无关。"""
    total, _, _ = _solve(edges, source, sink)
    return total


def min_cut(edges, source, sink):
    """返回 (源侧可达顶点列表（按字母序）, 割容量)；割容量等于最大流。"""
    total, residual, caps = _solve(edges, source, sink)
    side = set()
    queue = deque([source])
    side.add(source)
    while queue:
        u = queue.popleft()
        for v, capacity in residual.get(u, {}).items():
            if capacity > 0 and v not in side:
                side.add(v)
                queue.append(v)
    capacity = sum(
        cap for (u, v), cap in caps.items() if u in side and v not in side
    )
    return sorted(side), capacity
