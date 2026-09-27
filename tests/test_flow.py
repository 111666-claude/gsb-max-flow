import io
import itertools
import random
import time
import unittest
from contextlib import redirect_stdout

from maxflow.cli import main
from maxflow.flow import FlowError, max_flow, min_cut, parse_edges


class ParseTest(unittest.TestCase):
    def test_two_edges(self):
        self.assertEqual(parse_edges("s-a:2,b-t:3"), [("s", "a", 2), ("b", "t", 3)])

    def test_blank_items_are_skipped(self):
        self.assertEqual(parse_edges("s-a:1,"), [("s", "a", 1)])

    def test_missing_colon(self):
        with self.assertRaises(FlowError):
            parse_edges("s-a")

    def test_missing_dash(self):
        with self.assertRaises(FlowError):
            parse_edges("sa:1")

    def test_error_reports_edge_index(self):
        with self.assertRaises(FlowError) as caught:
            parse_edges("s-a:1,a-b:2,ab:3")
        self.assertIn("第3条边", str(caught.exception))

    def test_negative_capacity(self):
        with self.assertRaises(FlowError) as caught:
            parse_edges("s-a:-2")
        self.assertIn("第1条边", str(caught.exception))

    def test_zero_capacity(self):
        with self.assertRaises(FlowError) as caught:
            parse_edges("s-a:0")
        self.assertIn("第1条边", str(caught.exception))

    def test_non_numeric_capacity(self):
        with self.assertRaises(FlowError) as caught:
            parse_edges("s-a:1,b-t:x")
        self.assertIn("第2条边", str(caught.exception))

    def test_missing_colon_reports_index(self):
        with self.assertRaises(FlowError) as caught:
            parse_edges("s-a:1,b-t")
        self.assertIn("第2条边", str(caught.exception))


class FlowTest(unittest.TestCase):
    def test_single_path(self):
        self.assertEqual(max_flow(parse_edges("s-a:3,a-t:3"), "s", "t"), 3)

    def test_parallel_edges_add_up(self):
        self.assertEqual(max_flow(parse_edges("s-a:1,s-a:2,a-t:5"), "s", "t"), 3)

    def test_self_loop_is_ignored(self):
        self.assertEqual(max_flow(parse_edges("s-a:2,a-a:9,a-t:2"), "s", "t"), 2)

    def test_no_path(self):
        self.assertEqual(max_flow(parse_edges("a-b:4"), "s", "t"), 0)

    def test_empty_graph(self):
        self.assertEqual(max_flow([], "s", "t"), 0)

    def test_flow_is_not_negative(self):
        self.assertGreaterEqual(max_flow(parse_edges("s-a:1,a-t:1"), "s", "t"), 0)

    def test_residual_back_edges(self):
        # 经典反例：必须靠反向残量边把 a-b 的流量让回去才能到 2。
        edges = parse_edges("s-a:1,s-b:1,a-b:1,a-t:1,b-t:1")
        self.assertEqual(max_flow(edges, "s", "t"), 2)

    def test_edge_order_does_not_matter(self):
        forward = max_flow(parse_edges("s-a:1,s-b:1,a-b:1,a-t:1,b-t:1"), "s", "t")
        backward = max_flow(parse_edges("b-t:1,a-t:1,a-b:1,s-b:1,s-a:1"), "s", "t")
        self.assertEqual(forward, backward)

    def test_deterministic(self):
        edges = parse_edges("s-a:3,s-b:2,a-b:1,a-t:2,b-t:4")
        first = max_flow(edges, "s", "t")
        for _ in range(5):
            self.assertEqual(max_flow(edges, "s", "t"), first)


class MinCutTest(unittest.TestCase):
    def test_min_cut_matches_flow(self):
        edges = parse_edges("s-a:3,a-t:3")
        side, capacity = min_cut(edges, "s", "t")
        self.assertEqual(capacity, max_flow(edges, "s", "t"))
        self.assertEqual(side, ["s"])

    def test_min_cut_classic(self):
        edges = parse_edges("s-a:1,s-b:1,a-b:1,a-t:1,b-t:1")
        side, capacity = min_cut(edges, "s", "t")
        self.assertEqual(capacity, 2)
        self.assertEqual(side, ["s"])

    def test_min_cut_side_sorted(self):
        edges = parse_edges("s-c:1,c-a:1,s-b:1,b-t:1,a-t:1")
        side, capacity = min_cut(edges, "s", "t")
        self.assertEqual(side, sorted(side))
        self.assertEqual(capacity, max_flow(edges, "s", "t"))

    def test_min_cut_no_path(self):
        side, capacity = min_cut(parse_edges("a-b:4"), "s", "t")
        self.assertEqual(side, ["s"])
        self.assertEqual(capacity, 0)


def brute_force_min_cut(edges, source, sink):
    """穷举所有割取最小容量，作为对照实现。"""
    caps = {}
    vertices = set()
    for u, v, capacity in edges:
        if u == v:
            continue
        caps[(u, v)] = caps.get((u, v), 0) + capacity
        vertices.add(u)
        vertices.add(v)
    others = sorted(vertices - {source, sink})
    best = None
    for size in range(len(others) + 1):
        for combo in itertools.combinations(others, size):
            side = {source} | set(combo)
            capacity = sum(
                cap for (u, v), cap in caps.items() if u in side and v not in side
            )
            if best is None or capacity < best:
                best = capacity
    return best


class BruteForceCrossCheckTest(unittest.TestCase):
    def test_random_small_graphs_match_brute_force(self):
        rng = random.Random(20260927)
        mismatches = 0
        for _ in range(200):
            count = rng.randint(2, 10)
            vertices = ["v%d" % i for i in range(count)]
            source, sink = vertices[0], vertices[-1]
            edges = []
            for _ in range(rng.randint(0, 2 * count)):
                u = rng.choice(vertices)
                v = rng.choice(vertices)
                edges.append((u, v, rng.randint(1, 9)))
            if max_flow(edges, source, sink) != brute_force_min_cut(edges, source, sink):
                mismatches += 1
            side, capacity = min_cut(edges, source, sink)
            self.assertEqual(capacity, max_flow(edges, source, sink))
        self.assertEqual(mismatches, 0)


class ScaleTest(unittest.TestCase):
    def test_thousand_vertices_twenty_thousand_edges(self):
        rng = random.Random(7)
        count = 1000
        vertices = ["v%d" % i for i in range(count)]
        edges = []
        for _ in range(20000):
            u = rng.choice(vertices)
            v = rng.choice(vertices)
            if u != v:
                edges.append((u, v, rng.randint(1, 100)))
        start = time.time()
        value = max_flow(edges, vertices[0], vertices[-1])
        elapsed = time.time() - start
        self.assertGreaterEqual(value, 0)
        self.assertLess(elapsed, 30)


class CliTest(unittest.TestCase):
    def test_prints_flow(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", "s-a:2,a-t:2", "--source", "s", "--sink", "t"])
        self.assertEqual(code, 0)
        self.assertEqual(buffer.getvalue().strip(), "flow=2")

    def test_missing_edges(self):
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
