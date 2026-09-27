"""最大流与最小割。只用标准库。缺陷：残量图不完整，最小割没实现。"""


class FlowError(Exception):
    """输入不合法。缺陷：不带边下标。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def parse_edges(text):
    """把 "s-a:1,s-b:2" 解析成 (u, v, 容量) 列表。缺陷：出错时不带边下标。"""
    edges = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        pair, sep, raw_cap = item.partition(":")
        left, dash, right = pair.partition("-")
        if not sep or not dash:
            raise FlowError("边格式不对：%s" % item)
        edges.append((left.strip(), right.strip(), int(raw_cap)))
    return edges


def build_caps(edges):
    """缺陷：只累积正向容量，没有反向残量边。"""
    caps = {}
    for u, v, capacity in edges:
        if u == v:
            continue
        caps[(u, v)] = caps.get((u, v), 0) + capacity
    return caps


def _find_path(caps, source, sink, seen):
    """缺陷：只在正向剩余容量上做 DFS，退不回去。"""
    if source == sink:
        return []
    seen.add(source)
    for (u, v), capacity in caps.items():
        if u != source or capacity <= 0 or v in seen:
            continue
        if v == sink:
            return [(u, v)]
        rest = _find_path(caps, v, sink, seen)
        if rest:
            return [(u, v)] + rest
    return None


def max_flow(edges, source, sink):
    """缺陷：增广只用正向剩余容量，残量图上没有反向边。"""
    caps = build_caps(edges)
    total = 0
    while True:
        path = _find_path(caps, source, sink, set())
        if not path:
            return total
        amount = min(caps[edge] for edge in path)
        for edge in path:
            caps[edge] -= amount
        total += amount


def min_cut(edges, source, sink):
    """缺陷：还没实现。"""
    raise FlowError("最小割还没实现")
