"""最大流与最小割。Edmonds-Karp（BFS 增广），只用标准库。"""

import re
from collections import deque


class FlowError(Exception):
    """输入不合法，消息里带第几条边。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


_CAPACITY_RE = re.compile(r"[0-9]+")


def parse_edges(text):
    """把 "s-a:1,s-b:2" 解析成 (u, v, 容量) 列表；出错时报第几条边。"""
    edges = []
    number = 0
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        number += 1
        pair, sep, raw_cap = item.partition(":")
        left, dash, right = pair.partition("-")
        if not sep or not dash or not left.strip() or not right.strip():
            raise FlowError("第%d条边格式不对（应为 u-v:容量）：%s" % (number, item))
        raw_cap = raw_cap.strip()
        if not _CAPACITY_RE.fullmatch(raw_cap):
            raise FlowError("第%d条边容量不是正十进制整数：%s" % (number, item))
        capacity = int(raw_cap)
        if capacity <= 0:
            raise FlowError("第%d条边容量必须为正整数：%s" % (number, item))
        edges.append((left.strip(), right.strip(), capacity))
    return edges


def build_caps(edges):
    """平行边容量相加，自环忽略；返回 {u: {v: 剩余容量}}，反向边初始为 0。"""
    caps = {}
    for u, v, capacity in edges:
        if u == v:
            continue
        row = caps.setdefault(u, {})
        row[v] = row.get(v, 0) + capacity
        caps.setdefault(v, {}).setdefault(u, 0)
    return caps


def _augment(caps, source, sink):
    """在残量图上 BFS 找最短增广路并增广，返回本次流量（0 表示没有增广路）。"""
    if source == sink:
        return 0
    parent = {source: None}
    queue = deque([source])
    while queue and sink not in parent:
        u = queue.popleft()
        for v, remaining in caps.get(u, {}).items():
            if remaining > 0 and v not in parent:
                parent[v] = u
                if v == sink:
                    break
                queue.append(v)
    if sink not in parent:
        return 0
    amount = None
    node = sink
    while node != source:
        remaining = caps[parent[node]][node]
        amount = remaining if amount is None else min(amount, remaining)
        node = parent[node]
    node = sink
    while node != source:
        prev = parent[node]
        caps[prev][node] -= amount
        caps[node][prev] = caps[node].get(prev, 0) + amount
        node = prev
    return amount


def _run_max_flow(caps, source, sink):
    total = 0
    while True:
        amount = _augment(caps, source, sink)
        if amount == 0:
            return total
        total += amount


def max_flow(edges, source, sink):
    """Edmonds-Karp 最大流，结果与边的书写顺序无关。"""
    return _run_max_flow(build_caps(edges), source, sink)


def min_cut(edges, source, sink):
    """返回 (源侧可达顶点列表, 割容量)；割容量等于最大流。"""
    caps = build_caps(edges)
    _run_max_flow(caps, source, sink)
    side = {source}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v, remaining in caps.get(u, {}).items():
            if remaining > 0 and v not in side:
                side.add(v)
                queue.append(v)
    capacity = 0
    for u, v, cap in edges:
        if u != v and u in side and v not in side:
            capacity += cap
    return sorted(side), capacity
