import io
import itertools
import random
import unittest
from contextlib import redirect_stdout

from maxflow.cli import main
from maxflow.flow import FlowError, build_caps, max_flow, min_cut, parse_edges, _run_max_flow


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

    def test_error_reports_edge_number(self):
        with self.assertRaises(FlowError) as ctx:
            parse_edges("s-a:1,b-c")
        self.assertIn("第2条", str(ctx.exception))

    def test_negative_capacity_rejected(self):
        with self.assertRaises(FlowError) as ctx:
            parse_edges("s-a:1,a-t:-2")
        self.assertIn("第2条", str(ctx.exception))

    def test_zero_capacity_rejected(self):
        with self.assertRaises(FlowError) as ctx:
            parse_edges("s-a:0")
        self.assertIn("第1条", str(ctx.exception))

    def test_non_numeric_capacity_rejected(self):
        with self.assertRaises(FlowError) as ctx:
            parse_edges("s-a:x")
        self.assertIn("第1条", str(ctx.exception))

    def test_missing_dash_reports_edge_number(self):
        with self.assertRaises(FlowError) as ctx:
            parse_edges("s-a:1,bt:2")
        self.assertIn("第2条", str(ctx.exception))


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

    def test_residual_graph_allows_canceling(self):
        # 经典反例：必须靠反向残量边把 a-b 的流量让回去才能到 2
        edges = parse_edges("s-a:1,s-b:1,a-b:1,a-t:1,b-t:1")
        self.assertEqual(max_flow(edges, "s", "t"), 2)

    def test_result_independent_of_edge_order(self):
        text = "s-a:1,s-b:1,a-b:1,a-t:1,b-t:1"
        expected = max_flow(parse_edges(text), "s", "t")
        rng = random.Random(7)
        items = text.split(",")
        for _ in range(20):
            rng.shuffle(items)
            self.assertEqual(max_flow(parse_edges(",".join(items)), "s", "t"), expected)

    def test_deterministic_across_runs(self):
        edges = parse_edges("s-a:2,s-b:1,a-b:1,a-t:1,b-t:2")
        self.assertEqual(max_flow(edges, "s", "t"), max_flow(edges, "s", "t"))


class MinCutTest(unittest.TestCase):
    def test_min_cut_matches_max_flow(self):
        edges = parse_edges("s-a:1,s-b:1,a-b:1,a-t:1,b-t:1")
        side, capacity = min_cut(edges, "s", "t")
        self.assertEqual(capacity, max_flow(edges, "s", "t"))
        self.assertEqual(side, ["s"])

    def test_min_cut_sorted_source_side(self):
        edges = parse_edges("s-a:3,a-t:3")
        side, capacity = min_cut(edges, "s", "t")
        self.assertEqual(side, ["s"])
        self.assertEqual(capacity, 3)

    def test_min_cut_multiple_vertices_on_source_side(self):
        edges = parse_edges("s-a:5,a-b:5,b-t:1")
        side, capacity = min_cut(edges, "s", "t")
        self.assertEqual(side, ["a", "b", "s"])
        self.assertEqual(capacity, 1)


class InvariantTest(unittest.TestCase):
    def _net_flows(self, edges, source, sink):
        caps = build_caps(edges)
        _run_max_flow(caps, source, sink)
        original = {}
        for u, v, capacity in edges:
            if u != v:
                original[(u, v)] = original.get((u, v), 0) + capacity
        vertices = set()
        for u, v, _ in edges:
            vertices.add(u)
            vertices.add(v)
        net = {}
        for u in vertices:
            for v in vertices:
                if u != v:
                    net[(u, v)] = original.get((u, v), 0) - caps.get(u, {}).get(v, 0)
        return vertices, original, net

    def test_conservation_and_capacity(self):
        rng = random.Random(11)
        for _ in range(50):
            vertices = ["s", "t"] + ["v%d" % i for i in range(rng.randint(1, 6))]
            edges = []
            for _ in range(rng.randint(1, 15)):
                u, v = rng.sample(vertices, 2)
                edges.append((u, v, rng.randint(1, 9)))
            all_vertices, original, net = self._net_flows(edges, "s", "t")
            for x in all_vertices:
                if x in ("s", "t"):
                    continue
                outflow = sum(net[(x, v)] for v in all_vertices if v != x)
                self.assertEqual(outflow, 0, "顶点 %s 净流出不为 0" % x)
            for (u, v), capacity in original.items():
                self.assertLessEqual(net[(u, v)], capacity)
                self.assertGreaterEqual(net[(u, v)], -original.get((v, u), 0))


class BruteForceTest(unittest.TestCase):
    def _brute_force_min_cut(self, edges, source, sink):
        vertices = sorted({u for u, _, _ in edges} | {v for _, v, _ in edges})
        others = [v for v in vertices if v not in (source, sink)]
        best = None
        for size in range(len(others) + 1):
            for combo in itertools.combinations(others, size):
                side = {source} | set(combo)
                capacity = sum(
                    cap for u, v, cap in edges if u != v and u in side and v not in side
                )
                if best is None or capacity < best:
                    best = capacity
        return best if best is not None else 0

    def test_matches_brute_force_on_200_random_graphs(self):
        rng = random.Random(20260927)
        mismatches = 0
        for _ in range(200):
            count = rng.randint(2, 10)
            vertices = ["s", "t"] + ["v%d" % i for i in range(count - 2)]
            edges = []
            for _ in range(rng.randint(0, 20)):
                u = rng.choice(vertices)
                v = rng.choice(vertices)
                if u == v and rng.random() < 0.5:
                    pass  # 偶尔保留自环，确认被忽略
                edges.append((u, v, rng.randint(1, 9)))
            expected = self._brute_force_min_cut(edges, "s", "t")
            actual = max_flow(edges, "s", "t")
            _, cut_capacity = min_cut(edges, "s", "t")
            if actual != expected or cut_capacity != expected:
                mismatches += 1
        self.assertEqual(mismatches, 0)


class CliTest(unittest.TestCase):
    def test_prints_flow(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", "s-a:2,a-t:2", "--source", "s", "--sink", "t"])
        self.assertEqual(code, 0)
        self.assertEqual(buffer.getvalue().strip(), "flow=2")

    def test_missing_edges(self):
        self.assertEqual(main([]), 2)

    def test_min_cut_output(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main([
                "--edges", "s-a:1,s-b:1,a-b:1,a-t:1,b-t:1",
                "--source", "s", "--sink", "t", "--min-cut",
            ])
        self.assertEqual(code, 0)
        self.assertEqual(buffer.getvalue().splitlines(), ["flow=2", "cut=s", "cut_capacity=2"])

    def test_invalid_capacity_exit_code(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", "s-a:1,a-t:x"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
